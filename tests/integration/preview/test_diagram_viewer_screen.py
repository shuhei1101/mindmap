"""画面設計『図の拡大』（詳細パネルからのモーダル）の結合テスト。"""

from __future__ import annotations

import re

from playwright.sync_api import Page
from preview_fixture_types import OpenPreview, WriteSamplePreview

# 図を描き終わるまで待つ上限ミリ秒
DIAGRAM_TIMEOUT_MS = 20_000

# 図の上でホイールを回す量（拡大する向き）
WHEEL_DELTA = -300

# 図の上の位置（モーダルの中央）
DIAGRAM_POINT = (640, 400)


def _open_viewer(write_sample_preview, open_preview) -> Page:
    """詳細パネルの図の拡大を開いて、そのページを返す。"""
    page = open_preview(write_sample_preview(), "#tab=decisions&view=table&id=D-3")
    page.wait_for_selector("aside.panel .mermaid svg", timeout=DIAGRAM_TIMEOUT_MS)
    page.click('aside.panel button[data-act="diagram-zoom"]')
    page.wait_for_selector("dialog.viewer[open] .v-stage svg")
    return page


def _percent(page: Page) -> int:
    """道具の行に出ている倍率（%）を数にして返す。"""
    text = page.inner_text("dialog.viewer .v-pct")
    found = re.search(r"\d+", text)
    assert found is not None, text
    return int(found.group())


def test_open_and_close(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """詳細パネルから図をモーダルで開き、本文へ戻るで閉じる（正常系）。"""
    # 準備・実行
    page = _open_viewer(write_sample_preview, open_preview)
    # 検証
    assert page.locator("dialog.viewer .v-stage svg").count() == 1
    # 図を置く窓が高さを持ち、窓に収まる倍率（正の値）で開く
    assert page.evaluate("document.querySelector('dialog.viewer .v-canvas').clientHeight") > 0
    assert _percent(page) > 0
    page.click('dialog.viewer button[data-act="diagram-close"]')
    page.wait_for_function("!document.querySelector('dialog.viewer')")
    assert page.locator("aside.panel.open").count() == 1


def test_close_by_escape(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """Esc で図の拡大を閉じ、詳細パネルは開いたままにする（正常系）。"""
    # 準備
    page = _open_viewer(write_sample_preview, open_preview)
    # 実行
    page.keyboard.press("Escape")
    # 検証
    page.wait_for_function("!document.querySelector('dialog.viewer')")
    assert page.locator("aside.panel.open").count() == 1
    assert "id=D-3" in page.evaluate("location.hash")


def test_zoom(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """拡大・縮小のボタンとホイールで倍率を変える（正常系）。"""
    # 準備
    page = _open_viewer(write_sample_preview, open_preview)
    page.wait_for_function("document.querySelector('dialog.viewer .v-pct').textContent.match(/\\d/)")
    before = _percent(page)
    # 実行・検証
    page.click('dialog.viewer button[aria-label="拡大"]')
    after_button = _percent(page)
    assert after_button > before
    page.mouse.move(*DIAGRAM_POINT)
    page.mouse.wheel(0, WHEEL_DELTA)
    page.wait_for_function(
        f"parseInt(document.querySelector('dialog.viewer .v-pct').textContent.match(/\\d+/)[0]) > {after_button}"
    )
    after_wheel = _percent(page)
    page.click('dialog.viewer button[aria-label="縮小"]')
    assert _percent(page) < after_wheel


def test_text_selectable(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """図の文字は選んでコピーできる（正常系）。"""
    # 準備
    page = _open_viewer(write_sample_preview, open_preview)
    # 実行・検証
    select = page.evaluate(
        "getComputedStyle(document.querySelector('dialog.viewer .v-stage svg text, dialog.viewer .v-stage svg .nodeLabel')).userSelect"
    )
    assert select == "text"
