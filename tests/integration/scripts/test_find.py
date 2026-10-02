"""find（項目の検索）の結合テスト。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from .fixture_types import MakeItem, MakeWorkspace, RunMindmap


@pytest.fixture
def schema_workspace(make_workspace: MakeWorkspace, make_item: MakeItem) -> Path:
    """文字と属性で探すためのワークスペース（D-1・D-2・T-1）を作る。"""
    return make_workspace(
        make_item("D-1", title="スキーマの設計", attrs={"担当": "自分"}),
        make_item(
            "D-2",
            title="別の問い",
            options=[{"key": "A", "content": "スキーマを分ける"}],
        ),
        make_item("T-1", title="作業", attrs={"担当": "自分"}),
    )


def test_normal(schema_workspace: Path, run_mindmap: RunMindmap) -> None:
    """文字と属性で探し、両方に合う項目だけを返す（正常系）。"""
    # 実行
    result = run_mindmap(
        "find", "--workspace", str(schema_workspace), "--text", "スキーマ", "--attr", "担当=自分"
    )
    # 検証
    assert result.returncode == 0
    assert json.loads(result.stdout) == {
        "items": [{"id": "D-1", "kind": "decision", "title": "スキーマの設計", "status": "未決定"}]
    }


def test_normal_when_nested_text(schema_workspace: Path, run_mindmap: RunMindmap) -> None:
    """文字だけで探すと、案の中身に含む項目も返す（正常系）。"""
    # 実行
    result = run_mindmap("find", "--workspace", str(schema_workspace), "--text", "スキーマ")
    # 検証
    assert result.returncode == 0
    items = json.loads(result.stdout)["items"]
    assert [item["id"] for item in items] == ["D-1", "D-2"]


def test_error_when_workspace_not_found(tmp_path: Path, run_mindmap: RunMindmap) -> None:
    """mindmap.yaml が無いフォルダを指すとエラーで終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = run_mindmap("find", "--workspace", str(root))
    # 検証
    assert result.returncode == 1
    assert str(root) in result.stderr
