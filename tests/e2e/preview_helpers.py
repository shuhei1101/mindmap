"""プレビューの E2E テストが共有する型と、画面を操作する補助。"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

__all__ = [
    "BuildPreview",
    "OpenPreview",
    "click_item_ball",
    "count_balls",
    "preview_reflects_yaml",
    "row_ids",
    "shown_ball_item_ids",
]

type BuildPreview = Callable[..., Path]
type OpenPreview = Callable[..., Page]

# つながりのキャンバスの上を調べる間隔（px）。玉の当たりの半径（12px 前後）より細かくして、玉を取りこぼさない
BALL_SCAN_STEP = 4

# 近い位置を同じ玉とみなす距離（px）
BALL_MERGE_DISTANCE = 24

# キャンバスの縁を調べないための余白（px）
CANVAS_MARGIN = 6

# 玉の数の上限と、玉を一巡して試す回数（試す回数の上限は 2 つの積）
BALL_MAX_BALLS = 20
BALL_CYCLES = 2

# カメラが止まったとみなす条件: 走査を間を空けて 2 回続け、どの玉も動いた距離がこの値（px）以下
BALL_STILL_DISTANCE = 1.5

# 走査の間隔（ミリ秒）と、止まるのを待つ走査の回数の上限
BALL_STILL_INTERVAL_MS = 250
BALL_STILL_MAX_SCANS = 60

# 玉を押した後に詳細が開くのを待つ上限（ミリ秒）。玉に当たっていなければ開かない
BALL_OPEN_TIMEOUT_MS = 1_500

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


# 埋め込みのデータの開きタグ
DATA_ELEMENT_OPEN = '<script type="application/json" id="mindmap-data">'

# 7 種類の YAML のファイル名（キーの名前はファイル名から .yaml を落としたもの）
KIND_KEYS = ("decisions", "tasks", "research", "docs", "terms", "notes", "logs")


def _yaml_items(root: Path, key: str) -> list[Any]:
    """ワークスペースの種類ごとの YAML の項目を返す（ファイルが無い種類は項目なし）。"""
    path = root / f"{key}.yaml"
    if not path.exists():
        return []
    return yaml.safe_load(path.read_text(encoding="utf-8"))["items"]


def preview_reflects_yaml(root: Path) -> bool:
    """preview.html に埋め込んだ記録が、今のワークスペースの YAML と同じか（最後の編集の後に書き出されたか）を返す。

    ファイルの更新時刻の比べ方は、実行環境の時計が戻ると崩れるので、書き出された中身で確かめる。
    """
    html = (root / "preview.html").read_text(encoding="utf-8")
    embedded: dict[str, Any] = json.loads(
        html.split(DATA_ELEMENT_OPEN, 1)[1].split("</script>", 1)[0]
    )
    return all(embedded[key] == _yaml_items(root, key) for key in KIND_KEYS)


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


def _settled_ball_centers(page: Page) -> list[tuple[float, float]]:
    """カメラが止まる（玉の位置が走査 2 回で動かなくなる）まで待って、玉の中心を返す。"""
    previous = _find_ball_centers(page)
    for _ in range(BALL_STILL_MAX_SCANS):
        page.wait_for_timeout(BALL_STILL_INTERVAL_MS)
        current = _find_ball_centers(page)
        still = len(current) == len(previous) and all(
            abs(x - px) <= BALL_STILL_DISTANCE and abs(y - py) <= BALL_STILL_DISTANCE
            for (x, y), (px, py) in zip(current, previous, strict=True)
        )
        if still and current:
            return current
        previous = current
    raise AssertionError("つながりのカメラが止まりませんでした")


def click_item_ball(page: Page, item_id: str) -> None:
    """つながりのキャンバスで、指定した項目の玉を探して押す（玉の位置は画面に出ないので、押して開いた詳細で確かめる）。

    詳細パネルが開いたままだと、押した玉が開いている項目と同じかを見分けられず、カメラもその項目へ寄っているので、
    先にパネルを閉じて全体を見る位置に戻す。
    """
    if page.locator("aside.panel.open").count() > 0:
        page.keyboard.press("Escape")
        page.wait_for_function("!document.querySelector('aside.panel.open')")
    for attempt in range(BALL_MAX_BALLS * BALL_CYCLES):
        # カメラが止まってから玉を探す。押すたびに玉の数や並びが変わりうるので、探した玉を順に（一巡したら最初から）押す
        centers = _settled_ball_centers(page)
        x, y = centers[attempt % len(centers)]
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.up()
        try:
            page.wait_for_selector("aside.panel.open .panel-kind .mono", timeout=BALL_OPEN_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            # 玉に当たらなかった: 次の玉へ
            continue
        # 押した玉が目的の項目なら、そこで終える。違えば閉じて、カメラが止まるのを待って次の玉を押す
        if page.locator("aside.panel.open .panel-kind .mono").inner_text() == item_id:
            return
        page.keyboard.press("Escape")
        page.wait_for_function("!document.querySelector('aside.panel.open')")
    raise AssertionError(f"つながりに {item_id} の玉が見つかりませんでした")


def count_balls(page: Page) -> int:
    """つながりのキャンバスに出ている玉の数を返す（近い玉どうしは 1 つに数える）。"""
    return len(_find_ball_centers(page))


def shown_ball_item_ids(page: Page) -> set[str]:
    """つながりのキャンバスに出ている玉を順に押し、開いた詳細から項目の ID を集めて返す。

    押すとカメラがその玉へ寄るので、押すたびに閉じて、カメラが止まるのを待ってから次の玉を探す。
    """
    ids: set[str] = set()
    ball_count = len(_settled_ball_centers(page))
    for index in range(ball_count):
        centers = _settled_ball_centers(page)
        x, y = centers[index % len(centers)]
        page.mouse.move(x, y)
        page.mouse.down()
        page.mouse.up()
        try:
            page.wait_for_selector("aside.panel.open .panel-kind .mono", timeout=BALL_OPEN_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            # 玉に当たらなかった: 次の玉へ
            continue
        ids.add(page.locator("aside.panel.open .panel-kind .mono").inner_text())
        page.keyboard.press("Escape")
        page.wait_for_function("!document.querySelector('aside.panel.open')")
    return ids
