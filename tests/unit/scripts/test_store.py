"""store.py（読み込み・検証・採番・書き込み）の単体テスト。"""

from __future__ import annotations

import dataclasses
import os
import re
import shutil
import stat
import sys
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator

import store
from errors import (
    ItemNotFoundError,
    SchemaMismatchError,
    WorkspaceExistsError,
    WorkspaceNotFoundError,
    WriteFailedError,
)
from fixture_types import FailingUnlink, MakeItem, MakeWorkspace, SnapshotTree

# 壊れた YAML（閉じていないフローの配列）
BROKEN_YAML = "items: [unclosed"


def _prepare_target(target: Path, mode: int | None) -> None:
    """mode があれば、その権限を持つ置き換え先のファイルを作る（None なら作らない）。"""
    # 置き換え先が無い場合を作るときは何もしない
    if mode is None:
        return
    target.write_text("元の中身\n", encoding="utf-8")
    target.chmod(mode)


@pytest.fixture
def restore_umask() -> Iterator[None]:
    """テストの後で umask を元に戻す。"""
    original = os.umask(0)
    os.umask(original)
    yield
    os.umask(original)


def _fail_body_temp(
    real_write_temp: Callable[[Path, str], Path],
) -> Callable[[Path, str], Path]:
    """docs/ の本文の一時ファイルだけ書けない _write_temp の代わりを作る。"""

    def _write_temp(target: Path, text: str) -> Path:
        """置き換え先が docs/ の下なら OSError、それ以外は本物で書く。"""
        # 本文（docs/ の下）の一時ファイル
        if target.parent.name == "docs":
            raise OSError("書き込めません")
        # YAML の一時ファイルは本物で書く
        return real_write_temp(target, text)

    return _write_temp


def test_load_workspace(make_workspace, make_item) -> None:
    """設定と種類ごとの項目を読む（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    workspace = store.load_workspace(root)
    # 検証
    assert workspace.items == {
        "decision": [make_item("D-1")],
        "task": [],
        "research": [],
        "doc": [],
        "term": [],
        "note": [],
        "log": [],
    }
    assert workspace.load_problems == []


def test_load_workspace_when_yaml_broken(make_workspace) -> None:
    """読めない YAML を問題に記録して続ける（正常系）。"""
    # 準備
    root = make_workspace(raw_files={"tasks.yaml": BROKEN_YAML})
    # 実行
    workspace = store.load_workspace(root)
    # 検証
    assert workspace.items["task"] == []
    assert len(workspace.load_problems) == 1
    problem = workspace.load_problems[0]
    assert problem.file == "tasks.yaml"
    assert problem.kind == "schema"
    assert problem.key == "(全体)"


def test_load_workspace_when_settings_missing(tmp_path: Path) -> None:
    """mindmap.yaml が無いフォルダは読まない（異常系）。"""
    # 実行・検証
    with pytest.raises(WorkspaceNotFoundError, match=re.escape(str(tmp_path))):
        store.load_workspace(tmp_path)


def test_load_workspace_when_top_level_list(make_workspace) -> None:
    """一番上が配列のファイルは項目を空にし、読んだ値は raw に残す（正常系）。"""
    # 準備
    root = make_workspace(raw_files={"decisions.yaml": "- id: D-1\n"})
    # 実行
    workspace = store.load_workspace(root)
    # 検証
    assert workspace.items["decision"] == []
    assert workspace.raw["decisions.yaml"] == [{"id": "D-1"}]
    assert workspace.load_problems == []


def test_load_workspace_when_settings_broken(make_workspace) -> None:
    """設定が YAML として読めなければ問題に記録して空にする（正常系）。"""
    # 準備
    root = make_workspace(raw_files={"mindmap.yaml": BROKEN_YAML})
    # 実行
    workspace = store.load_workspace(root)
    # 検証
    assert workspace.settings == {}
    assert len(workspace.load_problems) == 1
    problem = workspace.load_problems[0]
    assert problem.file == "mindmap.yaml"
    assert problem.key == "(全体)"
    assert "mindmap.yaml" not in workspace.raw


def test_validate_workspace(make_workspace, make_item) -> None:
    """合うワークスペースは問題 0 件（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace(make_item("D-1")))
    # 実行
    problems = store.validate_workspace(workspace)
    # 検証
    assert problems == []


