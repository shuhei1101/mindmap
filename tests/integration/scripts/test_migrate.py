"""migrate（記録の形式の移行）の結合テスト。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .fixture_types import (
    LockDirs,
    MakeItem,
    MakeLegacyWorkspace,
    RunMindmap,
    SnapshotTree,
)

# 渡す題名
SUMMARY = "要件出しのスキルを設計する"


def _read_docs(root: Path) -> list[dict[str, Any]]:
    """ワークスペースの資料の並びを読む。"""
    return yaml.safe_load((root / "docs.yaml").read_text(encoding="utf-8"))["items"]


def test_normal(
    make_item: MakeItem, make_legacy_workspace: MakeLegacyWorkspace, run_mindmap: RunMindmap
) -> None:
    """題名を足し、資料の done を status に移す（正常系）。"""
    # 準備
    root = make_legacy_workspace(
        make_item("A-3", status="確認中"),
        legacy_docs={"A-1": True, "A-2": False},
        without_summary=True,
    )
    before = {item["id"]: item for item in _read_docs(root)}
    # 実行
    result = run_mindmap("migrate", "--workspace", str(root), "--summary", SUMMARY)
    # 検証
    assert result.returncode == 0
    assert json.loads(result.stdout)["migrated"] == [
        {"id": None, "file": "mindmap.yaml", "change": "summary を足した"},
        {"id": "A-1", "file": "docs.yaml", "change": "done: true → status: 完成"},
        {"id": "A-2", "file": "docs.yaml", "change": "done: false → status: 下書き"},
    ]
    settings = yaml.safe_load((root / "mindmap.yaml").read_text(encoding="utf-8"))
    assert settings["summary"] == SUMMARY
    after = {item["id"]: item for item in _read_docs(root)}
    assert after["A-1"]["status"] == "完成"
    assert after["A-2"]["status"] == "下書き"
    assert "done" not in after["A-1"]
    assert "done" not in after["A-2"]
    assert after["A-1"]["updated"] == before["A-1"]["updated"]
    assert after["A-2"]["updated"] == before["A-2"]["updated"]
    assert after["A-3"] == before["A-3"]
    # 続けて check がスキーマ違反を返さない
    checked = json.loads(run_mindmap("check", "--workspace", str(root)).stdout)
    assert [problem for problem in checked["problems"] if problem["kind"] == "schema"] == []


def test_normal_when_nothing_to_migrate(
    make_item: MakeItem,
    make_legacy_workspace: MakeLegacyWorkspace,
    run_mindmap: RunMindmap,
    snapshot_tree: SnapshotTree,
) -> None:
    """今の形式のワークスペースでは何も書かない（正常系）。"""
    # 準備
    root = make_legacy_workspace(make_item("A-1", status="完成"))
    before = snapshot_tree(root)
    # 実行
    result = run_mindmap("migrate", "--workspace", str(root))
    # 検証
    assert result.returncode == 0
    assert json.loads(result.stdout)["migrated"] == []
    assert snapshot_tree(root) == before


def test_error_when_workspace_not_found(
    tmp_path: Path, run_mindmap: RunMindmap, snapshot_tree: SnapshotTree
) -> None:
    """mindmap.yaml が無いフォルダを指すと、何も書かずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = run_mindmap("migrate", "--workspace", str(root))
    # 検証
    assert result.returncode == 1
    assert str(root) in result.stderr
    assert snapshot_tree(root) == {}


def test_error_when_schema_mismatch(
    make_item: MakeItem,
    make_legacy_workspace: MakeLegacyWorkspace,
    run_mindmap: RunMindmap,
    snapshot_tree: SnapshotTree,
) -> None:
    """移してもスキーマに合わないと、何も書かずに終わる（異常系）。"""
    # 準備
    root = make_legacy_workspace(make_item("D-1", status="完了"), legacy_docs={"A-1": True})
    before = snapshot_tree(root)
    # 実行
    result = run_mindmap("migrate", "--workspace", str(root))
    # 検証
    assert result.returncode == 1
    assert any(
        line.startswith("decisions.yaml: items[0].status:") for line in result.stderr.splitlines()
    )
    assert snapshot_tree(root) == before


def test_error_when_write_fails(
    make_legacy_workspace: MakeLegacyWorkspace,
    run_mindmap: RunMindmap,
    snapshot_tree: SnapshotTree,
    lock_dirs: LockDirs,
) -> None:
    """書き込めないワークスペースでは、前の mindmap.yaml・docs.yaml を残して終わる（異常系）。"""
    # 準備
    root = make_legacy_workspace(legacy_docs={"A-1": True}, without_summary=True)
    before = snapshot_tree(root)
    lock_dirs(root)
    # 実行
    result = run_mindmap("migrate", "--workspace", str(root), "--summary", SUMMARY)
    # 検証
    assert result.returncode == 1
    assert result.stderr.startswith("エラー: ")
    assert "Traceback" not in result.stderr
    assert snapshot_tree(root) == before


def test_error_when_summary_required(
    make_legacy_workspace: MakeLegacyWorkspace,
    run_mindmap: RunMindmap,
    snapshot_tree: SnapshotTree,
) -> None:
    """題名を持たないワークスペースで --summary を渡さないと、何も書かずに終わる（異常系）。"""
    # 準備
    root = make_legacy_workspace(legacy_docs={"A-1": True}, without_summary=True)
    before = snapshot_tree(root)
    # 実行
    result = run_mindmap("migrate", "--workspace", str(root))
    # 検証
    assert result.returncode == 2
    assert "--summary" in result.stderr
    assert snapshot_tree(root) == before
