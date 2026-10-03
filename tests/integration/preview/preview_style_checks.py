"""プレビューの見た目（余白・面の色・文字の大きさ・動き）を、計算後のスタイルで測る関数と、テストが共有する値。"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page

__all__ = [
    "BOARD_EDGE_GAP_PX",
    "MIN_UI_FONT_SIZE_PX",
    "TRANSPARENT",
    "animated_properties",
    "board_edges",
    "map_item_id_font_size",
    "pin_id_column",
    "row_backgrounds",
    "table_cell_backgrounds",
]

# 背景色を持たない要素の計算後の背景色
TRANSPARENT = "rgba(0, 0, 0, 0)"

# ボードの左端とカードの間に空ける余白（px）
BOARD_EDGE_GAP_PX = 8

# 画面の文字として許す最小の大きさ（px）
MIN_UI_FONT_SIZE_PX = 11

# 先頭の列の先頭のカード・ボード・ツールバーの左端を測る
_BOARD_EDGES_SCRIPT = """() => ({
    cardLeft: document.querySelector('.board .board-col:first-child .card').getBoundingClientRect().left,
    boardLeft: document.querySelector('.board').getBoundingClientRect().left,
    toolbarLeft: document.querySelector('.toolbar').getBoundingClientRect().left,
})"""

# 表のセルの背景色を、固定した列とそれ以外に分けて集める
_TABLE_CELL_BACKGROUNDS_SCRIPT = """() => {
    const colors = cells => [...new Set([...cells].map(c => getComputedStyle(c).backgroundColor))];
    return {
        wrap: getComputedStyle(document.querySelector('.table-wrap')).backgroundColor,
        plain: colors(document.querySelectorAll('table.grid tbody td:not(.pinned)')),
        pinned: colors(document.querySelectorAll('table.grid tbody td.pinned')),
    };
}"""

# 行の背景色と、その行のセルの背景色を、固定した列とそれ以外に分けて集める
_ROW_BACKGROUNDS_SCRIPT = """selector => {
    const row = document.querySelector(selector);
    const colors = cells => [...new Set([...cells].map(c => getComputedStyle(c).backgroundColor))];
    return {
        row: getComputedStyle(row).backgroundColor,
        cells: colors(row.querySelectorAll('td:not(.pinned)')),
        pinned: colors(row.querySelectorAll('td.pinned')),
    };
}"""

# ID の列まで固定する見出しのボタン
_PIN_ID_BUTTON = 'table.grid thead .th-tool.pin[data-pin="id"]'

# 時間の幅がある（0 秒より長い）transition の対象の名前を集める（対象と時間は組で数え、時間が足りない分は繰り返す）
_ANIMATED_PROPERTIES_SCRIPT = """selector => {
    const style = getComputedStyle(document.querySelector(selector));
    const properties = style.transitionProperty.split(',').map(p => p.trim());
    const durations = style.transitionDuration.split(',').map(d => parseFloat(d));
    return properties.filter((_, i) => durations[i % durations.length] > 0);
}"""


def board_edges(page: Page) -> dict[str, float]:
    """ボードの先頭のカード・ボード・ツールバーの左端の位置（px）を返す。"""
    return page.evaluate(_BOARD_EDGES_SCRIPT)


def table_cell_backgrounds(page: Page) -> dict[str, Any]:
    """表の枠の背景色と、本文のセルの背景色（固定した列とそれ以外）を返す。"""
    return page.evaluate(_TABLE_CELL_BACKGROUNDS_SCRIPT)


def pin_id_column(page: Page) -> None:
    """表の見出しのボタンで ID の列まで固定し、固定したセルが描かれるのを待つ。"""
    page.click(_PIN_ID_BUTTON)
    page.wait_for_selector("table.grid tbody td.pinned")


def row_backgrounds(page: Page, selector: str) -> dict[str, Any]:
    """表の行の背景色と、その行のセルの背景色（固定した列とそれ以外）を返す。"""
    return page.evaluate(_ROW_BACKGROUNDS_SCRIPT, selector)


def animated_properties(page: Page, selector: str) -> list[str]:
    """要素の transition のうち、時間の幅がある対象の名前を返す。"""
    return page.evaluate(_ANIMATED_PROPERTIES_SCRIPT, selector)


def map_item_id_font_size(page: Page) -> float:
    """マップの項目の 2 行目の ID の計算後の文字の大きさ（px）を返す。"""
    return page.evaluate(
        "parseFloat(getComputedStyle(document.querySelector('#decision-map .n-item .r2 .mono')).fontSize)"
    )