def test_validate_workspace_when_status_invalid(make_workspace, make_item) -> None:
    """共通でない種類固有の値の誤りを拾う（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"), make_item("D-2", status="完了"))
    workspace = store.load_workspace(root)
    # 実行
    problems = store.validate_workspace(workspace)
    # 検証
    assert len(problems) == 1
    problem = problems[0]
    assert problem.kind == "schema"
    assert problem.file == "decisions.yaml"
    assert problem.key == "items[1].status"
    assert problem.id == "D-2"


def test_validate_workspace_when_common_key_invalid(make_workspace, make_item) -> None:
    """共通のスキーマ側で決めたキーの誤りも拾う（ファイルをまたぐ $ref）（正常系）。"""
    # 準備
    root = make_workspace(make_item("T-1", tags="データ"))
    workspace = store.load_workspace(root)
    # 実行
    problems = store.validate_workspace(workspace)
    # 検証
    assert len(problems) == 1
    assert problems[0].file == "tasks.yaml"
    assert problems[0].key == "items[0].tags"


def test_validate_workspace_when_load_problem(make_workspace) -> None:
    """読めなかったファイルの問題も含める（正常系）。"""
    # 準備
    root = make_workspace(raw_files={"notes.yaml": BROKEN_YAML})
    workspace = store.load_workspace(root)
    # 実行
    problems = store.validate_workspace(workspace)
    # 検証
    assert workspace.load_problems[0] in problems


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("- id: D-1\n", id="top_level_list"),
        pytest.param("items: []\nextra: 1\n", id="extra_key"),
    ],
)
def test_validate_workspace_when_top_level_invalid(make_workspace, text: str) -> None:
    """一番上の形の誤りを拾う（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace(raw_files={"decisions.yaml": text}))
    # 実行
    problems = store.validate_workspace(workspace)
    # 検証
    assert len(problems) == 1
    assert problems[0].file == "decisions.yaml"
    assert problems[0].kind == "schema"
    assert problems[0].key == "(全体)"


@pytest.mark.parametrize(
    ("file_name", "item_id", "kind", "expected"),
    [
        pytest.param("mindmap.yaml", None, "schema", True, id="settings"),
        pytest.param("docs.yaml", "A-1", "schema", True, id="legacy_doc"),
        pytest.param("decisions.yaml", "D-1", "schema", False, id="decision"),
        pytest.param("docs.yaml", "A-1", "broken_ref", False, id="broken_ref"),
    ],
)
def test_is_legacy_problem(
    make_legacy_workspace,
    make_item,
    file_name: str,
    item_id: str | None,
    kind: str,
    expected: bool,
) -> None:
    """前の版の形式の問題を見分ける（正常系）。"""
    # 準備
    root = make_legacy_workspace(
        make_item("D-1", status="完了"), legacy_docs={"A-1": True}, without_summary=True
    )
    workspace = store.load_workspace(root)
    problems = store.validate_workspace(workspace)
    problem = next(p for p in problems if p.file == file_name and p.id == item_id)
    # 種類だけを差し替えた問題にする
    problem = dataclasses.replace(problem, kind=kind)
    # 実行
    result = store.is_legacy_problem(problem, workspace)
    # 検証
    assert result is expected


@pytest.mark.parametrize(
    "schema_name",
    [
        pytest.param("settings.schema.json", id="settings"),
        pytest.param("decisions.schema.json", id="decisions"),
        pytest.param("tasks.schema.json", id="tasks"),
        pytest.param("research.schema.json", id="research"),
        pytest.param("docs.schema.json", id="docs"),
        pytest.param("terms.schema.json", id="terms"),
        pytest.param("notes.schema.json", id="notes"),
        pytest.param("logs.schema.json", id="logs"),
    ],
)
def test_load_validators(schema_name: str) -> None:
    """同梱のスキーマから 8 つの検証器を作り、各スキーマがそれ自体として正しい（正常系）。"""
    # 実行
    validators = store.load_validators()
    # 検証
    assert len(validators) == 8
    assert schema_name in validators
    Draft202012Validator.check_schema(validators[schema_name].schema)


def test_find_item(make_workspace, make_item) -> None:
    """ID の項目と位置を返す（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace(make_item("D-1"), make_item("D-2")))
    # 実行
    ref = store.find_item(workspace, "D-2")
    # 検証
    assert ref.kind == "decision"
    assert ref.index == 1
    assert ref.item == make_item("D-2")


def test_find_item_when_unknown_prefix(make_workspace, make_item) -> None:
    """種類に当たらない ID は見つからない（異常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace(make_item("D-1")))
    # 実行・検証
    with pytest.raises(ItemNotFoundError, match="X-1"):
        store.find_item(workspace, "X-1")


