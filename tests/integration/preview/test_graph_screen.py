"""画面設計『つながり』（キャンバスは項目 ID `graph-canvas`）の結合テスト。"""

from __future__ import annotations

from preview_fixture_types import OpenPreview, WriteSamplePreview

# 種類の切り替えの並び（検討事項・タスク・調査・資料・用語集・メモ・会話ログ）
KIND_VALUES = ["decisions", "tasks", "research", "docs", "terms", "notes", "logs"]

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
        ".legend label", "labels => labels.map(l => [l.querySelector('input').value, l.querySelector('.n').textContent, l.querySelector('input').checked])"
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
