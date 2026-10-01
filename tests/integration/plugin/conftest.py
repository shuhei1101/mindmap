"""プラグインの結合テストの共通 fixture。"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

type RunClaude = Callable[..., subprocess.CompletedProcess[str]]

# claude の 1 コマンドを待つ上限秒数（マーケットプレイスの取り込みを含む）
CLAUDE_COMMAND_TIMEOUT_SEC = 180

# このファイルから見たリポジトリの直下（tests/integration/plugin/conftest.py の 3 つ上）
REPO_ROOT_PARENT_DEPTH = 3


@pytest.fixture
def repo_root() -> Path:
    """マーケットプレイスとして登録するリポジトリの直下を返す。"""
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
