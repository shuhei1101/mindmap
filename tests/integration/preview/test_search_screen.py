"""画面設計『全体の検索』の結合テスト。"""

from __future__ import annotations

from playwright.sync_api import Page
from preview_fixture_types import OpenPreview, WriteSamplePreview

# 検索のダイアログ
DIALOG = "dialog.search"


def _result_ids(page: Page) -> list[str]:
    """当たった項目の ID を並びのまま返す。"""
    return page.eval_on_selector_all(
        f"{DIALOG} .sr-item", "items => items.map(i => i.dataset.id)"
    )


def test_open_by_slash_and_trigger(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """`/` キーとトップバーの入口で開き、検索の言葉の欄に入力できる（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path)
    # 実行・検証
    page.keyboard.press("/")
    page.wait_for_selector(f"{DIALOG}[open]")
    assert page.evaluate(f"document.activeElement === document.querySelector('{DIALOG} input')")
    page.keyboard.press("Escape")
    page.wait_for_function(f"!document.querySelector('{DIALOG}')")
    page.click('button[data-act="search"]')
    page.wait_for_selector(f"{DIALOG}[open]")


def test_search_by_id_title_and_body(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """空白で区切った語を全て含む項目を、ID・タイトル・本文から探す（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path)
    page.keyboard.press("/")
    page.wait_for_selector(f"{DIALOG}[open]")
    # 実行・検証（ID）
    page.fill(f"{DIALOG} input", "d-3")
    page.wait_for_selector(f"{DIALOG} .sr-item")
    assert _result_ids(page) == ["D-3"]
    # 本文（大文字・小文字を区別しない）
    page.fill(f"{DIALOG} input", "本文の 段落")
    page.wait_for_function(f"document.querySelectorAll('{DIALOG} .sr-item').length === 1")
    assert _result_ids(page) == ["D-3"]
    # 全ての語を含まないものは外れる
    page.fill(f"{DIALOG} input", "本文の 無い語")
    page.wait_for_function(f"document.querySelectorAll('{DIALOG} .sr-item').length === 0")
    assert "該当する項目はありません" in page.inner_text(DIALOG)


def test_open_result(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """結果を押すと、その項目のタブと詳細パネルを開いて検索を閉じる（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path)
    page.keyboard.press("/")
    page.wait_for_selector(f"{DIALOG}[open]")
    page.fill(f"{DIALOG} input", "T-1")
    page.wait_for_selector(f"{DIALOG} .sr-item")
    # 実行
    page.click(f'{DIALOG} .sr-item[data-id="T-1"]')
    # 検証
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "T-1の題"
    assert page.get_attribute('nav.tabbar a[data-tab="tasks"]', "aria-current") == "page"
    assert page.locator(DIALOG).count() == 0


def test_open_result_by_keyboard(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """下の矢印で結果へ移り、上下の矢印で選んで Enter で、その項目を開く（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path)
    page.keyboard.press("/")
    page.wait_for_selector(f"{DIALOG}[open]")
    page.fill(f"{DIALOG} input", "の題")
    page.wait_for_selector(f"{DIALOG} .sr-item")
    ids = _result_ids(page)
    # 実行（入力欄から 1 つ目へ、2 つ目へ、3 つ目へ、2 つ目へ戻って開く）
    for key in ("ArrowDown", "ArrowDown", "ArrowDown", "ArrowUp", "Enter"):
        page.keyboard.press(key)
    # 検証
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title").startswith(f"{ids[1]}の題")
    assert page.locator(DIALOG).count() == 0


def test_close(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """閉じるボタン・Esc・外側の押下で閉じる（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path)
    # 実行・検証
    page.keyboard.press("/")
    page.wait_for_selector(f"{DIALOG}[open]")
    page.click(f'{DIALOG} button[aria-label="検索を閉じる"]')
    page.wait_for_function(f"!document.querySelector('{DIALOG}')")
    page.keyboard.press("/")
    page.wait_for_selector(f"{DIALOG}[open]")
    page.mouse.click(4, 4)
    page.wait_for_function(f"!document.querySelector('{DIALOG}')")
