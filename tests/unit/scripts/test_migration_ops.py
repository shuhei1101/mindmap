"""migration_ops.py（操作ごとの当て方と、手順の 1 行の説明）の単体テスト。"""

from __future__ import annotations

from contextlib import nullcontext
from pathlib import Path
from typing import Any

import pytest
import yaml

import migration_ops
from fixture_types import MakeItem, MakeLegacyWorkspace, MakeWorkspace, SnapshotTree
from migration_helpers import make_step, snapshot_mtimes
from migration_ops import StepError
from migrator import NeededValue

# v0.3.0 の 3 つの手順の引数（steps.yaml の中身を YAML で読んだ形。true・false は真偽値になる）
RENAME_DONE_ARGS: dict[str, Any] = {
    "file": "docs.yaml",
    "each_item": True,
    "from": "done",
    "to": "status",
}
MAP_STATUS_ARGS: dict[str, Any] = {
    "file": "docs.yaml",
    "each_item": True,
    "key": "status",
    "map": {True: "完成", False: "下書き"},
}
ASK_SUMMARY_ARGS: dict[str, Any] = {
    "file": "mindmap.yaml",
    "each_item": False,
    "key": "summary",
    "ask": "話し合いの題名",
}

# 変換のスクリプト（notes.yaml を書いて、変えたファイルを返す migrate を持つ）
CONVERT_SCRIPT = """\
from pathlib import Path


def migrate(root: Path) -> list[str]:
    \"\"\"notes.yaml を書いて、変えたファイルを返す。\"\"\"
    (root / "notes.yaml").write_text("items: []\\n", encoding="utf-8")
    return ["notes.yaml"]
"""


def _read_items(root: Path, file_name: str) -> list[dict[str, Any]]:
    """ワークスペースの YAML を読んで、項目の並びを返す。"""
    data = yaml.safe_load((root / file_name).read_text(encoding="utf-8"))
    return data["items"]


def test_apply_step_when_rename_key(make_legacy_workspace: MakeLegacyWorkspace) -> None:
    """キーの名前を位置を保って変える（正常系）。"""
    # 準備
    root = make_legacy_workspace(legacy_docs={"A-1": True})
    # 実行
    changed = migration_ops.apply_step(root, make_step("rename_key", RENAME_DONE_ARGS))
    # 検証
    item = _read_items(root, "docs.yaml")[0]
    assert list(item) == [
        "id",
        "title",
        "kind",
        "deliverable",
        "status",
        "body",
        "created",
        "updated",
    ]
    assert item["status"] is True
    assert changed == ["docs.yaml"]


def test_apply_step_when_rename_key_missing(
    make_workspace: MakeWorkspace, make_item: MakeItem, snapshot_tree: SnapshotTree
) -> None:
    """from が無い項目は飛ばし、ファイルを書かない（正常系）。"""
    # 準備
    root = make_workspace(make_item("A-1", status="完成"))
    before = snapshot_tree(root)
    mtimes = snapshot_mtimes(root)
    # 実行
    changed = migration_ops.apply_step(root, make_step("rename_key", RENAME_DONE_ARGS))
    # 検証
    assert changed == []
    assert snapshot_tree(root) == before
    assert snapshot_mtimes(root) == mtimes


