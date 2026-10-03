"""update（項目の更新）の結合テスト。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .fixture_types import (
    LockDirs,
    MakeItem,
    MakeLegacyWorkspace,
    MakeWorkspace,
    RunMindmap,
    SnapshotTree,
)


def _read_decisions(root: Path) -> list[dict[str, Any]]:
    """ワークスペースの検討事項の並びを読む。"""
    return yaml.safe_load((root / "decisions.yaml").read_text(encoding="utf-8"))["items"]


def test_normal(
    make_workspace: MakeWorkspace, make_item: MakeItem, run_mindmap: RunMindmap
) -> None:
    """検討事項の答えと状態を直し、不要になったキーを消す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", lead="キーを種類ごとに分けるか", weight="大"))
    stdin = json.dumps(
        {"answer": "種類ごとに分ける", "status": "決定済み", "weight": None}, ensure_ascii=False
    )
    # 実行
    result = run_mindmap("update", "D-1", "--workspace", str(root), stdin=stdin)
    # 検証
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["id"] == "D-1"
    assert payload["file"] == "decisions.yaml"
    assert payload["changed"] == ["answer", "status", "weight"]
    updated_item = _read_decisions(root)[0]
    updated = updated_item.pop("updated")
    assert updated > "2026-10-01T00:00:00+00:00"
    assert updated_item == {
        "id": "D-1",
        "title": "D-1の題",
        "status": "決定済み",
        "lead": "キーを種類ごとに分けるか",
        "answer": "種類ごとに分ける",
        "created": "2026-10-01T00:00:00+00:00",
    }


def test_error_when_workspace_not_found(tmp_path: Path, run_mindmap: RunMindmap) -> None:
    """mindmap.yaml が無いフォルダを指すと、何も書かずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = run_mindmap("update", "D-1", "--workspace", str(root), stdin='{"answer": "a"}')
    # 検証
    assert result.returncode == 1
    assert str(root) in result.stderr


def test_error_when_id_not_found(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    run_mindmap: RunMindmap,
    snapshot_tree: SnapshotTree,
) -> None:
    """存在しない ID は直さず、渡した ID を返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    # 実行
    result = run_mindmap("update", "D-9", "--workspace", str(root), stdin='{"answer": "a"}')
    # 検証
    assert result.returncode == 1
    assert "D-9" in result.stderr
    assert snapshot_tree(root) == before


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    run_mindmap: RunMindmap,
    snapshot_tree: SnapshotTree,
) -> None:
    """スクリプトが付けるキー created を渡すと直さない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    stdin = '{"created": "2000-01-01T00:00:00+00:00"}'
    # 実行
    result = run_mindmap("update", "D-1", "--workspace", str(root), stdin=stdin)
    # 検証
    assert result.returncode == 1
    assert "created" in result.stderr
    assert snapshot_tree(root) == before


def test_error_when_write_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    run_mindmap: RunMindmap,
    snapshot_tree: SnapshotTree,
    lock_dirs: LockDirs,
) -> None:
    """書き込めないワークスペースでは何も書き換えず、エラーの行を返す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    before = snapshot_tree(root)
    lock_dirs(root)
    # 実行
    result = run_mindmap("update", "D-1", "--workspace", str(root), stdin='{"answer": "a"}')
    # 検証
    assert result.returncode == 1
    assert result.stderr.startswith("エラー: ")
    assert "Traceback" not in result.stderr
    assert snapshot_tree(root) == before


def test_error_when_legacy_format(
    make_item: MakeItem,
    make_legacy_workspace: MakeLegacyWorkspace,
    run_mindmap: RunMindmap,
    snapshot_tree: SnapshotTree,
) -> None:
    """資料の done が残るワークスペースでは何も書かず、migrate を案内して終わる（異常系）。"""
    # 準備
    root = make_legacy_workspace(make_item("D-1"), legacy_docs={"A-1": True})
    before = snapshot_tree(root)
    # 実行
    result = run_mindmap(
        "update", "D-1", "--workspace", str(root), stdin='{"answer": "種類ごとに分ける"}'
    )
    # 検証
    assert result.returncode == 1
    lines = result.stderr.splitlines()
    assert any(line.startswith("docs.yaml: items[0]") for line in lines)
    assert lines[-1] == "ヒント: 前の版の形式の記録は migrate で今の形式に移せます"
    assert snapshot_tree(root) == before
