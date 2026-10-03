"""commands.py（コマンドごとの処理）の単体テスト。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

import commands
from errors import ItemNotFoundError, OptionNotFoundError, SchemaMismatchError
from fixture_types import MakeItem, MakeLegacyWorkspace, MakeWorkspace
from query import SearchFilter

# now の代わりに返す日時
FIXED_NOW = "2026-10-02T08:00:00+00:00"

# make_item が項目に入れる既定の日時
DEFAULT_TIMESTAMP = "2026-10-01T00:00:00+00:00"


def _fixed_now() -> str:
    """今の日時の代わりに、決めた日時を返す。"""
    return FIXED_NOW


def _read_items(root: Path, file_name: str) -> list[dict[str, Any]]:
    """ワークスペースの YAML を読んで、項目の並びを返す。"""
    data = yaml.safe_load((root / file_name).read_text(encoding="utf-8"))
    return data["items"]


@pytest.mark.parametrize(
    ("text", "expected_line"),
    [
        pytest.param("{", "標準入力: (全体): JSON として読めません", id="invalid_json"),
        pytest.param("[1]", "標準入力: (全体): オブジェクトではありません", id="not_object"),
    ],
)
def test_read_json_object_when_invalid(text: str, expected_line: str) -> None:
    """読めない・オブジェクトでない入力は受け付けない（異常系）。"""
    # 実行・検証
    with pytest.raises(SchemaMismatchError) as exc_info:
        commands.read_json_object(text)
    assert exc_info.value.lines == [expected_line]


def test_read_json_object() -> None:
    """オブジェクトを読む（正常系）。"""
    # 実行
    data = commands.read_json_object('{"title": "問い"}')
    # 検証
    assert data == {"title": "問い"}


def test_validate_input_keys() -> None:
    """渡せるキーだけなら何もしない（正常系）。"""
    # 実行
    result = commands.validate_input_keys("decision", {"title": "t", "body_markdown": "b"})
    # 検証
    assert result is None


@pytest.mark.parametrize("key", ["id", "created", "updated", "body"])
def test_validate_input_keys_when_reserved(key: str) -> None:
    """スクリプトが付けるキーを弾く（異常系）。"""
    # 実行・検証
    with pytest.raises(SchemaMismatchError) as exc_info:
        commands.validate_input_keys("decision", {key: "x"})
    assert key in exc_info.value.lines[0]


def test_validate_input_keys_when_body_not_allowed() -> None:
    """本文を持てない種類への body_markdown を弾く（異常系）。"""
    # 実行・検証
    with pytest.raises(SchemaMismatchError) as exc_info:
        commands.validate_input_keys("task", {"body_markdown": "b"})
    assert "body_markdown" in exc_info.value.lines[0]


def test_merge_changes() -> None:
    """置き換え・消す・同じ値を見分ける（正常系）。"""
    # 準備
    item = {"id": "D-1", "status": "未決定", "weight": "大", "lead": "l"}
    changes = {"status": "決定済み", "weight": None, "lead": "l", "answer": "a"}
    # 実行
    merged, changed = commands.merge_changes(item, changes)
    # 検証
    assert merged == {"id": "D-1", "status": "決定済み", "lead": "l", "answer": "a"}
    assert changed == ["status", "weight", "answer"]
    assert item == {"id": "D-1", "status": "未決定", "weight": "大", "lead": "l"}


def test_switch_adopted() -> None:
    """採用を切り替え、前の記号を返す（正常系）。"""
    # 準備
    item = {
        "options": [
            {"key": "A", "content": "案 A", "adopted": True},
            {"key": "B", "content": "案 B", "adopted": False},
        ]
    }
    # 実行
    switched, previous = commands.switch_adopted(item, "B")
    # 検証
    assert switched["options"] == [
        {"key": "A", "content": "案 A", "adopted": False},
        {"key": "B", "content": "案 B", "adopted": True},
    ]
    assert previous == "A"
    assert item["options"][0]["adopted"] is True


def test_switch_adopted_when_none_adopted() -> None:
    """採用が無ければ前の記号は None を返す（正常系）。"""
    # 準備
    item = {
        "options": [
            {"key": "A", "content": "案 A", "adopted": False},
            {"key": "B", "content": "案 B", "adopted": False},
        ]
    }
    # 実行
    switched, previous = commands.switch_adopted(item, "A")
    # 検証
    assert switched["options"] == [
        {"key": "A", "content": "案 A", "adopted": True},
        {"key": "B", "content": "案 B", "adopted": False},
    ]
    assert previous is None


def test_switch_adopted_when_option_missing() -> None:
    """無い記号は切り替えない（異常系）。"""
    # 準備
    item = {
        "options": [
            {"key": "A", "content": "案 A", "adopted": True},
            {"key": "B", "content": "案 B", "adopted": False},
        ]
    }
    # 実行・検証
    with pytest.raises(OptionNotFoundError) as exc_info:
        commands.switch_adopted(item, "Z")
    message = str(exc_info.value)
    assert "Z" in message
    assert "A" in message
    assert "B" in message


def test_run_init(tmp_path: Path, valid_settings: dict[str, Any]) -> None:
    """作ったワークスペースとファイルを返す（正常系）。"""
    # 準備
    root = tmp_path / "ws"
    # 実行
    payload, exit_code = commands.run_init(root, json.dumps(valid_settings, ensure_ascii=False))
    # 検証
    assert payload["workspace"] == str(root)
    assert len(payload["files"]) == 10
    assert exit_code == 0


def test_run_clear_release(make_workspace: MakeWorkspace) -> None:
    """release/ の中を消し、消したものを返す（正常系）。"""
    # 準備
    root = make_workspace()
    (root / "release" / "古い資料.md").write_text("古い\n", encoding="utf-8")
    # 実行
    payload, exit_code = commands.run_clear_release(root)
    # 検証
    assert payload == {"removed": ["古い資料.md"]}
    assert exit_code == 0


def test_run_add(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """本文つきの検討事項を足す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    stdin_text = json.dumps(
        {"title": "問い", "status": "未決定", "body_markdown": "## 経緯\n"},
        ensure_ascii=False,
    )
    # 実行
    payload, exit_code = commands.run_add(root, "decision", stdin_text, now=_fixed_now)
    # 検証
    assert payload == {"id": "D-2", "file": "decisions.yaml", "body": "docs/D-2.md"}
    assert exit_code == 0
    added = _read_items(root, "decisions.yaml")[1]
    assert added["created"] == FIXED_NOW
    assert added["updated"] == FIXED_NOW
    assert added["body"] == "D-2.md"
    assert "body_markdown" not in added
    assert (root / "docs" / "D-2.md").read_text(encoding="utf-8") == "## 経緯\n"