def test_find_item_when_id_missing(make_workspace, make_item) -> None:
    """種類に当たるが項目が無い ID は見つからない（異常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace(make_item("D-1")))
    # 実行・検証
    with pytest.raises(ItemNotFoundError, match="D-9"):
        store.find_item(workspace, "D-9")


def test_next_id(make_workspace, make_item) -> None:
    """間が空いていても最大 + 1 を振る（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace(make_item("D-1"), make_item("D-3")))
    # 実行
    item_id = store.next_id(workspace, "decision")
    # 検証
    assert item_id == "D-4"


def test_next_id_when_empty(make_workspace, make_item) -> None:
    """項目が無ければ 1 を振る（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace(make_item("D-1")))
    # 実行
    item_id = store.next_id(workspace, "task")
    # 検証
    assert item_id == "T-1"


def test_save_change(make_workspace, make_item, snapshot_tree) -> None:
    """項目の並びと本文を書き、一時ファイルを残さない（正常系）。"""
    # 準備
    root = make_workspace()
    workspace = store.load_workspace(root)
    item = make_item("D-1", body="D-1.md")
    change = store.Change(
        kind="decision",
        items=[item],
        body=store.BodyWrite(name="D-1.md", text="## 経緯\n"),
    )
    # 実行
    store.save_change(workspace, change)
    # 検証
    saved = yaml.safe_load((root / "decisions.yaml").read_text(encoding="utf-8"))
    assert saved == {"items": [item]}
    assert (root / "docs" / "D-1.md").read_text(encoding="utf-8") == "## 経緯\n"
    assert list(root.rglob("*.tmp")) == []


def test_save_change_when_schema_mismatch(make_workspace, make_item, snapshot_tree) -> None:
    """スキーマに合わない変更は書かない（異常系）。"""
    # 準備
    root = make_workspace()
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    change = store.Change(
        kind="decision",
        items=[make_item("D-1", body="D-1.md", status="完了")],
        body=store.BodyWrite(name="D-1.md", text="本文\n"),
    )
    # 実行・検証
    with pytest.raises(SchemaMismatchError) as exc_info:
        store.save_change(workspace, change)
    assert exc_info.value.lines[0].startswith("decisions.yaml: items[0].status:")
    assert snapshot_tree(root) == before


def test_save_change_when_temp_write_fails(
    make_workspace, make_item, snapshot_tree, monkeypatch: pytest.MonkeyPatch
) -> None:
    """一時ファイルを書けなければ何も置き換えない（異常系）。"""
    # 準備
    root = make_workspace()
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    change = store.Change(
        kind="decision",
        items=[make_item("D-1", body="D-1.md")],
        body=store.BodyWrite(name="D-1.md", text="本文\n"),
    )
    # store モジュールの参照を、本文の一時ファイルだけ書けないものに差し替える
    monkeypatch.setattr(store, "_write_temp", _fail_body_temp(store._write_temp))
    # 実行・検証
    with pytest.raises(WriteFailedError):
        store.save_change(workspace, change)
    assert snapshot_tree(root) == before
    assert list(root.rglob("*.tmp")) == []


def test_save_change_when_yaml_replace_fails_with_previous_body(
    make_workspace,
    make_item,
    snapshot_tree,
    failing_replace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """YAML の置き換えに失敗したら前の本文に戻す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", body="D-1.md"), bodies={"D-1.md": "前の本文\n"})
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    change = store.Change(
        kind="decision",
        items=[make_item("D-1", body="D-1.md", answer="a")],
        body=store.BodyWrite(name="D-1.md", text="新しい本文\n"),
    )
    # store モジュールの参照を、decisions.yaml への置き換えだけ失敗するものに差し替える
    monkeypatch.setattr(store.os, "replace", failing_replace("decisions.yaml"))
    # 実行・検証
    with pytest.raises(WriteFailedError, match=r"decisions\.yaml"):
        store.save_change(workspace, change)
    assert snapshot_tree(root) == before
    assert list(root.rglob("*.tmp")) == []


