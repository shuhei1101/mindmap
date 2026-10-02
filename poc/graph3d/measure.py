"""つながりの検証用ページを Chromium で開き、操作ごとのコマの落ち方と 1 コマの処理時間を測る。"""

from __future__ import annotations

import json
import math
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, sync_playwright

PAGE = Path(__file__).resolve().parent / "index.html"
# 既に立っている Chromium 系のブラウザへつなぐときの CDP の URL（無ければ Playwright の Chromium を開く）
CDP_URL = os.environ.get("CDP_URL")
# ブラウザから見たページの URL（Windows 側のブラウザでは、WSL のファイルの代わりに HTTP で配る）
PAGE_URL = os.environ.get("PAGE_URL", PAGE.as_uri())
# 計測用のブラウザのプロセスを見分ける --user-data-dir の一部（Windows のブラウザでメモリを測るとき）
MEM_PROFILE = os.environ.get("MEM_PROFILE")
MB = 1024 * 1024
# 画面のリフレッシュレートに合わせた落ちたコマ: 間隔の中央値のこの倍を超えたコマ
REL_DROP_FACTOR = 1.5

# 計測の段と条件（PoC の方針の案のとおり）
COUNTS = [67, 150, 300, 600, 1000]
VIEWPORTS = [(1280, 800), (1920, 1080)]
SCALES = [1, 2]

# 1 操作を続ける秒数
OP_SECONDS = 5.0
# 開いてから力学が落ち着くまで待つ秒数（alpha 0.06 から 0.004 まで約 450 コマ = 7.5 秒 + 開く動き 1.4 秒）
SETTLE_SECONDS = 9.0
# 操作と操作の間に置く秒数
OP_GAP_SECONDS = 1.0
# 操作の入力を送る間隔（60Hz の 1 コマ）
INPUT_INTERVAL = 1 / 60
# 拡大・縮小の向きを入れ替える秒数
ZOOM_FLIP_SECONDS = 0.5
# ホイールの 1 回の量
WHEEL_DELTA = 40
# 回転のドラッグで描く円の半径（px）と 1 周の秒数
DRAG_RADIUS = 160
DRAG_PERIOD = 2.0
# 押下: 開く → 閉じる を繰り返す間隔（秒）
PRESS_STEP = 1.25
# 閉じるときに押す背景の、キャンバスの左上からのずれ（px）
BACKGROUND_OFFSET = 12

# 合否の基準
DROP_MS = 25.0  # 1.5 コマ分
DROP_RATIO_MAX = 0.01
WORK_P95_MAX = 8.0
LONGTASK_MAX = 0
PERCENTILE = 0.95


def percentile(values: list[float], q: float) -> float:
    """q 分位の値を返す（値が無ければ 0）。"""
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, math.ceil(len(ordered) * q) - 1)]


def summarize(raw: dict[str, list[float]]) -> dict[str, Any]:
    """記録から、落ちたコマの割合・処理時間の p95・長いタスクの数と合否をまとめる。"""
    intervals = raw["intervals"]
    dropped = sum(1 for v in intervals if v > DROP_MS)
    ratio = dropped / len(intervals) if intervals else 1.0
    work95 = percentile(raw["work"], PERCENTILE)
    longtasks = len(raw["longtasks"])
    # リフレッシュレートが 60Hz でない画面向けに、間隔の中央値の 1.5 倍を超えたコマも数える
    median = statistics.median(intervals) if intervals else 0.0
    rel_dropped = sum(1 for v in intervals if v > median * REL_DROP_FACTOR)
    return {
        "frames": len(intervals),
        "interval_median": round(median, 2),
        "rel_drop_ratio": round(rel_dropped / len(intervals), 4) if intervals else 1.0,
        "dropped": dropped,
        "drop_ratio": round(ratio, 4),
        "work_p95": round(work95, 2),
        "work_max": round(max(raw["work"], default=0.0), 2),
        "longtasks": longtasks,
        "ok": ratio <= DROP_RATIO_MAX and work95 <= WORK_P95_MAX and longtasks <= LONGTASK_MAX,
    }


def canvas_box(page: Page) -> dict[str, float]:
    """キャンバスの画面上の位置と大きさを返す。"""
    box = page.locator("#fg3").bounding_box()
    # 描けていない: キャンバスが無ければ測れない
    if box is None:
        raise RuntimeError("キャンバスが画面にありません")
    return box


def op_zoom(page: Page) -> None:
    """マウスを中心に置き、拡大と縮小を半秒ごとに入れ替えながらホイールを送り続ける。"""
    box = canvas_box(page)
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    start = time.monotonic()
    while (elapsed := time.monotonic() - start) < OP_SECONDS:
        # 半秒ごとに、寄る（負）と離れる（正）を入れ替える
        sign = -1 if int(elapsed / ZOOM_FLIP_SECONDS) % 2 == 0 else 1
        page.mouse.wheel(0, sign * WHEEL_DELTA)
        time.sleep(INPUT_INTERVAL)


