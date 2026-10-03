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

# サンプルの記録が持つ状態（状態の印の並びの順）
SAMPLE_STATUSES = ["要見直し", "未決定", "保留", "決定済み"]

# まとめて切り替える箱（状態の印の並びの右端）と、その読み上げの名前
TOGGLE_ALL_BOX = ".legend .legend-all-check input"
TOGGLE_ALL_LABEL = "すべての状態を表示"

# 全ての状態を隠したときに出す文
NO_SHOWN_STATUS_TEXT = "表示する状態の検討事項はありません"

# 状態の印のチェックボックス（まとめて切り替える箱を除く）
STATUS_INPUTS = ".legend label:not(.legend-all-check) input"

# チェックの記号の見た目の中心が、箱の中心からずれてよい幅（px。チェックの形の偏りを許す）
CHECK_CENTER_TOLERANCE = 1

# マップに検討事項が 1 件も描かれていない
NO_MAP_ITEM_SCRIPT = "!document.querySelector('#decision-map .map-node.n-item')"


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
        ".legend label:not(.legend-all-check) input", "inputs => inputs.map(i => [i.value, i.checked])"
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


def _toggle_all_box(page: Page) -> dict[str, object]:
    """まとめて切り替える箱の、チェック・横棒・読み上げの名前・並びの右端かを返す。"""
    return page.eval_on_selector(
        TOGGLE_ALL_BOX,
        """box => ({
            checked: box.checked,
            indeterminate: box.indeterminate,
            ariaLabel: box.getAttribute('aria-label'),
            last: box.closest('.legend').lastElementChild === box.closest('label'),
        })""",
    )


def _status_checks(page: Page) -> list[bool]:
    """状態の印のチェックを、並びの順に返す。"""
    return page.eval_on_selector_all(STATUS_INPUTS, "inputs => inputs.map(i => i.checked)")


def _border_style(page: Page, selector: str) -> str:
    """要素の枠線の種類（実線・点線・なし）を返す。"""
    return page.evaluate(
        "selector => getComputedStyle(document.querySelector(selector)).borderTopStyle", selector
    )


