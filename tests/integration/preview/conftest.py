"""プレビューの結合テストの共通 fixture。

`build` で書き出した `preview.html` を file:// で開き、ハッシュで画面を指す。
描画のライブラリと文字は、配信元（jsDelivr・Google Fonts）から読む。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Page
from preview_fixture_types import (
    BODY_WITH_DIAGRAM,
    MAIN_SELECTOR,
    OpenPreview,
    WritePreview,
    WriteSamplePreview,
)
from workspace_fixtures import MakeItem, MakeWorkspace, RunMindmap

# 画面が描き終わるまで待つ上限ミリ秒
RENDER_TIMEOUT_MS = 15_000


@pytest.fixture
def write_preview(make_workspace: MakeWorkspace, run_mindmap: RunMindmap) -> WritePreview:
    """項目と設定を渡して `build` し、書き出した `preview.html` のパスを返す関数を返す。"""

    def _write(
        *items: dict[str, Any],
        settings: dict[str, Any] | None = None,
        bodies: dict[str, str] | None = None,
    ) -> Path:
        """ワークスペースを作って書き出す。`build` が失敗したらテストを止める。"""
        root = make_workspace(*items, settings=settings, bodies=bodies)
        result = run_mindmap("build", "--workspace", str(root))
        assert result.returncode == 0, result.stderr
        return root / "preview.html"

    return _write


@pytest.fixture
def sample_settings(valid_settings: dict[str, Any]) -> dict[str, Any]:
    """カテゴリー 2 つ・成果物 1 つを持つ設定を返す（概要の進み具合・成果物のチェックリスト用）。"""
    return {
        **valid_settings,
        "categories": [
            {"name": "データ構造", "target": "mindmap", "summary": "YAML の種類とキー"},
            {"name": "画面", "target": "mindmap", "summary": "プレビューの画面"},
        ],
        "goal": {
            "phase": "要件",
            "summary": "要件が決まる",
            "deliverables": [{"title": "YAML のスキーマ", "doc": "A-1"}],
        },
    }


@pytest.fixture
def sample_items(make_item: MakeItem) -> list[dict[str, Any]]:
    """全ての種類を 1 件以上持ち、状態・前提・案・本文がそろった項目を返す。"""
    return [
        make_item(
            "D-1",
            status="決定済み",
            phase="目的",
            category="データ構造",
            target="mindmap",
            answer="種類ごとに分ける",
        ),
        make_item(
            "D-2",
            status="未決定",
            phase="要件",
            category="データ構造",
            target="mindmap",
            depends_on=["D-1"],
            weight="大",
            lead="キーをどう持つか",
        ),
        make_item(
            "D-3",
            status="要見直し",
            phase="要件",
            category="画面",
            target="mindmap",
            body="D-3.md",
            options=[
                {"key": "A", "content": "表で見せる", "pros": "並べやすい", "adopted": True},
                {"key": "B", "content": "カードで見せる", "cons": ["数が多いと長い"]},
            ],
        ),
        make_item("D-4", status="保留", phase="構成", category="画面", depends_on=["D-2"]),
        make_item("D-5", status="未決定", phase="構成", category="画面", depends_on=["D-1"]),
        make_item("T-1", status="進行中", **{"for": ["D-2"]}),
        make_item("T-2", status="未着手"),
        make_item("T-3", status="完了"),
        make_item("R-1", confidence="高", conclusion="結論の文"),
        make_item("A-1", deliverable=True, status="完成", kind="文書"),
        make_item("A-2", deliverable=False, status="下書き", body="A-2.md"),
        make_item("G-1", meaning="用語の意味"),
        make_item("N-1", content="メモの中身"),
        make_item("L-1", date="2026-10-01"),
    ]


@pytest.fixture
def sample_bodies() -> dict[str, str]:
    """サンプルの項目が指す本文（`docs/` のファイル名 → 本文）。"""
    return {
        "D-3.md": BODY_WITH_DIAGRAM,
        "A-1.md": "# 成果物の本文\n",
        "A-2.md": "下書きの本文\n",
    }


@pytest.fixture
def write_sample_preview(
    write_preview: WritePreview,
    sample_items: list[dict[str, Any]],
    sample_settings: dict[str, Any],
    sample_bodies: dict[str, str],
) -> WriteSamplePreview:
    """サンプルの記録を書き出した `preview.html` のパスを返す関数を返す。"""

    def _write() -> Path:
        """サンプルの項目・設定・本文で書き出す。"""
        return write_preview(*sample_items, settings=sample_settings, bodies=sample_bodies)

    return _write


@pytest.fixture
def open_preview(page: Page) -> OpenPreview:
    """`preview.html` をハッシュ付きで開き、画面が描き終わるまで待つ関数を返す。"""

    def _open(path: Path, hash_text: str = "") -> Page:
        """file:// の URL にハッシュを付けて開き、本文の領域に中身が入るのを待つ。"""
        page.goto(f"{path.as_uri()}{hash_text}")
        page.wait_for_selector(f"{MAIN_SELECTOR} > *", state="attached", timeout=RENDER_TIMEOUT_MS)
        return page

    return _open
