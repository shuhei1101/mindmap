"""プレビューの単体テスト（フロント）の共通 fixture。

tsc が `.ts` から生成した `.js` を `page.add_script_tag` で読み、`page.evaluate` で関数を呼ぶ。
"""

from __future__ import annotations

import base64
import hashlib
import re
import urllib.request
from pathlib import Path
from typing import Any

import pytest
import yaml
from playwright.sync_api import Page

from .fixture_types import LoadLibrary, LoadPreviewScripts, MakeData

# このファイルから見たリポジトリの直下（tests/unit/preview の 3 つ上）
REPO_ROOT_PARENT_DEPTH = 3
REPO_ROOT = Path(__file__).resolve().parents[REPO_ROOT_PARENT_DEPTH]

# tsc が生成した `.js` を置くフォルダ
PREVIEW_DIR = REPO_ROOT / "skills" / "mindmap" / "preview"

# 描画のライブラリの外部ライブラリの設計書を置くフォルダ
LIBRARY_DESIGN_DIR = REPO_ROOT / "dev" / "設計書" / "外部ライブラリ"

# テストのページを開く、仮のオリジン（history.pushState が使える http(s) の URL）
PAGE_URL = "https://preview.test/index.html"

# 起動する `.js`（差し込む順の最後で、読むと画面を描き始めるため、画面の部品のテストでは読まない）
APP_SCRIPT = "app.js"

# 描画のライブラリの取得を待つ上限秒数
LIBRARY_FETCH_TIMEOUT_SEC = 60

# 描画のライブラリの取得結果（URL と本文）。テストをまたいで 1 回だけ取る
type FetchedLibrary = tuple[str, str]
_fetched_libraries: dict[str, FetchedLibrary] = {}


def _fetch_library(name: str) -> FetchedLibrary:
    """外部ライブラリの設計書の版の URL から本文を取り、integrity と突き合わせて返す。"""
    # 取得済みならそのまま返す
    if name in _fetched_libraries:
        return _fetched_libraries[name]
    design = yaml.safe_load((LIBRARY_DESIGN_DIR / f"{name}.yaml").read_text(encoding="utf-8"))
    url = design["version"]["source"]
    expected = re.search(r"sha384-[A-Za-z0-9+/=]+", design["version"]["pinning"])
    assert expected is not None, f"{name} の設計書に integrity がありません"
    with urllib.request.urlopen(url, timeout=LIBRARY_FETCH_TIMEOUT_SEC) as response:  # noqa: S310
        body = response.read()
    # 設計書が固定した版と同じバイトか
    digest = "sha384-" + base64.b64encode(hashlib.sha384(body).digest()).decode("ascii")
    assert digest == expected.group(0), f"{name} の配布物が設計書の integrity と違います"
    _fetched_libraries[name] = (url, body.decode("utf-8"))
    return _fetched_libraries[name]


@pytest.fixture
def preview_page(page: Page) -> Page:
    """空の文書を持つページを開いて返す。history.pushState が使える URL にする。"""
    page.route(
        PAGE_URL,
        lambda route: route.fulfill(
            body="<!doctype html><html><body></body></html>", content_type="text/html"
        ),
    )
    page.goto(PAGE_URL)
    return page


@pytest.fixture
def load_preview_scripts(preview_page: Page) -> LoadPreviewScripts:
    """tsc が生成した `.js` をページに読む関数を返す。"""

    def _load(*, include_app: bool = False) -> None:
        """プレビューの `.js` を、起動する `app.js` を除いて（include_app なら含めて）読む。"""
        paths = sorted(
            path
            for path in PREVIEW_DIR.rglob("*.js")
            if include_app or path.relative_to(PREVIEW_DIR).as_posix() != APP_SCRIPT
        )
        # tsc がまだ `.js` を生成していない
        if not paths:
            raise FileNotFoundError(f"tsc が生成した .js が {PREVIEW_DIR} にありません")
        for path in paths:
            preview_page.add_script_tag(path=str(path))

    return _load


@pytest.fixture
def load_library(preview_page: Page) -> LoadLibrary:
    """描画のライブラリを、配信元への要求に本文を返す形でページに読む関数を返す。"""

    def _load(name: str) -> None:
        """設計書の版のライブラリを `page.route` で返し、script 要素で読む。"""
        url, body = _fetch_library(name)
        preview_page.route(
            url, lambda route: route.fulfill(body=body, content_type="application/javascript")
        )
        preview_page.add_script_tag(url=url)

    return _load


@pytest.fixture
def make_data(valid_settings: dict[str, Any]) -> MakeData:
    """埋め込みのデータ（`mindmap-data` の中身）を作る関数を返す。"""

    def _make(
        *, settings: dict[str, Any] | None = None, next_ids: list[str] | None = None, **kinds: Any
    ) -> dict[str, Any]:
        """種類ごとの項目（decisions=[...] など）と、次の候補の ID を渡して埋め込みのデータを返す。"""
        data: dict[str, Any] = {
            "settings": valid_settings if settings is None else settings,
            "decisions": [],
            "tasks": [],
            "research": [],
            "docs": [],
            "terms": [],
            "notes": [],
            "logs": [],
            "bodies": {},
            "derived": {
                "next": [
                    {
                        "id": item_id,
                        "title": f"{item_id}の題",
                        "phase": None,
                        "weight": None,
                        "followers": 0,
                    }
                    for item_id in (next_ids or [])
                ],
                "goal": {
                    "reached": False,
                    "goal_phase": "構成",
                    "phases": [],
                    "remaining_decisions": [],
                    "remaining_deliverables": [],
                    "phase_progress": [],
                },
                "progress": [],
            },
            "built_at": "2026-10-02T08:00:00+00:00",
        }
        data.update(kinds)
        return data

    return _make
