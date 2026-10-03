"""画面設計『資料』（カード・表）の結合テスト。"""

from __future__ import annotations

from preview_fixture_types import OpenPreview, WriteSamplePreview


def _card_ids(page) -> list[str]:  # noqa: ANN001
    """資料のカードの ID を並びのまま返す。"""
    return page.eval_on_selector_all(".doc-card", "cards => cards.map(c => c.dataset.id)")


def test_cards(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """成果物を先頭に印付きで並べ、資料の状態を出し、押すと詳細を開く（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=docs")
    # 実行
    ids = _card_ids(page)
    badge_cards = page.eval_on_selector_all(
        ".doc-card:has(.deliv-badge)", "cards => cards.map(c => c.dataset.id)"
    )
    statuses = page.eval_on_selector_all(
        ".doc-card .st", "marks => marks.map(m => m.dataset.st)"
    )
    page.click('.doc-card[data-id="A-2"]')
    # 検証
    assert ids == ["A-1", "A-2"]
    assert badge_cards == ["A-1"]
    assert statuses == ["完成", "下書き"]
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "A-2の題"


def test_view_switch(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """表示形式の切り替えは カード・表 の 2 つで、既定はカード。表に切り替えると行を並べる（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=docs")
    views = page.eval_on_selector_all(
        ".segment button", "b => b.map(x => [x.dataset.view, x.getAttribute('aria-pressed')])"
    )
    # 実行
    page.click('.segment button[data-view="table"]')
    page.wait_for_selector("table.grid")
    # 検証
    assert views == [["cards", "true"], ["table", "false"]]
    rows = page.eval_on_selector_all("table.grid tbody tr", "rows => rows.map(r => r.dataset.id)")
    assert rows == ["A-1", "A-2"]
    assert page.inner_text("main h1") == "資料"


def test_card_filter(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """カードの絞り込みのポップオーバーで値を選ぶと、条件のチップが出て、個別とすべてを外せる（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=docs")
    # 実行
    page.click('button[aria-label="絞り込み"]')
    page.click('.pop label:has-text("成果物以外")')
    page.wait_for_selector(".chips .chip")
    # 検証
    assert page.eval_on_selector_all(".chips .chip", "c => c.map(x => x.textContent)") == [
        "成果物: 成果物以外"
    ]
    assert _card_ids(page) == ["A-2"]
    # チップの × で個別に外す
    page.click('.chips .chip button[aria-label="成果物: 成果物以外 の条件を外す"]')
    page.wait_for_function("document.querySelectorAll('.doc-card').length === 2")
    assert _card_ids(page) == ["A-1", "A-2"]


def test_card_filter_clear_all(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """条件が 2 つ以上あるとき、すべて外すで全ての条件を外す（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=docs&f.deliverable=成果物&f.status=完成")
    assert _card_ids(page) == ["A-1"]
    # 実行
    page.click(".chips >> text=すべて外す")
    # 検証
    page.wait_for_function("document.querySelectorAll('.doc-card').length === 2")
    assert page.locator(".chips .chip").count() == 0
