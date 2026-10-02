"""show（項目の表示）の結合テスト。"""

from __future__ import annotations

import json
from pathlib import Path

from .fixture_types import MakeItem, MakeWorkspace, RunMindmap, SnapshotTree


def test_normal(
    make_workspace: MakeWorkspace, make_item: MakeItem, run_mindmap: RunMindmap
) -> None:
    """項目の中身と本文、参照元をキーごとに返す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", body="D-1.md"),
        make_item("D-2", depends_on=["D-1"], related=["D-1"]),
        make_item("T-1", **{"for": ["D-1"]}),
        bodies={"D-1.md": "## 経緯\n\n本文です。\n"},
    )
    # 実行
    result = run_mindmap("show", "D-1", "--workspace", str(root))
    # 検証
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["item"] == make_item("D-1", body="D-1.md")
    assert payload["kind"] == "decision"
    assert payload["body_markdown"] == "## 経緯\n\n本文です。\n"
    assert payload["referenced_by"] == [
        {"id": "D-2", "key": "depends_on"},
        {"id": "D-2", "key": "related"},
        {"id": "T-1", "key": "for"},
    ]


def test_error_when_workspace_not_found(tmp_path: Path, run_mindmap: RunMindmap) -> None:
    """mindmap.yaml が無いフォルダを指すとエラーで終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = run_mindmap("show", "D-1", "--workspace", str(root))
    # 検証
    assert result.returncode == 1
    assert str(root) in result.stderr


def test_error_when_id_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    run_mindmap: RunMindmap,
    snapshot_tree: SnapshotTree,
) -> None:
    """存在しない ID はエラーで終わる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    # 実行
    result = run_mindmap("show", "D-9", "--workspace", str(root))
    # 検証
    assert result.returncode == 1
    assert "D-9" in result.stderr
    assert snapshot_tree(root) == before
