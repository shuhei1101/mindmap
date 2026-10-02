"""goal（ゴール判定）の結合テスト。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .fixture_types import MakeItem, MakeWorkspace, RunMindmap, SnapshotTree


def _goal_settings(
    valid_settings: dict[str, Any], deliverables: list[dict[str, str]]
) -> dict[str, Any]:
    """フェーズが 目的 → 要件 → 構成、ゴールが 要件 までの設定を返す。"""
    return {
        **valid_settings,
        "phases": ["目的", "要件", "構成"],
        "goal": {"phase": "要件", "summary": "要件が決まる", "deliverables": deliverables},
    }


def test_normal_when_reached(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    run_mindmap: RunMindmap,
    snapshot_tree: SnapshotTree,
) -> None:
    """ゴールのフェーズまでが決着し成果物が揃っていれば、届いたと返す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", phase="目的", status="決定済み"),
        make_item("D-2", phase="要件", status="対象外"),
        make_item("D-3", phase="要件", status="取り下げ"),
        make_item("D-4", phase="構成", status="未決定"),
        make_item("A-1", deliverable=True, done=True),
        settings=_goal_settings(valid_settings, [{"title": "要件定義書", "doc": "A-1"}]),
        bodies={"A-1.md": "要件定義書の本文"},
    )
    before = snapshot_tree(root)
    # 実行
    result = run_mindmap("goal", "--workspace", str(root))
    # 検証
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["reached"] is True
    assert payload["goal_phase"] == "要件"
    assert payload["phases"] == ["目的", "要件"]
    # ゴールより後ろの D-4 は残りに入らない
    assert payload["remaining_decisions"] == []
    assert payload["remaining_deliverables"] == []
    # ワークスペースの全てのファイルの中身が、呼ぶ前と同じ
    assert snapshot_tree(root) == before


def test_normal_when_not_reached(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    run_mindmap: RunMindmap,
) -> None:
    """決着していない検討事項と揃っていない成果物を残りとして返す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", phase="目的", status="未決定"),
        make_item("D-2", phase="要件", status="要見直し"),
        make_item("D-3", phase="要件", status="決定済み"),
        make_item("A-1", deliverable=True, done=False),
        settings=_goal_settings(
            valid_settings,
            [{"title": "要件定義書", "doc": "A-1"}, {"title": "用語集"}],
        ),
        bodies={"A-1.md": "要件定義書の本文"},
    )
    # 実行
    result = run_mindmap("goal", "--workspace", str(root))
    # 検証
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["reached"] is False
    assert payload["remaining_decisions"] == [
        {"id": "D-1", "title": "D-1の題", "phase": "目的", "status": "未決定"},
        {"id": "D-2", "title": "D-2の題", "phase": "要件", "status": "要見直し"},
    ]
    assert payload["remaining_deliverables"] == [
        {"title": "要件定義書", "doc": "A-1"},
        {"title": "用語集", "doc": None},
    ]


def test_error_when_workspace_not_found(tmp_path: Path, run_mindmap: RunMindmap) -> None:
    """mindmap.yaml が無いフォルダを指すとエラーで終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = run_mindmap("goal", "--workspace", str(root))
    # 検証
    assert result.returncode == 1
    assert str(root) in result.stderr
