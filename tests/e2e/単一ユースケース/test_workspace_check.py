"""ワークスペースの点検（スキルが参照切れと YAML と本文のずれを洗い出す）の E2E テスト。"""

from __future__ import annotations

import json

from workspace_fixtures import MakeItem, MakeWorkspace, RunMindmap, SnapshotTree


def test_normal_when_clean(
    make_workspace: MakeWorkspace, make_item: MakeItem, run_mindmap: RunMindmap
) -> None:
    """整った記録は、問題が無いと返る（正常系）。"""
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
    """参照切れ・本文の無い項目・項目の無い本文を、全て出す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", depends_on=["D-9"]),
        make_item("R-1", body="R-1.md"),
        bodies={"X-1.md": "どこからも指されない本文\n"},
    )
    before = snapshot_tree(root)
    # 実行
    result = run_mindmap("check", "--workspace", str(root))
    # 検証
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    problems = {
        (row["kind"], row["file"], row["id"], row["key"]): row for row in payload["problems"]
    }
    assert set(problems) == {
        ("broken_ref", "decisions.yaml", "D-1", "depends_on"),
        ("missing_body", "research.yaml", "R-1", "items[0].body"),
        ("orphan_body", "docs/X-1.md", None, None),
    }
    assert "D-9" in problems[("broken_ref", "decisions.yaml", "D-1", "depends_on")]["detail"]
    assert snapshot_tree(root) == before