def test_save_change_when_yaml_replace_fails_without_previous_body(
    make_workspace,
    make_item,
    snapshot_tree,
    failing_replace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """YAML の置き換えに失敗したら新しく書いた本文を消す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    change = store.Change(
        kind="decision",
        items=[make_item("D-1", body="D-1.md")],
        body=store.BodyWrite(name="D-1.md", text="新しい本文\n"),
    )
    # store モジュールの参照を、decisions.yaml への置き換えだけ失敗するものに差し替える
    monkeypatch.setattr(store.os, "replace", failing_replace("decisions.yaml"))
    # 実行・検証
    with pytest.raises(WriteFailedError):
        store.save_change(workspace, change)
    assert not (root / "docs" / "D-1.md").exists()
    assert snapshot_tree(root) == before
    assert list(root.rglob("*.tmp")) == []


def test_create_workspace(tmp_path: Path, valid_settings: dict[str, Any]) -> None:
    """まだ無いフォルダにワークスペースを作る（正常系）。"""
    # 準備
    root = tmp_path / "ws"
    # 実行
    files = store.create_workspace(root, valid_settings, version="v0.3.0")
    # 検証
    assert len(files) == 11
    assert set(files) == {
        "mindmap.yaml",
        "decisions.yaml",
        "tasks.yaml",
        "research.yaml",
        "docs.yaml",
        "terms.yaml",
        "notes.yaml",
        "logs.yaml",
        "mindstella-version.ini",
        "docs/",
        "release/",
    }
    assert yaml.safe_load((root / "mindmap.yaml").read_text(encoding="utf-8")) == valid_settings
    assert (root / "mindstella-version.ini").read_text(encoding="utf-8") == "v0.3.0\n"


def test_create_workspace_when_exists(make_workspace, snapshot_tree, valid_settings) -> None:
    """mindmap.yaml があるフォルダには作らない（異常系）。"""
    # 準備
    root = make_workspace()
    before = snapshot_tree(root)
    # 実行・検証
    with pytest.raises(WorkspaceExistsError, match=re.escape(str(root))):
        store.create_workspace(root, valid_settings, version="v0.3.0")
    assert snapshot_tree(root) == before


def test_create_workspace_when_settings_invalid(
    tmp_path: Path, valid_settings: dict[str, Any]
) -> None:
    """設定がスキーマに合わなければフォルダも作らない（異常系）。"""
    # 準備
    root = tmp_path / "ws"
    del valid_settings["phases"]
    # 実行・検証
    with pytest.raises(SchemaMismatchError) as exc_info:
        store.create_workspace(root, valid_settings, version="v0.3.0")
    assert "mindmap.yaml" in str(exc_info.value.lines)
    assert "phases" in str(exc_info.value.lines)
    assert not root.exists()


def test_create_workspace_when_write_fails(
    tmp_path: Path, valid_settings: dict[str, Any], failing_write_text
) -> None:
    """途中で書けなくなったら作ったものを消す（異常系）。"""
    # 準備
    root = tmp_path / "ws"
    # 7 種類の YAML のうち最後の logs.yaml だけ書けないようにする
    failing_write_text("logs.yaml")
    # 実行・検証
    with pytest.raises(WriteFailedError):
        store.create_workspace(root, valid_settings, version="v0.3.0")
    assert not root.exists()


def test_clear_release(make_workspace: MakeWorkspace) -> None:
    """release/ の中のファイルとフォルダを消し、消したものを名前の順に返す（正常系）。"""
    # 準備
    root = make_workspace()
    (root / "release" / "古い資料.md").write_text("古い\n", encoding="utf-8")
    (root / "release" / "図").mkdir()
    (root / "release" / "図" / "構成.md").write_text("図\n", encoding="utf-8")
    settings_before = (root / "mindmap.yaml").read_bytes()
    # 実行
    removed = store.clear_release(root)
    # 検証
    assert removed == ["古い資料.md", "図/"]
    assert (root / "release").is_dir()
    assert list((root / "release").iterdir()) == []
    assert (root / "mindmap.yaml").read_bytes() == settings_before


def test_clear_release_when_release_dir_missing(
    make_workspace: MakeWorkspace, snapshot_tree: SnapshotTree
) -> None:
    """release/ が無ければ空の release/ を作り、前の版の handoff/ は触らない（正常系）。"""
    # 準備
    root = make_workspace()
    shutil.rmtree(root / "release")
    (root / "handoff").mkdir()
    (root / "handoff" / "資料.md").write_text("前の版の資料\n", encoding="utf-8")
    handoff_before = snapshot_tree(root / "handoff")
    # 実行
    removed = store.clear_release(root)
    # 検証
    assert removed == []
    assert (root / "release").is_dir()
    assert list((root / "release").iterdir()) == []
    assert snapshot_tree(root / "handoff") == handoff_before


def test_clear_release_when_workspace_missing(tmp_path: Path) -> None:
    """mindmap.yaml が無ければ何も消さない（異常系）。"""
    # 準備
    (tmp_path / "release").mkdir()
    (tmp_path / "release" / "資料.md").write_text("資料\n", encoding="utf-8")
    # 実行・検証
    with pytest.raises(WorkspaceNotFoundError, match=re.escape(str(tmp_path))):
        store.clear_release(tmp_path)
    assert (tmp_path / "release" / "資料.md").read_text(encoding="utf-8") == "資料\n"


def test_clear_release_when_remove_fails(
    make_workspace: MakeWorkspace, failing_unlink: FailingUnlink
) -> None:
    """消せないものに当たった時点で止まり、それまでに消したものは戻さない（異常系）。"""
    # 準備
    root = make_workspace()
    (root / "release" / "一.md").write_text("一\n", encoding="utf-8")
    (root / "release" / "二.md").write_text("二\n", encoding="utf-8")
    # 名前の順に消すので、一.md を消した後に二.md で止まる
    failing_unlink("二.md")
    # 実行・検証
    with pytest.raises(WriteFailedError, match=re.escape(str(root / "release" / "二.md"))):
        store.clear_release(root)
    assert (root / "release" / "二.md").exists()
    assert not (root / "release" / "一.md").exists()


def test_read_body(make_workspace) -> None:
    """ある本文を読む（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace(bodies={"D-1.md": "本文\n"}))
    # 実行
    text = store.read_body(workspace, "D-1.md")
    # 検証
    assert text == "本文\n"