def test_map_toggle_all_box(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """状態の印の右端の箱を押すと、全ての状態を出し・隠し、各状態の印のチェックをそろえる（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=decisions&view=map")
    page.wait_for_selector("#decision-map .map-node.n-item")
    initial = _toggle_all_box(page)
    initial_checks = _status_checks(page)
    # 実行・検証（横棒のとき: 全ての状態を表示）
    page.click(TOGGLE_ALL_BOX)
    page.wait_for_selector('#decision-map button[data-node="D-1"]')
    after_all_shown = _toggle_all_box(page)
    all_shown_checks = _status_checks(page)
    # 実行・検証（チェックのとき: 全て隠す）
    page.click(TOGGLE_ALL_BOX)
    page.wait_for_function(NO_MAP_ITEM_SCRIPT)
    after_all_hidden = _toggle_all_box(page)
    all_hidden_checks = _status_checks(page)
    # 実行・検証（空のとき: 全ての状態を表示）
    page.click(TOGGLE_ALL_BOX)
    page.wait_for_selector('#decision-map button[data-node="D-1"]')
    after_all_shown_again = _toggle_all_box(page)
    # 実行・検証（1 つだけ隠すと横棒）
    page.click('.legend label:has(input[value="保留"])')
    page.wait_for_function("!document.querySelector('#decision-map [data-node=\"D-4\"]')")
    after_one_hidden = _toggle_all_box(page)
    # 検証
    assert initial == {
        "checked": False,
        "indeterminate": True,
        "ariaLabel": TOGGLE_ALL_LABEL,
        "last": True,
    }
    assert initial_checks == [True, True, True, False]
    assert (after_all_shown["checked"], after_all_shown["indeterminate"]) == (True, False)
    assert all_shown_checks == [True, True, True, True]
    assert (after_all_hidden["checked"], after_all_hidden["indeterminate"]) == (False, False)
    assert all_hidden_checks == [False, False, False, False]
    assert (after_all_shown_again["checked"], after_all_shown_again["indeterminate"]) == (True, False)
    assert (after_one_hidden["checked"], after_one_hidden["indeterminate"]) == (False, True)


def test_map_no_shown_status_note(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """全ての状態を隠すと、幅 901px 以上はマップの枠の中央、900px 以下は字下げの一覧に空の旨を出す（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=decisions&view=map")
    page.wait_for_selector("#decision-map .map-node.n-item")
    shown_before = page.is_visible("p.map-empty")
    # 実行（全ての状態を隠す。横棒 → 全て表示 → 全て隠す）
    page.click(TOGGLE_ALL_BOX)
    page.wait_for_selector('#decision-map button[data-node="D-1"]')
    page.click(TOGGLE_ALL_BOX)
    page.wait_for_function(NO_MAP_ITEM_SCRIPT)
    # 検証（広い幅: マップの枠の中央）
    assert shown_before is False
    assert page.inner_text("p.map-empty") == NO_SHOWN_STATUS_TEXT
    assert not page.is_visible("nav.map-outline")
    # 実行（狭い幅へ）
    page.set_viewport_size({"width": NARROW_WIDTH, "height": NARROW_HEIGHT})
    page.wait_for_selector("nav.map-outline", state="visible")
    # 検証（狭い幅: 字下げの一覧）
    assert page.inner_text("nav.map-outline p.empty") == NO_SHOWN_STATUS_TEXT
    assert not page.is_visible("p.map-empty")
    # 実行（1 つ戻すと、空の旨を消す）
    page.click('.legend label:has(input[value="未決定"])')
    page.wait_for_selector('nav.map-outline button[data-id="D-2"]')
    # 検証
    assert page.locator("nav.map-outline p.empty").count() == 0


def test_map_status_chip_border(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """非表示の状態の印は枠を点線にして、表示中と見分ける。まとめて切り替える箱の枠は点線にしない（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=decisions&view=map")
    page.wait_for_selector("#decision-map .map-node.n-item")
    # 実行
    shown_style = _border_style(page, '.legend label:has(input[value="未決定"])')
    hidden_style = _border_style(page, '.legend label:has(input[value="決定済み"])')
    box_label_style = _border_style(page, ".legend .legend-all-check")
    # 検証
    assert shown_style == "solid"
    assert hidden_style == "dashed"
    assert box_label_style == "none"


def test_map_toggle_all_box_appearance(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """箱は背景を透過にして枠と記号だけで描き、枠は印の枠と同じ色、横棒も枠線で描き、チェックは箱の中心に置く（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=decisions&view=map")
    page.wait_for_selector("#decision-map .map-node.n-item")
    # 実行（初期は横棒）
    box = page.evaluate(
        """box => {
            const input = document.querySelector(box);
            const chip = document.querySelector('.legend label:has(input[value="未決定"])');
            const bar = getComputedStyle(input, '::after');
            return {
                background: getComputedStyle(input).backgroundColor,
                borderWidth: getComputedStyle(input).borderTopWidth,
                borderColor: getComputedStyle(input).borderTopColor,
                chipBorderColor: getComputedStyle(chip).borderTopColor,
                barStyle: bar.borderTopStyle,
                barWidth: bar.borderTopWidth,
            };
        }""",
        TOGGLE_ALL_BOX,
    )
    # 実行（押して全部表示にし、チェックの記号の見た目の中心と箱の中心のずれを測る）
    page.click(TOGGLE_ALL_BOX)
    page.wait_for_selector('#decision-map button[data-node="D-1"]')
    check = page.evaluate(
        """box => {
            const input = document.querySelector(box);
            const mark = getComputedStyle(input, '::after');
            const px = (name) => parseFloat(mark.getPropertyValue(name));
            // 記号の枠の外形。回転は中心を動かさないので、中心へ寄せる移動だけを足す
            const width = px('width') + px('border-left-width') + px('border-right-width');
            const height = px('height') + px('border-top-width') + px('border-bottom-width');
            const move = new DOMMatrix(mark.transform);
            return {
                dx: px('left') + width / 2 + move.e - input.clientWidth / 2,
                dy: px('top') + height / 2 + move.f - input.clientHeight / 2,
            };
        }""",
        TOGGLE_ALL_BOX,
    )
    # 検証
    assert box["background"] == "rgba(0, 0, 0, 0)"
    assert box["borderWidth"] == "1px"
    assert box["borderColor"] == box["chipBorderColor"]
    # 横棒は枠線で描く（線の太さは画面の倍率で丸められるため、線があることだけを確かめる）
    assert box["barStyle"] == "solid"
    assert box["barWidth"] != "0px"
    assert abs(check["dx"]) <= CHECK_CENTER_TOLERANCE
    assert abs(check["dy"]) <= CHECK_CENTER_TOLERANCE
