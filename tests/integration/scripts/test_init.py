"""init（ワークスペースの作成）の結合テスト。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .fixture_types import LockDirs, MakeWorkspace, RunMindmap, SnapshotTree

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


def _read_kind_yamls(root: Path) -> dict[str, Any]:
    """7 種類の YAML を、ファイル名 → 読んだ値にして返す。"""
    return {
        name: yaml.safe_load((root / name).read_text(encoding="utf-8")) for name in KIND_YAML_FILES
    }


def _stdin(settings: dict[str, Any]) -> str:
    """設定を標準入力に渡す JSON の文字列にする。"""
    return json.dumps(settings, ensure_ascii=False)


def test_normal(tmp_path: Path, run_mindmap: RunMindmap, valid_settings: dict[str, Any]) -> None:
    """設定を渡して空のワークスペースを作る（正常系）。"""
    # 準備
    root = tmp_path / "new-workspace"
    # 実行
    result = run_mindmap("init", "--workspace", str(root), stdin=_stdin(valid_settings))
    # 検証
    assert result.returncode == 0
    assert yaml.safe_load((root / "mindmap.yaml").read_text(encoding="utf-8")) == valid_settings
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
    assert (root / "release").is_dir()
    payload = json.loads(result.stdout)
    assert payload["workspace"] == str(root)
    assert set(payload["files"]) == {"mindmap.yaml", *KIND_YAML_FILES, "docs/", "release/"}


def test_error_when_workspace_exists(
    make_workspace: MakeWorkspace,
    run_mindmap: RunMindmap,
    snapshot_tree: SnapshotTree,
    valid_settings: dict[str, Any],
) -> None:
    """mindmap.yaml があるフォルダには作らず、何も書き換えない（異常系）。"""
    # 準備
    root = make_workspace()
    before = snapshot_tree(root)
    # 実行
    result = run_mindmap("init", "--workspace", str(root), stdin=_stdin(valid_settings))
    # 検証
    assert result.returncode == 1
    assert str(root) in result.stderr
    assert snapshot_tree(root) == before


def test_error_when_settings_mismatch(
    tmp_path: Path, run_mindmap: RunMindmap, valid_settings: dict[str, Any]
) -> None:
    """フェーズが無い設定では作らず、フォルダも作らない（異常系）。"""
    # 準備
    root = tmp_path / "new-workspace"
    del valid_settings["phases"]
    # 実行
    result = run_mindmap("init", "--workspace", str(root), stdin=_stdin(valid_settings))
    # 検証
    assert result.returncode == 1
    assert "mindmap.yaml" in result.stderr
    assert "phases" in result.stderr
    assert not root.exists()


def test_error_when_write_fails(
    tmp_path: Path,
    run_mindmap: RunMindmap,
    lock_dirs: LockDirs,
    valid_settings: dict[str, Any],
) -> None:
    """書き込めない場所には作らず、エラーの行を返す（異常系）。"""
    # 準備
    locked = tmp_path / "locked"
    locked.mkdir()
    lock_dirs(locked)
    root = locked / "new-workspace"
    # 実行
    result = run_mindmap("init", "--workspace", str(root), stdin=_stdin(valid_settings))
    # 検証
    assert result.returncode == 1
    assert result.stderr.startswith("エラー: ")
    assert "Traceback" not in result.stderr
    assert not root.exists()