def test_read_body_when_missing(make_workspace) -> None:
    """無い本文は None を返す（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace())
    # 実行
    text = store.read_body(workspace, "D-9.md")
    # 検証
    assert text is None


def test_read_body_when_outside(make_workspace) -> None:
    """docs/ の外を指す名前は読まない（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace())
    # 実行
    text = store.read_body(workspace, "../mindmap.yaml")
    # 検証
    assert text is None


def test_dump_yaml() -> None:
    """日本語とキーの並びを保つ（正常系）。"""
    # 実行
    text = store.dump_yaml({"title": "問い", "id": "D-1"})
    # 検証
    assert text == "title: 問い\nid: D-1\n"


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        pytest.param(["items", 0, "options", 1, "key"], "items[0].options[1].key", id="nested"),
        pytest.param([], "(全体)", id="empty"),
    ],
)
def test_format_path(path: list[str | int], expected: str) -> None:
    """キーと添字をつなぐ（正常系）。"""
    # 実行
    text = store._format_path(path)
    # 検証
    assert text == expected


@pytest.mark.parametrize(
    "broken_text",
    [
        pytest.param("- id: D-1\n", id="top_level_list"),
        pytest.param("items:\n- id: D-1\nextra: 1\n", id="extra_key"),
        pytest.param("items:\n- id: D-1\n- 文字列の要素\n", id="string_element"),
        pytest.param(BROKEN_YAML, id="yaml_unreadable"),
    ],
)
def test_save_change_when_file_shape_broken(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
    broken_text: str,
) -> None:
    """書き戻すと中身を失うファイルには書かない（異常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"),
        make_item("D-2"),
        raw_files={"decisions.yaml": broken_text},
    )
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    change = store.Change(kind="decision", items=[make_item("D-1")])
    # 実行・検証
    with pytest.raises(SchemaMismatchError) as exc_info:
        store.save_change(workspace, change)
    assert all(line.startswith("decisions.yaml: ") for line in exc_info.value.lines)
    assert len(exc_info.value.lines) >= 1
    assert snapshot_tree(root) == before


def test_save_change_when_item_value_fixed(
    make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """項目の中の合わない値は、それを直す変更なら書ける（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", status="完了"))
    workspace = store.load_workspace(root)
    change = store.Change(kind="decision", items=[make_item("D-1", status="未決定")])
    # 実行
    store.save_change(workspace, change)
    # 検証
    saved = yaml.safe_load((root / "decisions.yaml").read_text(encoding="utf-8"))
    assert saved["items"][0]["status"] == "未決定"


@pytest.mark.skipif(sys.platform == "win32", reason="権限のビットは Windows では効かない")
@pytest.mark.parametrize(
    ("target_mode", "expected_mode"),
    [
        pytest.param(0o640, 0o640, id="copy_from_target"),
        pytest.param(None, 0o644, id="from_umask"),
    ],
)
def test_write_temp_when_mode(
    tmp_path: Path,
    restore_umask: None,
    target_mode: int | None,
    expected_mode: int,
) -> None:
    """置き換え先の権限を一時ファイルに写す（正常系）。"""
    # 準備
    target = tmp_path / "target.yaml"
    _prepare_target(target, target_mode)
    os.umask(0o022)
    # 実行
    temp = store._write_temp(target, "新しい中身\n")
    # 検証
    assert stat.S_IMODE(temp.stat().st_mode) == expected_mode