def op_rotate(page: Page) -> None:
    """押したまま、円を描くようにドラッグし続ける。"""
    box = canvas_box(page)
    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    page.mouse.move(cx + DRAG_RADIUS, cy)
    page.mouse.down()
    start = time.monotonic()
    while (elapsed := time.monotonic() - start) < OP_SECONDS:
        a = 2 * math.pi * elapsed / DRAG_PERIOD
        page.mouse.move(cx + DRAG_RADIUS * math.cos(a), cy + DRAG_RADIUS * math.sin(a))
        time.sleep(INPUT_INTERVAL)
    page.mouse.up()


def op_press(page: Page) -> None:
    """中心に近い玉を押して開き、背景を押して閉じる、を繰り返す。"""
    box = canvas_box(page)
    start = time.monotonic()
    last_id: str | None = None
    step = 0
    while time.monotonic() - start < OP_SECONDS:
        # 偶数の段: 前と違う玉を押して開く / 奇数の段: 左上の背景を押して閉じる
        if step % 2 == 0:
            node = page.evaluate("(skip) => window.__pickNode(skip)", last_id)
            page.mouse.click(node["x"], node["y"])
            last_id = node["id"]
        else:
            page.mouse.click(box["x"] + BACKGROUND_OFFSET, box["y"] + BACKGROUND_OFFSET)
        step += 1
        time.sleep(max(0.0, start + step * PRESS_STEP - time.monotonic()))


OPS = {"zoom": op_zoom, "rotate": op_rotate, "press": op_press}


def measure_op(page: Page, op: str) -> dict[str, Any]:
    """1 つの操作の間だけ記録して、まとめを返す。"""
    page.evaluate("window.__startRec()")
    OPS[op](page)
    raw = page.evaluate("window.__stopRec()")
    return summarize(raw)


def js_heap_mb(page: Page) -> float:
    """ページの JavaScript のヒープの使用量（MB）を CDP の Performance.getMetrics で返す。"""
    cdp = page.context.new_cdp_session(page)
    cdp.send("Performance.enable")
    metrics = {m["name"]: m["value"] for m in cdp.send("Performance.getMetrics")["metrics"]}
    cdp.detach()
    return round(metrics["JSHeapUsedSize"] / MB, 1)


def browser_memory_mb() -> float | None:
    """計測に使うブラウザの全てのプロセスの私用メモリ（MB）の合計を返す。Windows のブラウザでないときは None。"""
    # MEM_PROFILE: 計測用のブラウザだけを拾うための、--user-data-dir に含まれる文字列
    if not MEM_PROFILE:
        return None
    script = (
        "(Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*" + MEM_PROFILE + "*' } "
        "| Measure-Object -Property PrivatePageCount -Sum).Sum"
    )
    out = subprocess.run(["powershell.exe", "-NoProfile", "-Command", script], capture_output=True, text=True, check=True)
    return round(float(out.stdout.strip()) / MB, 1)


def main() -> None:
    """全ての段と条件を測り、1 行 1 件の JSON を書き出す。引数: 書き出し先・描き方（opt,opt-settle,mock）・件数（任意）。"""
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("results.jsonl")
    variants = sys.argv[2].split(",") if len(sys.argv) > 2 else ["opt"]
    counts = [int(v) for v in sys.argv[3].split(",")] if len(sys.argv) > 3 else COUNTS
    with sync_playwright() as pw, out.open("w", encoding="utf-8") as f:
        browser = pw.chromium.connect_over_cdp(CDP_URL) if CDP_URL else pw.chromium.launch(headless=False)
        for variant in variants:
            for n in counts:
                for width, height in VIEWPORTS:
                    for scale in SCALES:
                        base_mem = browser_memory_mb()
                        ctx = browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=scale)
                        page = ctx.new_page()
                        # 描き方の名前: {v}[-{rs}][-nolabel|-bitmap]（例 opt-settle・opt-each-bitmap）
                        parts = variant.split("-")
                        v, rs = parts[0], parts[1] if len(parts) > 1 else "each"
                        labels = "0" if "nolabel" in parts else "bitmap" if "bitmap" in parts else "1"
                        page.goto(f"{PAGE_URL}?n={n}&theme=dark&v={v}&rs={rs}&labels={labels}")
                        time.sleep(SETTLE_SECONDS)
                        for op in OPS:
                            row = {"variant": variant, "n": n, "viewport": f"{width}x{height}", "scale": scale, "op": op, **measure_op(page, op)}
                            # 操作の直後: ページの JavaScript のヒープと、ブラウザ全体の使用メモリの増え分
                            row["js_heap_mb"] = js_heap_mb(page)
                            if base_mem is not None:
                                now_mem = browser_memory_mb()
                                row["browser_mem_mb"] = now_mem
                                row["browser_mem_delta_mb"] = round(now_mem - base_mem, 1)
                            line = json.dumps(row, ensure_ascii=False)
                            print(line, flush=True)
                            f.write(line + "\n")
                            f.flush()
                            time.sleep(OP_GAP_SECONDS)
                        ctx.close()
        browser.close()


if __name__ == "__main__":
    main()
