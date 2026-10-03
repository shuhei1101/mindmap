"""項目を表で絞り込む（並べ替え・列ごとの絞り込み・ピン留め・表示する列の選択・初期設定に戻す）の E2E テスト。"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page
from preview_helpers import BuildPreview, OpenPreview, row_ids
from workspace_fixtures import MakeItem

# 表が縦に送れる件数にするために足す調査の件数
EXTRA_RESEARCH_COUNT = 40

# 表の縦のスクロールを送る量（px）
SCROLL_TOP = 200

# 横に送る量（px）とピン留めを確かめる幅（px）
SCROLL_LEFT = 150
NARROW_TABLE_WIDTH = 760


def _headers(page: Page) -> dict[str, str | None]:
    """表の見出しの aria-sort を、列の key ごとに返す。"""
    return page.evaluate(
        "Object.fromEntries([...document.querySelectorAll('table.grid thead th')].map(th => [th.querySelector('.th-sort').dataset.sort, th.getAttribute('aria-sort')]))"
    )


def _first_ids(page: Page, count: int) -> list[str]:
    """表の先頭の行の ID を count 件返す。"""
    return row_ids(page)[:count]


def _scroll_table(page: Page) -> float:
    """表を縦に送り、実際に送れた位置を返す（表が収まる件数なら 0）。"""
    return page.evaluate(
        f"(() => {{ const wrap = document.querySelector('.table-wrap'); wrap.scrollTop = {SCROLL_TOP}; return wrap.scrollTop; }})()"
    )


def _table_scroll_top(page: Page) -> float:
    """表の縦のスクロールの位置を返す。"""
    return page.evaluate("document.querySelector('.table-wrap').scrollTop")


def test_normal(
    build_preview: BuildPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """確度の並べ替え・絞り込み・ピン留め・表示する列の選択をして、初期設定に戻す（正常系）。"""
    # 準備
    extras = [
        make_item(f"R-{number}", confidence="中") for number in range(4, 4 + EXTRA_RESEARCH_COUNT)
    ]
    path = build_preview(
        make_item("R-1", confidence="高"),
        make_item("R-2", confidence="低"),
        make_item("R-3", confidence="高"),
        *extras,
        settings=valid_settings,
    )
    page = open_preview(path, "#tab=research", width=NARROW_TABLE_WIDTH)
    page.wait_for_selector("table.grid tbody tr")
    # 並べ替え: 昇順 → 降順 → 既定の並び
    assert _first_ids(page, 3) == ["R-1", "R-2", "R-3"]
    expected = [
        ("ascending", ["R-1", "R-3", "R-4"]),
        ("descending", ["R-2", "R-4", "R-5"]),
        ("none", ["R-1", "R-2", "R-3"]),
    ]
    for aria_sort, first_ids in expected:
        scrolled = _scroll_table(page)
        page.click('button.th-sort[data-sort="confidence"]')
        page.wait_for_function(
            f"document.querySelector('button.th-sort[data-sort=\"confidence\"]').closest('th').getAttribute('aria-sort') === '{aria_sort}'"
        )
        assert _headers(page)["confidence"] == aria_sort
        assert _first_ids(page, 3) == first_ids
        assert _table_scroll_top(page) == scrolled
    # 絞り込み: 選択肢に値ごとの件数が出る。「高」で絞ると R-2 が無く、確度 = 高のチップが出る
    page.click('button[data-popover="filter:confidence"]')
    page.wait_for_selector(".pop:popover-open label")
    counts = page.eval_on_selector_all(
        ".pop:popover-open label",
        "labels => Object.fromEntries(labels.map(l => [l.textContent.replace(/\\d+$/, '').trim(), l.querySelector('.n').textContent]))",
    )
    assert counts == {"高": "2", "中": str(EXTRA_RESEARCH_COUNT), "低": "1"}
    page.click('.pop:popover-open label:has-text("高")')
    page.wait_for_selector(".chips .chip")
    assert page.eval_on_selector_all(".chips .chip", "c => c.map(x => x.textContent)") == ["確度: 高"]
    assert "R-2" not in row_ids(page)
    page.click(".chips >> text=すべて外す")
    page.wait_for_function(
        f"document.querySelectorAll('table.grid tbody tr').length === {EXTRA_RESEARCH_COUNT + 3}"
    )
    # ピン留め: 押した列のボタンだけが押された見た目になり、横に送っても 2 列目までが残る
    scrolled = _scroll_table(page)
    page.click('button[data-pin="title"]')
    page.wait_for_function(
        "document.querySelector('button[data-pin=\"title\"]').getAttribute('aria-pressed') === 'true'"
    )
    pressed = page.eval_on_selector_all(
        "button.pin",
        "buttons => buttons.filter(b => b.getAttribute('aria-pressed') === 'true').map(b => b.dataset.pin)",
    )
    assert pressed == ["title"]
    assert _table_scroll_top(page) == scrolled
    left_before = page.evaluate(
        "document.querySelector('table.grid tbody tr td[data-col=\"1\"]').getBoundingClientRect().left"
    )
    page.evaluate(f"document.querySelector('.table-wrap').scrollLeft = {SCROLL_LEFT}")
    left_after = page.evaluate(
        "document.querySelector('table.grid tbody tr td[data-col=\"1\"]').getBoundingClientRect().left"
    )
    assert left_after == left_before
    # 表示する列: 隠した列が表に無い
    scrolled = _scroll_table(page)
    page.click('button[data-popover="columns"]')
    page.wait_for_selector(".pop:popover-open label")
    page.click('.pop:popover-open label:has-text("結論")')
    page.wait_for_function("document.querySelectorAll('button.th-sort[data-sort=\"conclusion\"]').length === 0")
    assert page.locator('button.th-sort[data-sort="conclusion"]').count() == 0
    assert _table_scroll_top(page) == scrolled
    # 初期設定に戻すと、隠した列が戻り、ピン留めが外れる
    page.click('.pop:popover-open button:has-text("初期設定に戻す")')
    page.wait_for_selector('button.th-sort[data-sort="conclusion"]')
    pressed_after = page.eval_on_selector_all(
        "button.pin",
        "buttons => buttons.filter(b => b.getAttribute('aria-pressed') === 'true').length",
    )
    assert pressed_after == 0


def test_normal_when_no_match(
    build_preview: BuildPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """どの行にも合わない条件では、該当なしと次の操作を書き、条件をすべて外すと行が戻る（正常系）。"""
    # 準備
    path = build_preview(
        make_item("T-1", kind="作業", status="完了"),
        make_item("T-2", kind="調査", status="未着手"),
        settings=valid_settings,
    )
    # 実行（種類 = 作業 かつ 状態 = 未着手 で絞る）
    page = open_preview(path, "#tab=tasks&view=table&f.kind=作業&f.status=未着手")
    page.wait_for_selector("table.grid")
    # 検証
    assert "該当するタスクはありません。別の条件を試してください。" in page.inner_text(".table-block")
    page.click(".chips >> text=すべて外す")
    page.wait_for_function("document.querySelectorAll('table.grid tbody tr[data-id]').length === 2")
    assert row_ids(page) == ["T-1", "T-2"]
    assert page.locator(".chips .chip").count() == 0
