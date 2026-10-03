"""画面設計『詳細パネル』の結合テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page
from preview_fixture_types import OpenPreview, WriteSamplePreview
from preview_style_checks import TRANSPARENT, animated_properties, row_backgrounds

# パネルを別画面として積む幅（これ以下）
NARROW_WIDTH = 800

# 狭い幅の画面の高さ
NARROW_HEIGHT = 700

# 図を描き終わるまで待つ上限ミリ秒
DIAGRAM_TIMEOUT_MS = 20_000


def _panel_title(page: Page) -> str:
    """パネルのタイトル（項目の題）を返す。"""
    return page.inner_text("aside.panel .d-title")


def test_content(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """項目の種類・ID・状態・タイトル・案・本文（見出しと図）を出す（正常系）。"""
    # 準備
    path = write_sample_preview()
    # 実行
    page = open_preview(path, "#tab=decisions&view=table&id=D-3")
    page.wait_for_selector("aside.panel.open .mermaid svg", timeout=DIAGRAM_TIMEOUT_MS)
    # 検証
    assert page.inner_text("aside.panel .panel-kind") == "検討事項 D-3"
    assert page.get_attribute("aside.panel .detail .st", "data-st") == "要見直し"
    options = page.eval_on_selector_all(
        "aside.panel .opt",
        "opts => opts.map(o => [o.querySelector('.key').textContent, o.querySelector('.res').textContent, o.classList.contains('adopted')])",
    )
    assert options == [["A", "採用", True], ["B", "検討中", False]]
    # 本文の見出しはパネルの節の見出し（h3）より下の段
    headings = page.eval_on_selector_all(
        "aside.panel .detail h2, aside.panel .detail h3, aside.panel .detail h4, aside.panel .detail h5",
        "hs => hs.map(h => h.tagName + ':' + h.textContent)",
    )
    assert headings == ["H2:D-3の題", "H3:案", "H3:本文", "H4:要件", "H5:流れ"]
    assert page.locator("aside.panel .mermaid svg").count() == 1


def test_related_items(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """前提・後続の項目・関連タスクを出し、押すとその項目へ移る（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=decisions&view=table&id=D-2")
    # 実行
    sections = page.eval_on_selector_all(
        "aside.panel .d-sec h3", "hs => hs.map(h => h.textContent)"
    )
    page.click("aside.panel .d-sec:has(h3:text-is('前提')) button.idlink")
    page.wait_for_function("document.querySelector('aside.panel .d-title')?.textContent === 'D-1の題'")
    # 検証
    assert sections == ["前提", "後続の項目", "関連タスク"]
    assert "id=D-1" in page.evaluate("location.hash")


