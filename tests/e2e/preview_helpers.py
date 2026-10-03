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

# つながりのキャンバスの上を調べる間隔（px）。玉の当たりの半径（12px 前後）より細かくして、玉を取りこぼさない
BALL_SCAN_STEP = 4

# 近い位置を同じ玉とみなす距離（px）
BALL_MERGE_DISTANCE = 24

# キャンバスの縁を調べないための余白（px）
CANVAS_MARGIN = 6

# 玉を探し直す回数の係数と、玉の数の上限（試す回数は 2 つの積）
BALL_SEARCH_ATTEMPTS = 2
BALL_MAX_BALLS = 20

# 玉を押した後に詳細が開くのを待つ時間と、閉じた後にカメラが戻るのを待つ時間（ミリ秒）
BALL_CLICK_WAIT_MS = 300
BALL_SETTLE_MS = 2_000

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


def _find_ball_centers(page: Page) -> list[tuple[float, float]]:
    """カーソルが指の形になった位置を、近いものどうしでまとめた中心にして返す。"""
    found = page.evaluate(SCAN_BALLS_SCRIPT, [BALL_SCAN_STEP, CANVAS_MARGIN])
    clusters: list[list[tuple[float, float]]] = []
    for x, y in found:
        for cluster in clusters:
            if any(abs(x - cx) + abs(y - cy) <= BALL_MERGE_DISTANCE for cx, cy in cluster):
                cluster.append((x, y))
                break
        else:
            clusters.append([(x, y)])
    return [
        (sum(x for x, _ in cluster) / len(cluster), sum(y for _, y in cluster) / len(cluster))
        for cluster in clusters
    ]


def click_item_ball(page: Page, item_id: str) -> None:
    """つながりのキャンバスで、指定した項目の玉を探して押す（玉の位置は画面に出ないので、押して開いた詳細で確かめる）。"""
    tried = 0
    for _ in range(BALL_SEARCH_ATTEMPTS * BALL_MAX_BALLS):
        # 押すたびにカメラがその玉へ寄るので、毎回探し直し、まだ押していない玉を順に押す
        centers = _find_ball_centers(page)
        if tried >= len(centers):
            break
        x, y = centers[tried]
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.up()
        page.wait_for_timeout(BALL_CLICK_WAIT_MS)
        opened = page.locator("aside.panel.open .panel-kind .mono")
        # 押した玉が目的の項目なら、そこで終える。違えば閉じて、カメラが戻るのを待ち、次の玉を押す
        if opened.count() == 1 and opened.inner_text() == item_id:
            return
        tried += 1
        if opened.count() == 1:
            page.keyboard.press("Escape")
            page.wait_for_function("!document.querySelector('aside.panel.open')")
            page.wait_for_timeout(BALL_SETTLE_MS)
    raise AssertionError(f"つながりに {item_id} の玉が見つかりませんでした")
