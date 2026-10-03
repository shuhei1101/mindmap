"""結合テストと E2E テストの共通 fixture。"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

# 単体・結合・E2E が共有する fixture（pytest は conftest の名前空間にある fixture を登録する）
from workspace_fixtures import (  # noqa: F401
    make_item,
    make_legacy_item,
    make_legacy_workspace,
    make_venv,
    make_workspace,
    run_mindmap,
    snapshot_tree,
    valid_settings,
)

type RunClaude = Callable[..., subprocess.CompletedProcess[str]]

# claude の 1 コマンドを待つ上限秒数（マーケットプレイスの取り込みを含む）
CLAUDE_COMMAND_TIMEOUT_SEC = 180

# このファイルから見たリポジトリの直下（tests/conftest.py の 1 つ上）
REPO_ROOT_PARENT_DEPTH = 1


@pytest.fixture
def repo_root() -> Path:
    """マーケットプレイスとして登録するリポジトリの作業ツリーの直下を返す。"""
    return Path(__file__).resolve().parents[REPO_ROOT_PARENT_DEPTH]


@pytest.fixture
def run_claude(tmp_path: Path) -> RunClaude:
    """テストごとの空の一時フォルダを設定のフォルダにして claude を実行する関数を返す。"""
    # 利用者の環境を汚さないよう、設定のフォルダをテストごとの空のフォルダに差し替える
    config_dir = tmp_path / "claude-config"
    config_dir.mkdir()
    env = {**os.environ, "CLAUDE_CONFIG_DIR": str(config_dir)}

    def _run(*args: str) -> subprocess.CompletedProcess[str]:
        """claude にサブコマンドを渡して実行し、終了コードが 0 以外なら例外にする。"""
        return subprocess.run(
            ["claude", *args],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=CLAUDE_COMMAND_TIMEOUT_SEC,
            check=True,
        )

    return _run
