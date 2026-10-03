"""全ての画面で共通のトップバーとタブの帯（画面設計の「トップバー」の要素）の結合テスト。"""

from __future__ import annotations

from preview_fixture_types import OpenPreview, WriteSamplePreview

# タブの帯に並ぶ画面の並び（つながりは右端）
TAB_KEYS = [
    "overview",
    "decisions",
    "tasks",
    "research",
    "docs",
    "terms",
    "notes",
    "logs",
    "graph",
]


def test_tabs(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """題名と、種類ごとの件数つきのタブを出す。タブを押すと画面を移って履歴に積む（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path)
    history_length = page.evaluate("history.length")
    # 実行
    tabs = page.eval_on_selector_all(
        "nav.tabbar a", "links => links.map(a => [a.dataset.tab, a.querySelector('.count')?.textContent ?? null])"
    )
    page.click('nav.tabbar a[data-tab="tasks"]')
    page.wait_for_selector(".screen.tasks")
    # 検証
    assert page.inner_text(".topbar .brand-sub") == "要件出しのスキル mindmap を設計する"
    assert [row[0] for row in tabs] == TAB_KEYS
    assert dict(tabs) == {
        "overview": None,
        "decisions": "5",
        "tasks": "3",
        "research": "1",
        "docs": "2",
        "terms": "1",
        "notes": "1",
        "logs": "1",
        "graph": None,
    }
    assert page.evaluate("history.length") == history_length + 1
    page.go_back()
    page.wait_for_selector(".overview")


def test_tab_keeps_detail_panel(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """タブを押しても、開いている詳細パネルは閉じない（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=decisions&view=table&id=D-2")
    # 実行
    page.click('nav.tabbar a[data-tab="tasks"]')
    page.wait_for_selector(".screen.tasks")
    # 検証
    assert page.inner_text("aside.panel .d-title") == "D-2の題"


def test_theme_is_kept(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """ライト / ダークを切り替え、端末の保存領域に残して開き直しても保つ（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path)
    page.emulate_media(color_scheme="light")
    page.reload()
    page.wait_for_selector("main#main > *")
    assert page.evaluate("document.documentElement.dataset.theme") == "light"
    # 実行
    page.click(".topbar button[data-theme]")
    # 検証
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    page.reload()
    page.wait_for_selector("main#main > *")
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
