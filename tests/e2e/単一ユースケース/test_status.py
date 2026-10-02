"""状況の確認（スキルが再開時の状況と次に検討する項目を読む）の E2E テスト。"""

from __future__ import annotations

import json

from workspace_fixtures import MakeItem, MakeWorkspace, RunMindmap, SnapshotTree


def test_normal_when_resume(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    run_mindmap: RunMindmap,
    snapshot_tree: SnapshotTree,
) -> None:
    """要見直し・進行中・再開可能・決定待ち・次の候補を読む（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", title="見直しの問い", status="要見直し"),
        make_item("T-1", title="進めている作業", status="進行中"),
        make_item("D-2", title="再開できる保留", status="保留", depends_on=["D-3"]),
        make_item("D-3", title="決まった問い", status="決定済み"),
        make_item("D-4", title="決定待ちの保留", status="保留", depends_on=["D-5"]),
        make_item("D-5", title="次に決める問い"),
    )
    before = snapshot_tree(root)
    # 実行
    result = run_mindmap("status", "--workspace", str(root))
    # 検証
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["needs_review"] == [{"id": "D-1", "title": "見直しの問い"}]
    assert payload["in_progress"] == [{"id": "T-1", "title": "進めている作業"}]
    assert payload["resumable"] == [{"id": "D-2", "title": "再開できる保留"}]
    assert payload["waiting"] == [
        {"id": "D-4", "title": "決定待ちの保留", "waiting_for": ["D-5"]},
    ]
    assert payload["next"][0]["id"] == "D-5"
    assert snapshot_tree(root) == before


def test_normal_when_next(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    run_mindmap: RunMindmap,
    snapshot_tree: SnapshotTree,
) -> None:
    """前提が揃った未決定を、フェーズ・影響度・後続の件数の順に読む（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", phase="要件", weight="小"),
        make_item("D-2", phase="目的", weight="小"),
        make_item("D-3", phase="要件", weight="大"),
        make_item("D-4", phase="要件", weight="大"),
        make_item("D-5", phase="目的", depends_on=["D-1"]),
        make_item("D-6", depends_on=["D-4"]),
        make_item("D-7", depends_on=["D-6"]),
    )
    before = snapshot_tree(root)
    # 実行
    result = run_mindmap("next", "--workspace", str(root))
    # 検証
    assert result.returncode == 0
    candidates = json.loads(result.stdout)["candidates"]
    assert [row["id"] for row in candidates] == ["D-2", "D-4", "D-3", "D-1"]
    assert [(row["phase"], row["weight"], row["followers"]) for row in candidates] == [
        ("目的", "小", 0),
        ("要件", "大", 2),
        ("要件", "大", 0),
        ("要件", "小", 1),
    ]
    assert snapshot_tree(root) == before
