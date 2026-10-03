"""画面設計『検討事項』（マップ・ボード・表。マップは項目 ID `decision-map`）の結合テスト。"""

from __future__ import annotations

from playwright.sync_api import Page
from preview_fixture_types import OpenPreview, WriteSamplePreview

# マップを字下げの一覧に切り替える幅の境（これ以下）
NARROW_WIDTH = 800

# 狭い幅の画面の高さ
NARROW_HEIGHT = 700

# 状態の順（ボードの列の並び）
DECISION_STATUSES = ["要見直し", "未決定", "保留", "未整理", "決定済み", "対象外", "取り下げ"]


def _view_pressed(page: Page, view: str) -> str | None:
    """表示形式の切り替えで、その形式のボタンが押されているかを返す。"""
    return page.get_attribute(f'.segment button[data-view="{view}"]', "aria-pressed")


def _map_item_ids(page: Page) -> list[str]:
    """マップに描かれている検討事項の ID を並びのまま返す。"""
    return page.eval_on_selector_all(
        "#decision-map .map-node.n-item", "nodes => nodes.map(n => n.dataset.node)"
    )


def test_view_switch(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """表示形式の切り替えで、マップ・ボード・表を行き来し、ハッシュの view を置き換える（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=decisions")
    history_length = page.evaluate("history.length")
    assert _view_pressed(page, "map") == "true"
    # 実行・検証
    for view in ("board", "table", "map"):
        page.click(f'.segment button[data-view="{view}"]')
        page.wait_for_function(
            f"document.querySelector('.segment button[data-view=\"{view}\"]').getAttribute('aria-pressed') === 'true'"
        )
        assert _view_pressed(page, view) == "true"
    # 表示形式の切り替えは履歴に積まない
    assert page.evaluate("history.length") == history_length
    # 画面の名前が h1
    assert page.inner_text("main h1") == "検討事項"


def test_map(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """対象 → カテゴリー → フェーズ → 検討事項の木をマップに描き、項目を押すと詳細パネルを開く（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=decisions&view=map")
    page.wait_for_selector("#decision-map .map-node.n-item")
    # 実行・検証（既定は決定済みを隠した状態）
    kinds = page.eval_on_selector_all(
        "#decision-map .map-node",
        "nodes => nodes.map(n => n.className.split(' ').find(c => c.startsWith('n-')))",
    )
    assert kinds[:3] == ["n-target", "n-category", "n-phase"]
    assert _map_item_ids(page) == ["D-2", "D-3", "D-4", "D-5"]
    page.click('#decision-map button[data-node="D-2"]')
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "D-2の題"
    assert "id=D-2" in page.evaluate("location.hash")


def test_map_status_legend(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """状態の印を押すと、その状態の項目をマップに出し・隠す（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=decisions&view=map")
    page.wait_for_selector("#decision-map .map-node.n-item")
    initial = page.eval_on_selector_all(
        ".legend input", "inputs => inputs.map(i => [i.value, i.checked])"
    )
    # 実行
    page.click('.legend label:has(input[value="決定済み"])')
    page.wait_for_selector('#decision-map button[data-node="D-1"]')
    shown = _map_item_ids(page)
    page.click('.legend label:has(input[value="保留"])')
    page.wait_for_function("!document.querySelector('#decision-map [data-node=\"D-4\"]')")
    # 検証
    assert initial == [["要見直し", True], ["未決定", True], ["保留", True], ["決定済み", False]]
    assert "D-1" in shown
    assert "D-4" not in _map_item_ids(page)


def test_map_keyword(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """キーワードを名前に含む項目を強調する（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=decisions&view=map")
    page.wait_for_selector("#decision-map .map-node.n-item")
    # 実行
    page.fill("input.map-q", "D-2")
    page.wait_for_selector("#decision-map .map-node.hit")
    # 検証
    hits = page.eval_on_selector_all(
        "#decision-map .map-node.hit", "nodes => nodes.map(n => n.dataset.node)"
    )
    assert hits == ["D-2"]


def test_map_zoom(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """拡大・縮小で倍率を変え、全体を表示で全体が収まる倍率に戻す（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=decisions&view=map")
    page.wait_for_selector("#decision-map .map-node.n-item")
    fit = page.locator(".zoom button", has_text="全体を表示")
    assert fit.get_attribute("aria-pressed") == "true"
    # 実行・検証
    page.click('.zoom button[aria-label="拡大"]')
    page.wait_for_function(
        "document.querySelector('.zoom .btn').getAttribute('aria-pressed') === 'false'"
    )
    page.click(".zoom .btn")
    page.wait_for_function(
        "document.querySelector('.zoom .btn').getAttribute('aria-pressed') === 'true'"
    )


def test_map_when_narrow(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """幅が狭いと、マップを字下げの一覧に切り替え、押すと詳細を開く（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=decisions&view=map")
    page.set_viewport_size({"width": NARROW_WIDTH, "height": NARROW_HEIGHT})
    # 実行
    page.wait_for_selector("nav.map-outline", state="visible")
    # 検証
    assert page.is_visible("nav.map-outline")
    assert not page.is_visible("#decision-map")
    page.click('nav.map-outline button[data-id="D-3"]')
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "D-3の題"


def test_board(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """状態ごとの列にカードを並べ、カードを押すと詳細を開く（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=decisions&view=board")
    # 実行
    columns = page.eval_on_selector_all(
        ".board section.board-col",
        "cols => cols.map(c => [c.getAttribute('aria-label'), [...c.querySelectorAll('.card')].map(k => k.dataset.id)])",
    )
    page.click('.board button.card[data-id="D-5"]')
    # 検証
    assert columns == [
        ["要見直し", ["D-3"]],
        ["未決定", ["D-2", "D-5"]],
        ["保留", ["D-4"]],
        ["未整理", []],
        ["決定済み", ["D-1"]],
        ["対象外", []],
        ["取り下げ", []],
    ]
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "D-5の題"


def test_table_ready_column(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """表の「着手できる」は、build が埋め込んだ次の候補にある検討事項だけ「はい」にする（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=decisions&view=table")
    # 実行
    ready = page.eval_on_selector_all(
        "table.grid tbody tr",
        "rows => rows.map(r => [r.dataset.id, r.querySelector('td[data-col=\"7\"]').textContent])",
    )
    # 検証
    assert ready == [
        ["D-1", "いいえ"],
        ["D-2", "はい"],
        ["D-3", "いいえ"],
        ["D-4", "いいえ"],
        ["D-5", "はい"],
    ]
    # 行のタイトルを押すと詳細を開く
    page.click('table.grid button.row-open[data-id="D-4"]')
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "D-4の題"
