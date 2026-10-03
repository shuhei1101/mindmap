"""screens/docs.ts（資料の画面）の単体テスト。"""

from __future__ import annotations

from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts, MakeItem


def test_order_docs(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, make_item: MakeItem
) -> None:
    """納品物が先（正常系）。"""
    # 準備
    docs = [
        make_item("A-1", deliverable=False),
        make_item("A-3", deliverable=True),
        make_item("A-2", deliverable=True),
    ]
    load_preview_scripts()
    # 実行
    ids = preview_page.evaluate(
        "(docs) => MindmapPreview.orderDocs(docs).map((doc) => doc.id)", docs
    )
    # 検証
    assert ids == ["A-2", "A-3", "A-1"]
