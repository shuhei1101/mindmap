"""プレビューの E2E テストが共有する型と、画面を操作する補助。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from playwright.sync_api import Page

__all__ = [
    "BuildPreview",
    "OpenPreview",
    "click_item_ball",
    "row_ids",
]

type BuildPreview = Callable[..., Path]
type OpenPreview = Callable[..., Page]

# つながりのキャンバスの上を調べる間隔（px）
BALL_SCAN_STEP = 18

# 近い位置を同じ玉とみなす距離（px）
BALL_MERGE_DISTANCE = 30

# キャンバスの縁を調べないための余白（px）
CANVAS_MARGIN = 6

# 玉の上でマウスのカーソルが指の形になることを、キャンバスの上を調べて集める
SCAN_BALLS_SCRIPT = """([step, margin]) => {
    const canvas = document.getElementById('graph-canvas');
    const rect = canvas.getBoundingClientRect();
    const found = [];
    for (let y = rect.top + margin; y < rect.bottom - margin; y += step) {
        for (let x = rect.left + margin; x < rect.right - margin; x += step) {
            canvas.dispatchEvent(new PointerEvent('pointermove', {clientX: x, clientY: y, bubbles: true}));
            if (canvas.style.cursor === 'pointer') found.push([x, y]);
        }
    }
    canvas.dispatchEvent(new PointerEvent('pointerleave', {bubbles: true}));
    return found;
}"""


def row_ids(page: Page) -> list[str]:
    """表に並んでいる行の ID を上から返す。"""
    return page.eval_on_selector_all("table.grid tbody tr", "rows => rows.map(r => r.dataset.id)")


def click_item_ball(page: Page, item_id: str) -> None:
    """つながりのキャンバスで、指定した項目の玉を探して押す（玉の位置は画面に出ないので、押して開いた詳細で確かめる）。"""
    # 玉の上でカーソルが指の形になる位置を集め、近いものを 1 つにまとめる
    found = page.evaluate(SCAN_BALLS_SCRIPT, [BALL_SCAN_STEP, CANVAS_MARGIN])
    candidates: list[tuple[float, float]] = []
    for x, y in found:
        if all(abs(x - cx) + abs(y - cy) > BALL_MERGE_DISTANCE for cx, cy in candidates):
            candidates.append((x, y))
    for x, y in candidates:
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.up()
        page.wait_for_timeout(300)
        opened = page.locator("aside.panel.open .panel-kind .mono")
        # 押した玉が目的の項目なら、そこで終える。違えば閉じて次の玉を試す
        if opened.count() == 1 and opened.inner_text() == item_id:
            return
        if opened.count() == 1:
            page.keyboard.press("Escape")
            page.wait_for_timeout(200)
    raise AssertionError(f"つながりに {item_id} の玉が見つかりませんでした（調べた候補: {len(candidates)}）")
