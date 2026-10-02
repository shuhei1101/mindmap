"""E2E テストの共通 fixture（ワークスペースと mindmap.py の起動は tests/workspace_fixtures.py）。"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from workspace_fixtures import RunMindmap

# スキルの手順が連ねるコマンドを再生する関数（コマンド・引数・中身の JSON を渡し、出力の JSON を返す）
type Replay = Callable[..., dict[str, Any]]


@pytest.fixture
def replay(run_mindmap: RunMindmap) -> Replay:
    """スキルの手順どおりに `--json '{JSON}'` でコマンドを再生し、出力の JSON を返す関数を返す。"""

    def _replay(*args: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        """コマンドを実行し、終了コードが 0 でなければ標準エラーを添えて失敗させ、出力の JSON を返す。"""
        command = list(args)
        # 中身の JSON があれば、手順と同じく --json の引数で渡す
        if data is not None:
            command += ["--json", json.dumps(data, ensure_ascii=False)]
        result = run_mindmap(*command)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    return _replay


@pytest.fixture
def read_yaml() -> Callable[[Path, str], Any]:
    """ワークスペースの YAML を読んで中身を返す関数を返す。"""

    def _read(root: Path, file_name: str) -> Any:
        """ワークスペースの下の YAML を読む。"""
        return yaml.safe_load((root / file_name).read_text(encoding="utf-8"))

    return _read
