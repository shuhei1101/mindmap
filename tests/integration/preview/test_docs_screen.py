"""画面設計『資料』（カード・ボード・表）の結合テスト。"""

from __future__ import annotations

from typing import Any

from preview_fixture_types import OpenPreview, WritePreview, WriteSamplePreview
from workspace_fixtures import MakeItem


def _card_ids(page) -> list[str]:
    """資料のカードの ID を並びのまま返す。"""
    return page.eval_on_selector_all(".doc-card", "cards => cards.map(c => c.dataset.id)")


def test_cards(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """納品物を先頭に印付きで並べ、資料の状態を出し、押すと詳細を開く（正常系）。"""
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
    """表示形式の切り替えは カード・ボード・表 の 3 つで、既定はカード。表に切り替えると行を並べる（正常系）。"""
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
    assert views == [["cards", "true"], ["board", "false"], ["table", "false"]]
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
    page.click('.pop label:has-text("納品物以外")')
    page.wait_for_selector(".chips .chip")
    # 検証
    assert page.eval_on_selector_all(".chips .chip", "c => c.map(x => x.textContent)") == [
        "納品物: 納品物以外"
    ]
    assert _card_ids(page) == ["A-2"]
    # チップの × で個別に外す
    page.click('.chips .chip button[aria-label="納品物: 納品物以外 の条件を外す"]')
    page.wait_for_function("document.querySelectorAll('.doc-card').length === 2")
    assert _card_ids(page) == ["A-1", "A-2"]


def test_card_filter_clear_all(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """条件が 2 つ以上あるとき、すべて外すで全ての条件を外す（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=docs&f.deliverable=納品物&f.status=完成")
    assert _card_ids(page) == ["A-1"]
    # 実行
    page.click(".chips >> text=すべて外す")
    # 検証
    page.wait_for_function("document.querySelectorAll('.doc-card').length === 2")
    assert page.locator(".chips .chip").count() == 0


def _board_columns(page) -> list[list[Any]]:
    """ボードの列を、状態・件数・カードの ID の並びで返す。"""
    return page.eval_on_selector_all(
        ".board section.board-col",
        """cols => cols.map(c => [
            c.getAttribute('aria-label'),
            c.querySelector('h3 .n').textContent,
            [...c.querySelectorAll('.card')].map(k => k.dataset.id),
        ])""",
    )


def test_view_switch_to_board(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """ボードに切り替えると状態の列を並べ、押されている形式がボードになる（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=docs")
    # 実行
    page.click('.segment button[data-view="board"]')
    page.wait_for_selector(".board")
    # 検証
    pressed = page.eval_on_selector_all(
        ".segment button", "b => b.map(x => [x.dataset.view, x.getAttribute('aria-pressed')])"
    )
    assert pressed == [["cards", "false"], ["board", "true"], ["table", "false"]]
    assert page.locator(".doc-grid").count() == 0


def test_board(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """下書き・確認中・完成の 3 列に資料を並べ、0 件の列も出し、カードに状態の印を出さない（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=docs&view=board")
    # 実行
    columns = _board_columns(page)
    marks = page.locator(".board .doc-card .st").count()
    badge_cards = page.eval_on_selector_all(
        ".board .doc-card:has(.deliv-badge)", "cards => cards.map(c => c.dataset.id)"
    )
    # 検証
    assert columns == [["下書き", "1", ["A-2"]], ["確認中", "0", []], ["完成", "1", ["A-1"]]]
    assert page.locator(".board section.board-col").nth(1).inner_text().endswith("なし")
    assert marks == 0
    assert badge_cards == ["A-1"]


def test_board_order(
    write_preview: WritePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    sample_settings: dict[str, Any],
) -> None:
    """列の中は納品物を先頭に連番の順に並べる（正常系）。"""
    # 準備
    path = write_preview(
        make_item("A-1", deliverable=False, status="完成", kind="文書"),
        make_item("A-2", deliverable=False, status="完成", kind="文書"),
        make_item("A-3", deliverable=True, status="完成", kind="文書"),
        make_item("A-4", deliverable=True, status="下書き", kind="文書"),
        make_item("A-5", deliverable=False, status="下書き", kind="文書"),
        settings=sample_settings,
    )
    page = open_preview(path, "#tab=docs&view=board")
    # 実行
    columns = _board_columns(page)
    # 検証
    assert columns == [
        ["下書き", "2", ["A-4", "A-5"]],
        ["確認中", "0", []],
        ["完成", "3", ["A-3", "A-1", "A-2"]],
    ]


def test_board_open_detail(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """カードを押すと詳細を開き、開いているカードに selected が付く（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=docs&view=board")
    # 実行
    page.click('.board .doc-card[data-id="A-2"]')
    # 検証
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "A-2の題"
    selected = page.eval_on_selector_all(
        ".board .doc-card.selected", "cards => cards.map(c => c.dataset.id)"
    )
    assert selected == ["A-2"]


def test_board_filter(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """ボードでも絞り込みのポップオーバーで値を選ぶと、条件のチップが出て、列のカードが絞られ、外すと戻る（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=docs&view=board")
    # 実行
    page.click('button[aria-label="絞り込み"]')
    page.click('.pop label:has-text("納品物以外")')
    page.wait_for_selector(".chips .chip")
    # 検証
    assert page.eval_on_selector_all(".chips .chip", "c => c.map(x => x.textContent)") == [
        "納品物: 納品物以外"
    ]
    assert _board_columns(page) == [
        ["下書き", "1", ["A-2"]],
        ["確認中", "0", []],
        ["完成", "0", []],
    ]
    # チップの × で外すと全ての列のカードが戻る
    page.click('.chips .chip button[aria-label="納品物: 納品物以外 の条件を外す"]')
    page.wait_for_function("document.querySelectorAll('.board .doc-card').length === 2")
    assert _board_columns(page) == [
        ["下書き", "1", ["A-2"]],
        ["確認中", "0", []],
        ["完成", "1", ["A-1"]],
    ]


def test_board_filter_from_url(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """URL の条件でボードを開くと、カードと同じ条件で絞られ、チップが出る（正常系）。"""
    # 準備・実行
    path = write_sample_preview()
    page = open_preview(path, "#tab=docs&view=board&f.status=完成")
    # 検証
    assert _board_columns(page) == [
        ["下書き", "0", []],
        ["確認中", "0", []],
        ["完成", "1", ["A-1"]],
    ]
    assert page.eval_on_selector_all(".chips .chip", "c => c.map(x => x.textContent)") == [
        "状態: 完成"
    ]