def test_run_add_when_no_body(make_workspace: MakeWorkspace) -> None:
    """本文が無ければ body を付けない（正常系）。"""
    # 準備
    root = make_workspace()
    stdin_text = json.dumps(
        {"title": "作業", "kind": "作業", "status": "未着手"}, ensure_ascii=False
    )
    # 実行
    payload, exit_code = commands.run_add(root, "task", stdin_text, now=_fixed_now)
    # 検証
    assert payload == {"id": "T-1", "file": "tasks.yaml", "body": None}
    assert exit_code == 0
    assert "body" not in _read_items(root, "tasks.yaml")[0]


def test_run_update(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """キーを置き換えて更新日時を変える（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", lead="l", weight="大"))
    # 実行
    payload, exit_code = commands.run_update(
        root, "D-1", '{"answer": "a", "weight": null}', now=_fixed_now
    )
    # 検証
    assert payload == {
        "id": "D-1",
        "file": "decisions.yaml",
        "changed": ["answer", "weight"],
    }
    assert exit_code == 0
    updated = _read_items(root, "decisions.yaml")[0]
    assert updated["answer"] == "a"
    assert "weight" not in updated
    assert updated["lead"] == "l"
    assert updated["created"] == DEFAULT_TIMESTAMP
    assert updated["updated"] == FIXED_NOW


def test_run_adopt(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """切り替えて書き込む（正常系）。"""
    # 準備
    root = make_workspace(
        make_item(
            "D-1",
            options=[
                {"key": "A", "content": "案 A", "adopted": True},
                {"key": "B", "content": "案 B", "adopted": False},
            ],
        )
    )
    # 実行
    payload, exit_code = commands.run_adopt(root, "D-1", "B", now=_fixed_now)
    # 検証
    assert payload == {"id": "D-1", "adopted": "B", "previous": "A"}
    assert exit_code == 0
    options = _read_items(root, "decisions.yaml")[0]["options"]
    assert options[0]["adopted"] is False
    assert options[1]["adopted"] is True


def test_run_adopt_when_not_decision(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """検討事項でない ID は切り替えない（異常系）。"""
    # 準備
    root = make_workspace(make_item("T-1"))
    # 実行・検証
    with pytest.raises(ItemNotFoundError, match="T-1"):
        commands.run_adopt(root, "T-1", "A", now=_fixed_now)


def test_run_check(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """問題が無ければ 0 を返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    payload, exit_code = commands.run_check(root)
    # 検証
    assert payload == {"ok": True, "problems": []}
    assert exit_code == 0


def test_run_check_when_problems(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """問題があれば 1 を返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", depends_on=["D-9"]))
    # 実行
    payload, exit_code = commands.run_check(root)
    # 検証
    assert payload["ok"] is False
    assert len(payload["problems"]) == 1
    assert exit_code == 1


def test_run_check_when_legacy_format(make_legacy_workspace: MakeLegacyWorkspace) -> None:
    """前の版の形式の問題に migrate を案内する（正常系）。"""
    # 準備
    root = make_legacy_workspace(legacy_docs={"A-1": True})
    # 実行
    payload, exit_code = commands.run_check(root)
    # 検証
    assert payload["ok"] is False
    assert exit_code == 1
    details = [problem["detail"] for problem in payload["problems"] if problem["id"] == "A-1"]
    assert details != []
    assert all(detail.endswith("（migrate で今の形式に移せます）") for detail in details)


def test_run_build(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """書き出したパスを返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    payload, exit_code = commands.run_build(root, now=_fixed_now)
    # 検証
    assert payload == {"path": str(root / "preview.html")}
    assert exit_code == 0
    assert (root / "preview.html").exists()


def test_run_impact(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """影響を出力の形にする（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"), make_item("D-2", title="依存する問い", depends_on=["D-1"])
    )
    # 実行
    payload, exit_code = commands.run_impact(root, "D-1")
    # 検証
    assert payload == {
        "id": "D-1",
        "affected": [
            {
                "id": "D-2",
                "title": "依存する問い",
                "status": "未決定",
                "via": [],
                "key": "depends_on",
            }
        ],
    }
    assert exit_code == 0


def test_run_next(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """次の候補を出力の形にする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", title="最初の問い"))
    # 実行
    payload, exit_code = commands.run_next(root, None)
    # 検証
    assert payload == {
        "candidates": [
            {
                "id": "D-1",
                "title": "最初の問い",
                "phase": None,
                "weight": None,
                "followers": 0,
            }
        ]
    }
    assert exit_code == 0


def test_run_status(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """再開時の状況を出力の形にする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", title="見直しの問い", status="要見直し"))
    # 実行
    payload, exit_code = commands.run_status(root)
    # 検証
    assert payload["needs_review"] == [{"id": "D-1", "title": "見直しの問い"}]
    assert {"in_progress", "resumable", "waiting", "on_hold", "next"} <= set(payload)
    assert exit_code == 0


def test_run_find(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """検索結果を出力の形にする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", title="最初の問い"))
    # 実行
    payload, exit_code = commands.run_find(root, SearchFilter())
    # 検証
    assert payload == {
        "items": [{"id": "D-1", "kind": "decision", "title": "最初の問い", "status": "未決定"}]
    }
    assert exit_code == 0


def test_run_show(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """1 件を出力の形にする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    # 実行
    payload, exit_code = commands.run_show(root, "D-1")
    # 検証
    assert set(payload) == {"item", "kind", "body_markdown", "referenced_by"}
    assert exit_code == 0


def test_run_attrs(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """属性名を出力の形にする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", attrs={"担当": "自分"}))
    # 実行
    payload, exit_code = commands.run_attrs(root)
    # 検証
    assert payload == {"attrs": [{"name": "担当", "count": 1, "kinds": ["decision"]}]}
    assert exit_code == 0


def test_run_goal(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """判定を出力の形にする（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", phase="目的", status="未決定"))
    # 実行
    payload, exit_code = commands.run_goal(root)
    # 検証
    assert exit_code == 0
    assert payload["reached"] is False
    assert {
        "goal_phase",
        "phases",
        "remaining_decisions",
        "remaining_deliverables",
    } <= set(payload)


def test_run_migrate(make_legacy_workspace: MakeLegacyWorkspace) -> None:
    """移したものを返す（正常系）。"""
    # 準備
    root = make_legacy_workspace(legacy_docs={"A-1": False})
    # 実行
    payload, exit_code = commands.run_migrate(root, summary=None)
    # 検証
    assert exit_code == 0
    assert payload == {
        "migrated": [{"id": "A-1", "file": "docs.yaml", "change": "done: false → status: 下書き"}]
    }
