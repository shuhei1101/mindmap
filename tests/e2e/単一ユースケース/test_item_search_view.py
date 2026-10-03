"""項目を検索する（全体の検索で ID・タイトル・本文から探し、結果からその項目を開く）の E2E テスト。"""

from __future__ import annotations

from typing import Any

from preview_helpers import BuildPreview, OpenPreview
from workspace_fixtures import MakeItem

# 検索のダイアログ
DIALOG = "dialog.search"


def test_normal(
    build_preview: BuildPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """タイトルと本文の語で探し、結果の資料を押すと、資料のタブと詳細パネルを開く（正常系）。"""
    # 準備
    path = build_preview(
        make_item("D-2", title="保存先を決める"),
        make_item("A-1", title="仕様の資料"),
        make_item("T-1"),
        settings=valid_settings,
        bodies={"A-1.md": "保存先は利用者のフォルダにする\n"},
    )
    page = open_preview(path)
    # 実行
    page.keyboard.press("/")
    page.wait_for_selector(f"{DIALOG}[open]")
    page.fill(f"{DIALOG} input", "保存先")
    page.wait_for_selector(f"{DIALOG} .sr-item")
    # 検証
    ids = page.eval_on_selector_all(f"{DIALOG} .sr-item", "items => items.map(i => i.dataset.id)")
    assert sorted(ids) == ["A-1", "D-2"]
    page.click(f'{DIALOG} .sr-item[data-id="A-1"]')
    page.wait_for_selector("aside.panel.open")
    assert page.locator(DIALOG).count() == 0
    assert page.get_attribute('nav.tabbar a[data-tab="docs"]', "aria-current") == "page"
    assert page.inner_text("aside.panel .d-title") == "仕様の資料"
    hash_text = page.evaluate("location.hash")
    assert "tab=docs" in hash_text
    assert "id=A-1" in hash_text


def test_normal_when_no_match(
    build_preview: BuildPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """どの項目にも合わない語では、該当なしを出し、Esc で開く前の画面のままに戻る（正常系）。"""
    # 準備
    path = build_preview(make_item("D-1"), make_item("T-1"), settings=valid_settings)
    page = open_preview(path)
    hash_before = page.evaluate("location.hash")
    # 実行
    page.click('button[data-act="search"]')
    page.wait_for_selector(f"{DIALOG}[open]")
    page.fill(f"{DIALOG} input", "存在しない語")
    page.wait_for_selector(f"{DIALOG} .no-match")
    # 検証
    assert (
        page.inner_text(f"{DIALOG} .no-match")
        == "該当する項目はありません。別の条件を試してください。"
    )
    page.keyboard.press("Escape")
    page.wait_for_function(f"!document.querySelector('{DIALOG}')")
    assert page.get_attribute('nav.tabbar a[data-tab="overview"]', "aria-current") == "page"
    assert page.evaluate("location.hash") == hash_before
