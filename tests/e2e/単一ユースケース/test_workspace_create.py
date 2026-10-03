"""ワークスペースの作成（スキルが依存を確かめ、新しいワークスペースを作る）の E2E テスト。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from workspace_fixtures import MakeVenv, RunMindmap, SnapshotTree

# スキルがセットアップのステップで決める設定
SETTINGS: dict[str, Any] = {
    "summary": "要件出しのスキル mindmap を設計する",
    "field": "システム開発",
    "target_label": "システム",
    "phases": ["目的", "要件", "構成"],
    "targets": [{"name": "mindmap", "summary": "話し合いを記録するスキル"}],
    "categories": [{"name": "データ構造", "target": "mindmap", "summary": "YAML の種類とキー"}],
    "goal": {
        "phase": "構成",
        "summary": "作り始められる",
        "deliverables": [{"title": "YAML のスキーマ"}],
    },
    "links": [],
}

# 作られる 7 種類の YAML のファイル名
KIND_YAML_FILES = (
    "decisions.yaml",
    "tasks.yaml",
    "research.yaml",
    "docs.yaml",
    "terms.yaml",
    "notes.yaml",
    "logs.yaml",
)


def _stdin(data: dict[str, Any]) -> str:
    """標準入力に渡す JSON の文字列にする。"""
    return json.dumps(data, ensure_ascii=False)


def _read_kind_yamls(root: Path) -> dict[str, Any]:
    """7 種類の YAML を、ファイル名 → 読んだ値にして返す。"""
    return {
        name: yaml.safe_load((root / name).read_text(encoding="utf-8")) for name in KIND_YAML_FILES
    }


def test_normal(tmp_path: Path, make_venv: MakeVenv, run_mindmap: RunMindmap) -> None:
    """依存が揃っていることを確かめ、新しいワークスペースを作る（正常系）。"""
    # 準備
    venv_dir = make_venv("venv")
    root = tmp_path / "new-workspace"
    # 実行
    check_env = run_mindmap("check-env", "--venv", str(venv_dir))
    python_path = json.loads(check_env.stdout)["python_path"]
    created = run_mindmap(
        "init", "--workspace", str(root), stdin=_stdin(SETTINGS), python=python_path
    )
    checked = run_mindmap("check", "--workspace", str(root), python=python_path)
    # 検証
    assert check_env.returncode == 0
    assert created.returncode == 0
    assert yaml.safe_load((root / "mindmap.yaml").read_text(encoding="utf-8")) == SETTINGS
    assert _read_kind_yamls(root) == {
        "decisions.yaml": {"items": []},
        "tasks.yaml": {"items": []},
        "research.yaml": {"items": []},
        "docs.yaml": {"items": []},
        "terms.yaml": {"items": []},
        "notes.yaml": {"items": []},
        "logs.yaml": {"items": []},
    }
    assert (root / "docs").is_dir()
    assert (root / "handoff").is_dir()
    # 全ての YAML がスキーマに合う（点検がスキーマ違反を出さない）
    assert checked.returncode == 0
    assert json.loads(checked.stdout) == {"ok": True, "problems": []}


def test_error_when_dependency_missing(make_venv: MakeVenv, run_mindmap: RunMindmap) -> None:
    """依存が足りないことを確かめ、足りないライブラリと入れるコマンドを受け取る（異常系）。"""
    # 準備
    venv_dir = make_venv("bare-venv", with_libraries=False)
    # 実行
    result = run_mindmap("check-env", "--venv", str(venv_dir))
    # 検証
    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["packages"][0]["name"] == "PyYAML"
    assert payload["packages"][0]["ok"] is False
    assert payload["packages"][1]["name"] == "jsonschema"
    assert payload["packages"][1]["ok"] is False
    assert "pip install" in payload["install"]


def test_error_when_workspace_exists(
    tmp_path: Path, run_mindmap: RunMindmap, snapshot_tree: SnapshotTree
) -> None:
    """既存のワークスペースのフォルダを渡すと、何も書き換えずに既にあるというエラーになる（異常系）。"""
    # 準備
    root = tmp_path / "workspace"
    run_mindmap("init", "--workspace", str(root), stdin=_stdin(SETTINGS))
    run_mindmap(
        "add",
        "decision",
        "--workspace",
        str(root),
        stdin=_stdin({"title": "最初の問い", "status": "未決定"}),
    )
    before = snapshot_tree(root)
    # 実行
    result = run_mindmap("init", "--workspace", str(root), stdin=_stdin(SETTINGS))
    # 検証
    assert result.returncode != 0
    assert "既にワークスペースがあります" in result.stderr
    assert str(root) in result.stderr
    assert snapshot_tree(root) == before
