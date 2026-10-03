"""資料を読む（成果物を先頭にしたカードとボードで見て、絞り込み、カードから本文を開く）の E2E テスト。"""

from __future__ import annotations

from typing import Any

from preview_helpers import BuildPreview, OpenPreview
from workspace_fixtures import MakeItem

# 見出しと表を持つ資料の本文
SPEC_BODY = """## 仕様の見出し

| 項目 | 値 |
| --- | --- |
| 列 | 3 |
"""


def test_normal(
    build_preview: BuildPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """成果物を先頭にカードを並べ、ボードで状態の列に分けて本文を読み、カードに戻して種類で絞り込み、本文を見出しと表で読む（正常系）。"""
    # 準備
    path = build_preview(
        make_item("A-1", deliverable=False, kind="メモ書き", status="下書き"),
        make_item("A-2", deliverable=True, kind="仕様書", status="完成"),
        settings=valid_settings,
        bodies={"A-1.md": "メモ書きの本文\n", "A-2.md": SPEC_BODY},
    )
    # 実行
    page = open_preview(path, "#tab=docs")
    # 検証（カードの並びと状態）
    cards = page.eval_on_selector_all(".doc-card", "cards => cards.map(c => c.dataset.id)")
    assert cards == ["A-2", "A-1"]
    assert page.locator('.doc-card[data-id="A-2"] .deliv-badge').count() == 1
    assert page.locator('.doc-card[data-id="A-1"] .deliv-badge').count() == 0
    statuses = page.eval_on_selector_all(
        ".doc-card", "cards => cards.map(c => [c.dataset.id, c.querySelector('.st').dataset.st])"
    )
    assert statuses == [["A-2", "完成"], ["A-1", "下書き"]]
    # 表示形式をボードに切り替えると、状態の 3 列に分かれ、確認中の列は 0 件で出る
    page.click('.segment button[data-view="board"]')
    page.wait_for_selector(".board")
    columns = page.eval_on_selector_all(
        ".board section.board-col",
        """cols => cols.map(c => [
            c.getAttribute('aria-label'),
            c.querySelector('h3 .n').textContent,
            [...c.querySelectorAll('.card')].map(k => k.dataset.id),
        ])""",
    )
    assert columns == [["下書き", "1", ["A-1"]], ["確認中", "0", []], ["完成", "1", ["A-2"]]]
    # ボードの A-1 のカードを押すと、詳細パネルに A-1 の本文が出る
    page.click('.board .doc-card[data-id="A-1"]')
    page.wait_for_selector("aside.panel.open")
    page.wait_for_function(
        "document.querySelector('aside.panel .md')?.textContent.includes('メモ書きの本文')"
    )
    # 表示形式をカードに戻すと、成果物を先頭にしたカードが出る
    page.click('.segment button[data-view="cards"]')
    page.wait_for_selector(".doc-grid")
    assert page.eval_on_selector_all(".doc-card", "cards => cards.map(c => c.dataset.id)") == [
        "A-2",
        "A-1",
    ]
    # 種類 = 仕様書で絞り込む
    page.click('button[aria-label="絞り込み"]')
    page.click('.pop label:has-text("仕様書")')
    page.wait_for_function("document.querySelectorAll('.doc-card').length === 1")
    assert page.eval_on_selector_all(".doc-card", "cards => cards.map(c => c.dataset.id)") == ["A-2"]
    chips = page.eval_on_selector_all(".chips .chip", "chips => chips.map(c => c.textContent)")
    assert chips == ["種類: 仕様書"]
    # カードを押すと、詳細パネルに本文が見出しと表で描かれる
    page.click('.doc-card[data-id="A-2"]')
    page.wait_for_selector('aside.panel.open .md [data-md-level="2"]')
    assert page.inner_text('aside.panel .md [data-md-level="2"]') == "仕様の見出し"
    assert page.locator("aside.panel .md table").count() == 1
    cells = page.eval_on_selector_all(
        "aside.panel .md td", "cells => cells.map(c => c.textContent)"
    )
    assert cells == ["列", "3"]
