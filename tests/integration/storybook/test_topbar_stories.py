"""部品設計『トップバー』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

from storybook_fixture_types import OpenStory

# 狭い幅（Storybook の画面幅を 390px にしたときの幅と高さ）
NARROW_SIZE = {"width": 390, "height": 844}

# 題名が収まりきらなくなる幅（題名を隠す幅 900px より広い）
MEDIUM_SIZE = {"width": 1000, "height": 600}

# 開いている画面のタブ・入口の key を読む
CURRENT_SCRIPT = """() => [...document.querySelectorAll('nav.tabbar a[aria-current="page"]')].map(a => a.dataset.tab)"""


def test_overview(open_story: OpenStory) -> None:
    """概要を開いている。開いている画面のタブだけが aria-current="page" を持つ（正常系）。"""
    # 準備・実行
    page = open_story("preview-topbar--overview")
    # 検証
    assert page.evaluate(CURRENT_SCRIPT) == ["overview"]
    assert page.locator("nav.tabbar").get_attribute("aria-label") == "項目の種類"
    # トップバーのツール名が mindstella
    assert page.inner_text(".brand-name") == "mindstella"
    assert page.inner_text(".brand-sub") == "要件出しのスキル mindmap を設計する"


def test_graph(open_story: OpenStory) -> None:
    """つながりを開いている。つながりの入口だけを選んだ見た目にする（正常系）。"""
    # 準備・実行
    page = open_story("preview-topbar--graph")
    # 検証
    assert page.evaluate(CURRENT_SCRIPT) == ["graph"]
    assert page.locator("nav.tabbar a.tab-special").count() == 1


def test_long_title(open_story: OpenStory) -> None:
    """題名が長いと 1 行で末尾を省略し、検索の入口とテーマの切り替えを押し出さない（正常系）。"""
    # 準備・実行
    page = open_story("preview-topbar--long-title")
    page.set_viewport_size(MEDIUM_SIZE)
    page.wait_for_function("innerWidth === 1000")
    # 検証
    title = page.evaluate(
        "(() => { const t = document.querySelector('.brand-sub'); return [t.scrollWidth > t.clientWidth, getComputedStyle(t).textOverflow, t.title.length > 40]; })()"
    )
    assert title == [True, "ellipsis", True]
    viewport_width = page.evaluate("innerWidth")
    for selector in (".search-trigger", ".top-btn"):
        box = page.locator(selector).bounding_box()
        assert box is not None
        assert box["x"] + box["width"] <= viewport_width


def test_dark(open_story: OpenStory) -> None:
    """ダークのとき、ライトへ切り替えるボタンを出す（正常系）。"""
    # 準備・実行
    page = open_story("preview-topbar--dark")
    # 検証
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    assert page.get_attribute(".top-btn", "aria-label") == "ライトに切り替え"
    assert page.get_attribute(".top-btn", "data-theme") == "light"


def test_narrow(open_story: OpenStory) -> None:
    """幅 390px では、検索の入口を虫眼鏡だけにして題名を隠し、タブは帯の中で横に送る（正常系）。"""
    # 準備
    page = open_story("preview-topbar--narrow")
    page.set_viewport_size(NARROW_SIZE)
    page.wait_for_function("innerWidth === 390")
    # 実行・検証
    search_width = page.locator(".search-trigger").bounding_box()["width"]  # type: ignore[index]
    assert search_width <= 40
    assert not page.is_visible(".brand-sub")
    assert page.get_attribute(".search-trigger", "aria-label") == "すべての項目を検索"
    overflow = page.evaluate(
        "(() => { const t = document.querySelector('nav.tabbar'); return [t.scrollWidth > t.clientWidth, document.documentElement.scrollWidth <= innerWidth]; })()"
    )
    assert overflow == [True, True]
