"""部品設計『表』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from storybook_fixture_types import OpenStory

# 長いタイトルが折り返す幅
NARROW_SIZE = {"width": 640, "height": 600}

# 見出しの aria-sort を列の key で読む
SORT_SCRIPT = """() => Object.fromEntries([...document.querySelectorAll('table.grid thead th')].map(
    th => [th.querySelector('.th-sort').dataset.sort, th.getAttribute('aria-sort')]
))"""


def test_default(open_story: OpenStory) -> None:
    """通常。全ての見出しの aria-sort が none で、行は元の並び（正常系）。"""
    # 準備・実行
    page = open_story("preview-table--default")
    # 検証
    assert set(page.evaluate(SORT_SCRIPT).values()) == {"none"}
    rows = page.eval_on_selector_all("table.grid tbody tr", "rows => rows.map(r => r.dataset.id)")
    assert rows == ["D-1", "D-2", "D-3", "D-4"]


def test_sorted_asc(open_story: OpenStory) -> None:
    """タイトルで昇順。見出しが aria-sort="ascending" を持つ（正常系）。"""
    # 準備・実行
    page = open_story("preview-table--sorted-asc")
    # 検証
    sort = page.evaluate(SORT_SCRIPT)
    assert sort["title"] == "ascending"
    assert {value for key, value in sort.items() if key != "title"} == {"none"}


def test_sorted_desc(open_story: OpenStory) -> None:
    """タイトルで降順。見出しが aria-sort="descending" を持つ（正常系）。"""
    # 準備・実行
    page = open_story("preview-table--sorted-desc")
    # 検証
    assert page.evaluate(SORT_SCRIPT)["title"] == "descending"


def test_filtered(open_story: OpenStory) -> None:
    """確度 = 高で絞り込み中。条件のチップとすべて外すを並べ、絞り込みの道具を押された見た目にする（正常系）。"""
    # 準備・実行
    page = open_story("preview-table--filtered")
    # 検証
    assert page.eval_on_selector_all(".chips .chip", "c => c.map(x => x.textContent)") == ["確度: 高"]
    assert page.locator(".chips >> text=すべて外す").count() == 1
    assert page.get_attribute('button[aria-label="確度で絞り込み"]', "aria-pressed") == "true"
    rows = page.eval_on_selector_all("table.grid tbody tr", "rows => rows.map(r => r.dataset.id)")
    assert rows == ["D-1", "D-3"]


def test_pinned(open_story: OpenStory) -> None:
    """ID の列までピン留め。押した列のボタンだけが押された見た目で、固定した列の境に影（正常系）。"""
    # 準備・実行
    page = open_story("preview-table--pinned")
    # 検証
    pressed = page.eval_on_selector_all(
        "button.pin", "buttons => buttons.filter(b => b.getAttribute('aria-pressed') === 'true').map(b => b.dataset.pin)"
    )
    assert pressed == ["id"]
    assert page.locator("table.grid .pinned").count() > 0


def test_long_title(open_story: OpenStory) -> None:
    """長いタイトルは折り返し、ほかの列は崩れない（正常系）。"""
    # 準備・実行
    page = open_story("preview-table--long-title")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 640")
    # 検証
    heights = page.evaluate(
        "(() => { const rows = [...document.querySelectorAll('table.grid tbody tr')]; return rows.map(r => Math.round(r.getBoundingClientRect().height)); })()"
    )
    assert heights[0] > heights[1]
    # ID の列の文字は折り返さない
    assert page.evaluate(
        "(() => { const r = document.createRange(); r.selectNodeContents(document.querySelector('table.grid tbody tr td')); return r.getBoundingClientRect().height < 30; })()"
    )


def test_no_match(open_story: OpenStory) -> None:
    """該当なし（ピン留め中）。表の場所に該当なしと次の操作を書き、文言は表の枠の左に留める（正常系）。"""
    # 準備・実行
    page = open_story("preview-table--no-match")
    # 検証
    assert "該当" in page.inner_text("table.grid tbody")
    assert page.locator("table.grid td.no-match-cell .no-match").count() == 1
    assert page.evaluate(
        "getComputedStyle(document.querySelector('td.no-match-cell .no-match')).position"
    ) == "sticky"


def test_columns_popover(open_story: OpenStory) -> None:
    """表示する列のポップオーバーを開いている。タイトルの列は外せない（正常系）。"""
    # 準備・実行
    page = open_story("preview-table--columns-popover")
    page.wait_for_selector(".pop:popover-open")
    # 検証
    boxes = page.evaluate(
        "[...document.querySelectorAll('.pop label')].map(l => [l.textContent.trim(), l.querySelector('input').disabled, l.querySelector('input').checked])"
    )
    assert boxes == [
        ["ID", False, True],
        ["タイトル", True, True],
        ["確度", False, True],
        ["状態", False, True],
    ]
    # ポップオーバーの題は見出しの要素にせず、aria-labelledby から指す
    assert page.locator(".pop h3").count() == 0
    labelled = page.get_attribute(".pop", "aria-labelledby")
    assert page.inner_text(f"#{labelled}") == "表示する列"
