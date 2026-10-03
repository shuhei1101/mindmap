"""画面設計『詳細の全画面』と『図の拡大』（全画面の中身の切り替え）の結合テスト。"""

from __future__ import annotations

from playwright.sync_api import Page
from preview_fixture_types import OpenPreview, WriteSamplePreview

# 図を描き終わるまで待つ上限ミリ秒
DIAGRAM_TIMEOUT_MS = 20_000

# 全画面のモーダルの外側（後ろの幕）を押す位置（画面の左上の隅）
BACKDROP_POINT = (4, 4)


def _open_full(page: Page) -> None:
    """全画面に切り替えるボタンを押し、全画面が開くのを待つ。"""
    page.click('aside.panel button[data-act="full"]')
    page.wait_for_selector("dialog.full[open]")


def test_open_and_restore(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """全画面に切り替えても履歴に積まず、元の大きさに戻すとパネルへ戻る（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=decisions&view=table&id=D-2")
    history_length = page.evaluate("history.length")
    panel_button = 'aside.panel button[data-act="full"]'
    assert page.get_attribute(panel_button, "aria-label") == "全画面表示"
    assert page.get_attribute(panel_button, "aria-pressed") == "false"
    # 実行
    _open_full(page)
    # 検証
    # ラベルは変えず、押された状態で全画面を示す
    full_button = 'dialog.full button[data-act="full"]'
    assert page.get_attribute(full_button, "aria-label") == "全画面表示"
    assert page.get_attribute(full_button, "aria-pressed") == "true"
    assert "full=1" in page.evaluate("location.hash")
    assert page.evaluate("history.length") == history_length
    assert page.inner_text("dialog.full .d-title") == "D-2の題"
    # 全てを閉じるボタンは置かない
    assert page.locator('dialog.full button[data-act="close"]').count() == 0
    page.click('dialog.full button[data-act="full"]')
    page.wait_for_selector("aside.panel.open")
    assert page.locator("dialog.full").count() == 0
    assert "full=" not in page.evaluate("location.hash")


def test_restore_by_escape(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """Esc で元の大きさ（詳細パネル）に戻る（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=decisions&view=table&id=D-2&full=1")
    page.wait_for_selector("dialog.full[open]")
    # 実行
    page.keyboard.press("Escape")
    # 検証
    page.wait_for_selector("aside.panel.open")
    assert page.locator("dialog.full").count() == 0
    assert "id=D-2" in page.evaluate("location.hash")


def test_restore_by_backdrop(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """後ろの幕（外側）を押すと、元の大きさに戻る（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=decisions&view=table&id=D-2&full=1")
    page.wait_for_selector("dialog.full[open]")
    # 実行
    page.mouse.click(*BACKDROP_POINT)
    # 検証
    page.wait_for_selector("aside.panel.open")
    assert page.locator("dialog.full").count() == 0


def test_navigate_inside(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """全画面の中で項目を移ると履歴に積み、戻る・進むで行き来できる（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=decisions&view=table&id=D-2&full=1")
    page.wait_for_selector("dialog.full[open]")
    history_length = page.evaluate("history.length")
    # 実行
    page.click("dialog.full .d-sec:has(h3:text-is('前提')) button.idlink")
    page.wait_for_function("document.querySelector('dialog.full .d-title')?.textContent === 'D-1の題'")
    # 検証
    assert page.evaluate("history.length") == history_length + 1
    page.click('dialog.full button[data-act="back"]')
    page.wait_for_function("document.querySelector('dialog.full .d-title')?.textContent === 'D-2の題'")


def test_diagram_zoom_switches_content(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """全画面の中で図を拡大すると、モーダルを重ねずに中身を図の拡大へ切り替え、閉じると本文へ戻る（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=decisions&view=table&id=D-3&full=1")
    page.wait_for_selector("dialog.full .mermaid svg", timeout=DIAGRAM_TIMEOUT_MS)
    # 実行
    page.click('dialog.full button[data-act="diagram-zoom"]')
    page.wait_for_selector("dialog.full .full-viewer .v-stage svg")
    # 検証
    assert page.locator("dialog[open]").count() == 1
    assert not page.is_visible("dialog.full .panel-body")
    page.click('dialog.full button[data-act="diagram-close"]')
    page.wait_for_selector("dialog.full .panel-body", state="visible")
    assert page.locator("dialog.full .full-viewer").count() == 0