def test_apply_step_when_rename_key_conflict(
    make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """from と to の両方を持つ項目は送る（異常系）。"""
    # 準備
    root = make_workspace(make_item("A-1", done=True))
    # 実行・検証
    with pytest.raises(StepError) as exc_info:
        migration_ops.apply_step(root, make_step("rename_key", RENAME_DONE_ARGS))
    message = str(exc_info.value)
    assert "status" in message
    assert any(token in message for token in ("A-1", "items[0]"))


def test_apply_step_when_map_values(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """map にある値だけを置き換える（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("A-1", status=True),
        make_item("A-2", status=False),
        make_item("A-3", status="確認中"),
    )
    # 実行
    migration_ops.apply_step(root, make_step("map_values", MAP_STATUS_ARGS))
    # 検証
    statuses = [item["status"] for item in _read_items(root, "docs.yaml")]
    assert statuses == ["完成", "下書き", "確認中"]


def test_apply_step_when_set_default_ask(
    make_legacy_workspace: MakeLegacyWorkspace, snapshot_tree: SnapshotTree
) -> None:
    """ask は何も書かない（正常系）。"""
    # 準備
    root = make_legacy_workspace(without_summary=True)
    before = snapshot_tree(root)
    # 実行
    changed = migration_ops.apply_step(root, make_step("set_default", ASK_SUMMARY_ARGS))
    # 検証
    assert changed == []
    assert snapshot_tree(root) == before


def test_apply_step_when_set_default_value(
    make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """キーが無い項目にだけ既定の値を足す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", tags=["既存"]), make_item("D-2"))
    step = make_step(
        "set_default",
        {"file": "decisions.yaml", "each_item": True, "key": "tags", "value": []},
    )
    # 実行
    migration_ops.apply_step(root, step)
    # 検証
    items = _read_items(root, "decisions.yaml")
    assert items[0]["tags"] == ["既存"]
    assert items[1]["tags"] == []


@pytest.mark.parametrize(
    (
        "files",
        "expectation",
        "expected_changed",
        "expected_a_exists",
        "expected_b_text",
    ),
    [
        pytest.param(
            {"a.yaml": "a\n"},
            nullcontext(),
            ["a.yaml", "b.yaml"],
            False,
            "a\n",
            id="move",
        ),
        pytest.param(
            {"a.yaml": "a\n", "b.yaml": "b\n"},
            pytest.raises(StepError),
            None,
            True,
            "b\n",
            id="destination_exists",
        ),
    ],
)
def test_apply_step_when_rename_file(
    make_workspace: MakeWorkspace,
    files: dict[str, str],
    expectation: Any,
    expected_changed: list[str] | None,
    expected_a_exists: bool,
    expected_b_text: str,
) -> None:
    """ファイルを動かし、動かす先があれば送る（正常系・異常系）。"""
    # 準備
    root = make_workspace(raw_files=files)
    step = make_step("rename_file", {"from": "a.yaml", "to": "b.yaml"})
    changed: list[str] | None = None
    # 実行・検証
    with expectation:
        changed = migration_ops.apply_step(root, step)
    assert changed == expected_changed
    assert (root / "a.yaml").exists() is expected_a_exists
    assert (root / "b.yaml").read_text(encoding="utf-8") == expected_b_text


def test_apply_step_when_delete_missing(make_workspace: MakeWorkspace) -> None:
    """消す対象が無ければ飛ばす（正常系）。"""
    # 準備
    root = make_workspace()
    # 実行
    changed = migration_ops.apply_step(root, make_step("delete", {"path": "old/"}))
    # 検証
    assert changed == []


def test_apply_step_when_call(make_workspace: MakeWorkspace, tmp_path: Path) -> None:
    """変換のスクリプトの migrate を呼ぶ（正常系）。"""
    # 準備
    root = make_workspace()
    folder = tmp_path / "v0.3.0"
    (folder / "scripts").mkdir(parents=True)
    (folder / "scripts" / "convert.py").write_text(CONVERT_SCRIPT, encoding="utf-8")
    step = make_step("call", {"script": "convert"}, folder=folder)
    # 実行
    changed = migration_ops.apply_step(root, step)
    # 検証
    assert changed == ["notes.yaml"]
    assert (root / "notes.yaml").exists()


def test_apply_step_when_unreadable(make_workspace: MakeWorkspace) -> None:
    """YAML として読めなければ送る（異常系）。"""
    # 準備
    root = make_workspace(raw_files={"docs.yaml": "items: [\n"})
    # 実行・検証
    with pytest.raises(StepError) as exc_info:
        migration_ops.apply_step(root, make_step("rename_key", RENAME_DONE_ARGS))
    assert str(exc_info.value).startswith("docs.yaml を読めません")


@pytest.mark.parametrize(
    ("step", "expected"),
    [
        pytest.param(
            make_step("rename_key", RENAME_DONE_ARGS),
            "docs.yaml の items[].done を status に名前を変える",
            id="rename_key",
        ),
        pytest.param(
            make_step("map_values", MAP_STATUS_ARGS),
            "docs.yaml の items[].status の値を置き換える（true → 完成、false → 下書き）",
            id="map_values",
        ),
        pytest.param(
            make_step("set_default", ASK_SUMMARY_ARGS),
            "mindmap.yaml の summary を利用者に聞く（話し合いの題名）",
            id="set_default_ask",
        ),
    ],
)
def test_describe_step(step: Any, expected: str) -> None:
    """操作ごとの 1 行を作る（正常系）。"""
    # 実行
    result = migration_ops.describe_step(step)
    # 検証
    assert result == expected


@pytest.mark.parametrize(
    ("without_summary", "expected"),
    [
        pytest.param(
            True,
            [NeededValue(file="mindmap.yaml", key="summary", description="話し合いの題名")],
            id="missing",
        ),
        pytest.param(False, [], id="present"),
    ],
)
def test_list_needed_values(
    make_legacy_workspace: MakeLegacyWorkspace,
    without_summary: bool,
    expected: list[NeededValue],
) -> None:
    """キーが無ければ返し、あれば返さない（正常系）。"""
    # 準備
    root = make_legacy_workspace(without_summary=without_summary)
    # 実行
    result = migration_ops.list_needed_values(root, make_step("set_default", ASK_SUMMARY_ARGS))
    # 検証
    assert result == expected
