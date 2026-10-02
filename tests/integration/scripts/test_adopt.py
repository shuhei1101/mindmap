"""adopt（採用する案の切り替え）の結合テスト。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from .fixture_types import LockDirs, MakeItem, MakeWorkspace, RunMindmap, SnapshotTree


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
    """案 A から案 B へ採用を切り替える（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", status="決定済み", answer="案 A に決めた", options=two_options)
    )
    # 実行
    result = run_mindmap("adopt", "D-1", "B", "--workspace", str(root))
    # 検証
    assert result.returncode == 0
    assert json.loads(result.stdout) == {"id": "D-1", "adopted": "B", "previous": "A"}
    adopted = yaml.safe_load((root / "decisions.yaml").read_text(encoding="utf-8"))["items"][0]
    assert adopted["options"] == [
        {"key": "A", "content": "種類ごとに分ける", "adopted": False},
        {"key": "B", "content": "1 つにまとめる", "adopted": True},
    ]
    assert adopted["status"] == "決定済み"
    assert adopted["answer"] == "案 A に決めた"


def test_error_when_workspace_not_found(tmp_path: Path, run_mindmap: RunMindmap) -> None:
    """mindmap.yaml が無いフォルダを指すと、何も書かずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = run_mindmap("adopt", "D-1", "B", "--workspace", str(root))
    # 検証
    assert result.returncode == 1
    assert str(root) in result.stderr


def test_error_when_id_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    run_mindmap: RunMindmap,
    snapshot_tree: SnapshotTree,
) -> None:
    """存在しない検討事項は切り替えない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    # 実行
    result = run_mindmap("adopt", "D-9", "A", "--workspace", str(root))
    # 検証
    assert result.returncode == 1
    assert "D-9" in result.stderr
    assert snapshot_tree(root) == before


def test_error_when_option_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    run_mindmap: RunMindmap,
    snapshot_tree: SnapshotTree,
    two_options: list[dict[str, Any]],
) -> None:
    """検討事項が持たない記号は切り替えず、持っている記号を返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=two_options))
    before = snapshot_tree(root)
    # 実行
    result = run_mindmap("adopt", "D-1", "Z", "--workspace", str(root))
    # 検証
    assert result.returncode == 1
    assert "Z" in result.stderr
    assert "A" in result.stderr
    assert "B" in result.stderr
    assert snapshot_tree(root) == before


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    run_mindmap: RunMindmap,
    snapshot_tree: SnapshotTree,
    two_options: list[dict[str, Any]],
) -> None:
    """手で崩した YAML が残っていると切り替えず、合わない箇所を返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=two_options), make_item("D-2", status="完了"))
    before = snapshot_tree(root)
    # 実行
    result = run_mindmap("adopt", "D-1", "B", "--workspace", str(root))
    # 検証
    assert result.returncode == 1
    assert "decisions.yaml: items[1].status:" in result.stderr
    assert snapshot_tree(root) == before


def test_error_when_write_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    run_mindmap: RunMindmap,
    snapshot_tree: SnapshotTree,
    lock_dirs: LockDirs,
    two_options: list[dict[str, Any]],
) -> None:
    """書き込めないワークスペースでは切り替えず、エラーの行を返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", options=two_options))
    before = snapshot_tree(root)
    lock_dirs(root)
    # 実行
    result = run_mindmap("adopt", "D-1", "B", "--workspace", str(root))
    # 検証
    assert result.returncode == 1
    assert result.stderr.startswith("エラー: ")
    assert "Traceback" not in result.stderr
    assert snapshot_tree(root) == before
