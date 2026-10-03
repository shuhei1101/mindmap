"""画面設計『つながり』（キャンバスは項目 ID `graph-canvas`）の結合テスト。"""

from __future__ import annotations

from playwright.sync_api import Page
from preview_fixture_types import OpenPreview, WriteSamplePreview

# 種類の切り替えの並び（検討事項・タスク・調査・資料・用語集・メモ・会話ログ）
KIND_VALUES = ["decisions", "tasks", "research", "docs", "terms", "notes", "logs"]

# 狭い幅の画面の大きさ（空の旨の文はどの幅でも出す）
NARROW_WIDTH = 800
NARROW_HEIGHT = 700

# まとめて切り替える箱（項目の種類の並びの右端）と、その読み上げの名前
TOGGLE_ALL_BOX = ".legend .legend-all-check input"
TOGGLE_ALL_LABEL = "すべての種類を表示"

# 全ての種類を隠したときに出す文
NO_SHOWN_KIND_TEXT = "表示する種類の項目はありません"

# 項目の種類のチェックボックス（まとめて切り替える箱を除く）
KIND_INPUTS = ".legend label:not(.legend-all-check) input"

# キャンバスに描かれた画素のうち、背景以外が 1 つでもあるかを調べる
HAS_DRAWING_SCRIPT = """() => {
    const canvas = document.getElementById('graph-canvas');
    const data = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
    for (let i = 3; i < data.length; i += 4) if (data[i] !== 0) return true;
    return false;
}"""


