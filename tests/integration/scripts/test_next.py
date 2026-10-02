"""next（次の候補）の結合テスト。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from .fixture_types import MakeItem, MakeWorkspace, RunMindmap


@pytest.fixture
def next_workspace(make_workspace: MakeWorkspace, make_item: MakeItem) -> Path:
    """前提が揃った未決定 D-1〜D-4 と、未決定に依存する D-5〜D-7 を持つワークスペースを作る。"""
    return make_workspace(
        make_item("D-1", phase="要件", weight="小"),
        make_item("D-2", phase="目的", weight="小"),
        make_item("D-3", phase="要件", weight="大"),
        make_item("D-4", phase="要件", weight="大"),
        make_item("D-5", depends_on=["D-1"]),
        make_item("D-6", depends_on=["D-4"]),
        make_item("D-7", depends_on=["D-6"]),
    )


def test_normal(next_workspace: Path, run_mindmap: RunMindmap) -> None:
    """前提が揃った未決定を決めた順に並べ、前提が揃っていないものを外す（正常系）。"""
    # 実行
    result = run_mindmap("next", "--workspace", str(next_workspace))
    # 検証
    assert result.returncode == 0
    candidates = json.loads(result.stdout)["candidates"]
    assert [(row["id"], row["followers"]) for row in candidates] == [
        ("D-2", 0),
        ("D-4", 2),
        ("D-3", 0),
        ("D-1", 1),
    ]


def test_normal_when_limited(next_workspace: Path, run_mindmap: RunMindmap) -> None:
    """--limit で先頭から指定した件数だけ返す（正常系）。"""
    # 実行
    result = run_mindmap("next", "--workspace", str(next_workspace), "--limit", "2")
    # 検証
    assert result.returncode == 0
    candidates = json.loads(result.stdout)["candidates"]
    assert [row["id"] for row in candidates] == ["D-2", "D-4"]


def test_error_when_workspace_not_found(tmp_path: Path, run_mindmap: RunMindmap) -> None:
    """mindmap.yaml が無いフォルダを指すとエラーで終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = run_mindmap("next", "--workspace", str(root))
    # 検証
    assert result.returncode == 1
    assert str(root) in result.stderr
