"""check（ワークスペースの点検）の結合テスト。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .fixture_types import MakeItem, MakeLegacyWorkspace, MakeWorkspace, RunMindmap, SnapshotTree


def _problem_keys(problems: list[dict[str, Any]]) -> set[tuple[str, str, str | None, str | None]]:
    """問題から種類・ファイル・ID・キーの組を取り出し、並びを問わない集まりにする。"""
    return {(row["kind"], row["file"], row["id"], row["key"]) for row in problems}


def test_normal_when_clean(
    make_workspace: MakeWorkspace, make_item: MakeItem, run_mindmap: RunMindmap
) -> None:
    """整ったワークスペースで問題 0 件を返す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", body="D-1.md"),
        make_item("D-2", depends_on=["D-1"]),
        bodies={"D-1.md": "本文\n"},
    )
    # 実行
    result = run_mindmap("check", "--workspace", str(root))
    # 検証
    assert result.returncode == 0
    assert json.loads(result.stdout) == {"ok": True, "problems": []}


def test_normal_when_problems_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    run_mindmap: RunMindmap,
    snapshot_tree: SnapshotTree,
) -> None:
    """スキーマ違反・参照切れ・本文のずれを全て返し、終了コード 1 で終える（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", depends_on=["D-9"]),
        make_item("D-2", status="完了"),
        make_item("R-1", body="R-1.md"),
        bodies={"X-1.md": "どこからも指されない本文\n"},
    )
    before = snapshot_tree(root)
    # 実行
    result = run_mindmap("check", "--workspace", str(root))
    # 検証
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert _problem_keys(payload["problems"]) == {
        ("broken_ref", "decisions.yaml", "D-1", "depends_on"),
        ("schema", "decisions.yaml", "D-2", "items[1].status"),
        ("missing_body", "research.yaml", "R-1", "items[0].body"),
        ("orphan_body", "docs/X-1.md", None, None),
    }
    assert "D-9" in result.stdout
    assert snapshot_tree(root) == before


def test_normal_when_legacy_format(
    make_item: MakeItem, make_legacy_workspace: MakeLegacyWorkspace, run_mindmap: RunMindmap
) -> None:
    """前の形式の資料は、/mindstella:upgrade で移せることを添えたスキーマ違反として返す（正常系）。"""
    # 準備
    root = make_legacy_workspace(make_item("D-1"), legacy_docs={"A-1": True})
    # 実行
    result = run_mindmap("check", "--workspace", str(root))
    # 検証
    assert result.returncode == 1
    problems = json.loads(result.stdout)["problems"]
    legacy = [row for row in problems if row["file"] == "docs.yaml"]
    assert [row["kind"] for row in legacy] == ["schema", "schema"]
    assert all(
        row["id"] == "A-1" and "/mindstella:upgrade で今の形式に移せます" in row["detail"]
        for row in legacy
    )


def test_error_when_workspace_not_found(tmp_path: Path, run_mindmap: RunMindmap) -> None:
    """mindmap.yaml が無いフォルダを指すとエラーで終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = run_mindmap("check", "--workspace", str(root))
    # 検証
    assert result.returncode == 1
    assert str(root) in result.stderr
    assert result.stdout == ""
