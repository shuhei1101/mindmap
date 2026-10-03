"""E2E テストの共通 fixture（ワークスペースと mindmap.py の起動は tests/workspace_fixtures.py）。"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml
from playwright.sync_api import Page
from preview_helpers import BuildPreview, OpenPreview
from workspace_fixtures import MakeVenv, MakeWorkspace, RunMindmap

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
def python_path(make_venv: MakeVenv, run_mindmap: RunMindmap) -> str:
    """依存が揃った環境で `check-env` を流し、ほかのコマンドの起動し直し先の Python を返す。"""
    check_env = run_mindmap("check-env", "--venv", str(make_venv("venv")))
    assert check_env.returncode == 0
    return json.loads(check_env.stdout)["python_path"]


@pytest.fixture
def read_yaml() -> Callable[[Path, str], Any]:
    """ワークスペースの YAML を読んで中身を返す関数を返す。"""

    def _read(root: Path, file_name: str) -> Any:
        """ワークスペースの下の YAML を読む。"""
        return yaml.safe_load((root / file_name).read_text(encoding="utf-8"))

    return _read


# 画面が描き終わるまで待つ上限ミリ秒
RENDER_TIMEOUT_MS = 20_000


@pytest.fixture
def build_preview(make_workspace: MakeWorkspace, run_mindmap: RunMindmap) -> BuildPreview:
    """項目と設定と本文を渡して作成を済ませたワークスペースを `build` し、`preview.html` のパスを返す関数を返す。"""

    def _build(
        *items: dict[str, Any],
        settings: dict[str, Any] | None = None,
        bodies: dict[str, str] | None = None,
    ) -> Path:
        """スキルと同じく `build` を実際に起動して書き出す。失敗したら標準エラーを添えて止める。"""
        root = make_workspace(*items, settings=settings, bodies=bodies)
        result = run_mindmap("build", "--workspace", str(root))
        assert result.returncode == 0, result.stderr
        return root / "preview.html"

    return _build


@pytest.fixture
def open_preview(page: Page) -> OpenPreview:
    """`preview.html` を実際のブラウザでハッシュ付きで開き、画面が描き終わるまで待つ関数を返す。"""

    def _open(
        path: Path, hash_text: str = "", *, width: int | None = None, height: int = 800
    ) -> Page:
        """幅を指定したときはその大きさにしてから開き、本文の領域に中身が入るのを待つ。"""
        if width is not None:
            page.set_viewport_size({"width": width, "height": height})
        page.goto(f"{path.as_uri()}{hash_text}")
        page.wait_for_selector("main#main > *", state="attached", timeout=RENDER_TIMEOUT_MS)
        return page

    return _open