def test_back_and_forward(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """パネルの中で移った項目を、戻る・進むで行き来する（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=decisions&view=table&id=D-2")
    back = 'aside.panel button[data-act="back"]'
    forward = 'aside.panel button[data-act="forward"]'
    assert page.is_disabled(back)
    assert page.is_disabled(forward)
    page.click("aside.panel .d-sec:has(h3:text-is('前提')) button.idlink")
    page.wait_for_function("document.querySelector('aside.panel .d-title')?.textContent === 'D-1の題'")
    # 実行・検証
    assert page.is_enabled(back)
    page.click(back)
    page.wait_for_function("document.querySelector('aside.panel .d-title')?.textContent === 'D-2の題'")
    assert page.is_enabled(forward)
    page.click(forward)
    page.wait_for_function("document.querySelector('aside.panel .d-title')?.textContent === 'D-1の題'")


def test_selected_row(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """開いている項目の行に「選択中」の印を付け、閉じると外す（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=decisions&view=table&id=D-2")
    # 実行・検証
    selected = page.eval_on_selector_all(
        "main tr[data-id].selected", "rows => rows.map(r => r.dataset.id)"
    )
    assert selected == ["D-2"]
    page.click('aside.panel button[data-act="close"]')
    page.wait_for_function("document.querySelectorAll('main tr[data-id].selected').length === 0")


def test_close(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """閉じるボタンと Esc でパネルを閉じ、ハッシュから id を外す（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=decisions&view=table&id=D-2")
    # 実行・検証
    page.click('aside.panel button[data-act="close"]')
    page.wait_for_function("!document.querySelector('aside.panel.open')")
    assert "id=" not in page.evaluate("location.hash")
    page.click('table.grid button.row-open[data-id="D-1"]')
    page.wait_for_selector("aside.panel.open")
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('aside.panel.open')")
    assert "id=" not in page.evaluate("location.hash")


def test_side_by_side_when_wide(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """幅が広いと本文を寄せて並べる（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=decisions&view=table")
    before = page.evaluate("document.querySelector('main#main').getBoundingClientRect().width")
    # 実行
    page.click('table.grid button.row-open[data-id="D-1"]')
    page.wait_for_selector("aside.panel.open")
    # 検証
    assert page.evaluate("document.body.classList.contains('panel-open')")
    after = page.evaluate("document.querySelector('main#main').getBoundingClientRect().width")
    assert after < before


def test_overlay_when_narrow(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """幅が狭いと、パネルを別画面として積み、一覧へ戻る操作で戻る（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=decisions&view=table")
    page.set_viewport_size({"width": NARROW_WIDTH, "height": NARROW_HEIGHT})
    history_length = page.evaluate("history.length")
    # 実行
    page.click('table.grid button.row-open[data-id="D-1"]')
    page.wait_for_selector("aside.panel.open")
    # 検証
    assert page.evaluate("history.length") == history_length + 1
    panel_width = page.evaluate("document.querySelector('aside.panel').getBoundingClientRect().width")
    assert panel_width == pytest.approx(NARROW_WIDTH, abs=1)
    page.click("aside.panel button.panel-back")
    page.wait_for_function("!document.querySelector('aside.panel.open')")
    assert "id=" not in page.evaluate("location.hash")


def test_diagram_raw(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """図の Raw で、図と mermaid の原文を切り替える（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=decisions&view=table&id=D-3")
    page.wait_for_selector("aside.panel .mermaid svg", timeout=DIAGRAM_TIMEOUT_MS)
    # 実行
    page.click('aside.panel button[data-act="diagram-raw"]')
    # 検証
    assert page.get_attribute('aside.panel button[data-act="diagram-raw"]', "aria-pressed") == "true"
    assert page.is_visible("aside.panel pre.dg-raw")
    assert not page.is_visible("aside.panel .mermaid")
    assert "flowchart LR" in page.inner_text("aside.panel pre.dg-raw")
    page.click('aside.panel button[data-act="diagram-raw"]')
    assert page.is_visible("aside.panel .mermaid")


def test_content_transition(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """本文の寄せは動かさず、パネルだけが transform ですべり込む（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=decisions&view=table&id=D-2")
    page.wait_for_selector("aside.panel.open")
    # 実行
    content = animated_properties(page, "main#main")
    panel = animated_properties(page, "aside.panel")
    # 検証
    assert content == []
    assert panel == ["transform"]


def test_selected_row_hover(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """表で選んだ行は、ホバー中も選んだ行の色のままで、ほかの行はホバーで色が変わる（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=decisions&view=table&id=D-2")
    page.wait_for_selector("aside.panel.open")
    selected_row = 'table.grid tbody tr[data-id="D-2"]'
    other_row = 'table.grid tbody tr[data-id="D-4"]'
    at_rest = row_backgrounds(page, selected_row)
    # 実行
    page.hover(selected_row)
    selected_hovered = row_backgrounds(page, selected_row)
    page.hover(other_row)
    other_hovered = row_backgrounds(page, other_row)
    # 検証
    assert selected_hovered == at_rest
    assert at_rest["row"] != TRANSPARENT
    assert set(at_rest["cells"]) <= {TRANSPARENT, at_rest["row"]}
    assert other_hovered["row"] == TRANSPARENT
    assert TRANSPARENT not in other_hovered["cells"]
    assert at_rest["row"] not in other_hovered["cells"]