def test_canvas(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """3D のキャンバスに全種類の項目と関連を描く（正常系）。"""
    # 準備
    path = write_sample_preview()
    # 実行
    page = open_preview(path, "#tab=graph")
    page.wait_for_function(HAS_DRAWING_SCRIPT)
    # 検証
    assert page.get_attribute("#graph-canvas", "role") == "img"
    assert page.inner_text("main h1") == "つながり"
    assert page.get_attribute('nav.tabbar a[data-tab="graph"]', "aria-current") == "page"


def test_kind_toggles(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """種類ごとに表示 / 非表示を切り替え、件数を出す（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=graph")
    page.wait_for_function(HAS_DRAWING_SCRIPT)
    toggles = page.eval_on_selector_all(
        ".legend label:not(.legend-all-check)", "labels => labels.map(l => [l.querySelector('input').value, l.querySelector('.n').textContent, l.querySelector('input').checked])"
    )
    # 実行
    page.click('.legend label:has(input[value="logs"])')
    # 検証
    assert toggles == [
        ["decisions", "5", True],
        ["tasks", "3", True],
        ["research", "1", True],
        ["docs", "2", True],
        ["terms", "1", True],
        ["notes", "1", True],
        ["logs", "1", True],
    ]
    assert [row[0] for row in toggles] == KIND_VALUES
    assert page.is_checked('.legend input[value="logs"]') is False
    # 非表示の種類は、見た目も変わる（種類の色の点が薄くなる）
    assert page.evaluate(
        "getComputedStyle(document.querySelector('.legend label:has(input[value=\"logs\"]) .kdot')).opacity"
    ) == "0.35"
    assert page.is_checked('.legend input[value="decisions"]') is True


def test_open_item_from_hash(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """ハッシュの id で項目を選ぶと、詳細パネルを開いたままキャンバスを保つ（正常系）。"""
    # 準備
    path = write_sample_preview()
    # 実行
    page = open_preview(path, "#tab=graph&id=D-2")
    page.wait_for_selector("aside.panel.open")
    # 検証
    assert page.inner_text("aside.panel .d-title") == "D-2の題"
    assert page.locator("#graph-canvas").count() == 1


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


def _kind_checks(page: Page) -> list[bool]:
    """項目の種類のチェックを、並びの順に返す。"""
    return page.eval_on_selector_all(KIND_INPUTS, "inputs => inputs.map(i => i.checked)")


def test_kind_toggle_all_box(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """項目の種類の右端の箱を押すと、全ての種類を出し・隠し、各種類のチェックをそろえる（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=graph")
    page.wait_for_function(HAS_DRAWING_SCRIPT)
    initial = _toggle_all_box(page)
    # 実行・検証（チェックのとき: 全て隠す）
    page.click(TOGGLE_ALL_BOX)
    after_all_hidden = _toggle_all_box(page)
    all_hidden_checks = _kind_checks(page)
    # 実行・検証（空のとき: 全ての種類を表示）
    page.click(TOGGLE_ALL_BOX)
    after_all_shown = _toggle_all_box(page)
    all_shown_checks = _kind_checks(page)
    # 実行・検証（1 つだけ隠すと横棒）
    page.click('.legend label:has(input[value="logs"])')
    after_one_hidden = _toggle_all_box(page)
    # 実行・検証（横棒のとき: 全ての種類を表示）
    page.click(TOGGLE_ALL_BOX)
    after_all_shown_from_some = _toggle_all_box(page)
    # 検証
    assert initial == {
        "checked": True,
        "indeterminate": False,
        "ariaLabel": TOGGLE_ALL_LABEL,
        "last": True,
    }
    assert (after_all_hidden["checked"], after_all_hidden["indeterminate"]) == (False, False)
    assert all_hidden_checks == [False] * len(KIND_VALUES)
    assert (after_all_shown["checked"], after_all_shown["indeterminate"]) == (True, False)
    assert all_shown_checks == [True] * len(KIND_VALUES)
    assert (after_one_hidden["checked"], after_one_hidden["indeterminate"]) == (False, True)
    assert (after_all_shown_from_some["checked"], after_all_shown_from_some["indeterminate"]) == (
        True,
        False,
    )


def test_no_shown_kind_note(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """全ての種類を隠すと、どの幅でも枠の中央に空の旨を出す。1 つでも出すと消す（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=graph")
    page.wait_for_function(HAS_DRAWING_SCRIPT)
    shown_before = page.is_visible("p.map-empty")
    # 実行（全て隠す）
    page.click(TOGGLE_ALL_BOX)
    page.wait_for_selector("p.map-empty", state="visible")
    # 検証（広い幅）
    assert shown_before is False
    assert page.inner_text("p.map-empty") == NO_SHOWN_KIND_TEXT
    # 実行（狭い幅へ）
    page.set_viewport_size({"width": NARROW_WIDTH, "height": NARROW_HEIGHT})
    page.wait_for_selector("p.map-empty", state="visible")
    # 検証（狭い幅）
    assert page.inner_text("p.map-empty") == NO_SHOWN_KIND_TEXT
    # 実行（1 つ戻す）
    page.click('.legend label:has(input[value="decisions"])')
    page.wait_for_selector("p.map-empty", state="hidden")
    # 検証
    assert page.is_visible("p.map-empty") is False


def test_kind_chip_style(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """項目の種類のチップは、枠と表示中・非表示の見た目を状態の印にそろえ、非表示は点線の枠にして打ち消し線は付けない（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=graph")
    page.wait_for_function(HAS_DRAWING_SCRIPT)
    page.click('.legend label:has(input[value="logs"])')
    # 実行
    styles = page.evaluate(
        """() => {
            const read = (value) => {
                const chip = document.querySelector(`.legend label:has(input[value="${value}"])`);
                const style = getComputedStyle(chip);
                return {
                    borderStyle: style.borderTopStyle,
                    borderWidth: style.borderTopWidth,
                    textDecoration: style.textDecorationLine,
                    fontWeight: style.fontWeight,
                };
            };
            return {shown: read('decisions'), hidden: read('logs')};
        }"""
    )
    box_label_style = page.evaluate(
        "getComputedStyle(document.querySelector('.legend .legend-all-check')).borderTopStyle"
    )
    # 検証
    assert styles["shown"]["borderStyle"] == "solid"
    assert styles["hidden"]["borderStyle"] == "dashed"
    assert styles["shown"]["borderWidth"] == styles["hidden"]["borderWidth"] == "1px"
    assert styles["shown"]["textDecoration"] == styles["hidden"]["textDecoration"] == "none"
    assert styles["shown"]["fontWeight"] == styles["hidden"]["fontWeight"]
    assert box_label_style == "none"
