"""採用する案の切り替え（スキルが採用する案を切り替え、影響を洗い出す）の E2E テスト。"""

from __future__ import annotations

import json
from typing import Any

import pytest
import yaml
from workspace_fixtures import MakeItem, MakeWorkspace, RunMindmap, SnapshotTree


@pytest.fixture
def two_options() -> list[dict[str, Any]]:
    """案 A（採用）と案 B を持つ検討事項の案を返す。"""
    return [
        {"key": "A", "content": "種類ごとに分ける", "adopted": True},
        {"key": "B", "content": "1 つにまとめる", "adopted": False},
    ]


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    run_mindmap: RunMindmap,
    two_options: list[dict[str, Any]],
) -> None:
    """D-1 の採用する案を B に切り替え、影響を受ける項目を洗い出す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", status="決定済み", options=two_options),
        make_item("D-2", status="決定済み", depends_on=["D-1"]),
        make_item("D-3", depends_on=["D-2"]),
        make_item("T-1", **{"for": ["D-3"]}),
        make_item("D-4", status="決定済み"),
    )
    # 実行
    switched = run_mindmap("adopt", "D-1", "B", "--workspace", str(root))
    affected = run_mindmap("impact", "D-1", "--workspace", str(root))
    # 検証
    assert switched.returncode == 0
    decisions = yaml.safe_load((root / "decisions.yaml").read_text(encoding="utf-8"))["items"]
    options = decisions[0]["options"]
    assert options[0]["adopted"] is False
    assert options[1]["adopted"] is True
    assert affected.returncode == 0
    rows = json.loads(affected.stdout)["affected"]
    assert [row["id"] for row in rows] == ["D-2", "D-3", "T-1"]
    assert [row["via"] for row in rows] == [[], ["D-2"], ["D-2", "D-3"]]


def test_error_when_option_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    run_mindmap: RunMindmap,
    snapshot_tree: SnapshotTree,
    two_options: list[dict[str, Any]],
) -> None:
    """存在しない案を指すと、持っている案を示すエラーになり、何も書き換えない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=two_options))
    before = snapshot_tree(root)
    # 実行
    result = run_mindmap("adopt", "D-1", "Z", "--workspace", str(root))
    # 検証
    assert result.returncode != 0
    assert "Z" in result.stderr
    assert "A" in result.stderr
    assert "B" in result.stderr
    assert snapshot_tree(root) == before
