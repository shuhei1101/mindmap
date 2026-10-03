"""画面設計『タスク』（ボード・表）の結合テスト。"""

from __future__ import annotations

from preview_fixture_types import OpenPreview, WriteSamplePreview


def test_board(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """状態ごとの列にカードを並べ、進める検討事項を出し、押すと詳細を開く（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=tasks")
    # 実行
    columns = page.eval_on_selector_all(
        ".board section.board-col",
        "cols => cols.map(c => [c.getAttribute('aria-label'), [...c.querySelectorAll('.card')].map(k => k.dataset.id)])",
    )
    running_for = page.inner_text('.board button.card[data-id="T-1"] .c-for')
    page.click('.board button.card[data-id="T-1"]')
    # 検証
    assert columns == [
        ["未着手", ["T-2"]],
        ["進行中", ["T-1"]],
        ["保留", []],
        ["完了", ["T-3"]],
        ["中止", []],
    ]
    assert "D-2の題" in running_for
    # 0 件の列には、種類の名前で空の旨を出す
    assert page.inner_text('.board section.board-col[aria-label="保留"] .empty') == "タスクはありません。"
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "T-1の題"


def test_view_switch(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """表示形式の切り替えは ボード・表 の 2 つで、既定はボード。表に切り替えると行を並べる（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=tasks")
    views = page.eval_on_selector_all(".segment button", "b => b.map(x => [x.dataset.view, x.getAttribute('aria-pressed')])")
    # 実行
    page.click('.segment button[data-view="table"]')
    page.wait_for_selector("table.grid")
    # 検証
    assert views == [["board", "true"], ["table", "false"]]
    rows = page.eval_on_selector_all("table.grid tbody tr", "rows => rows.map(r => r.dataset.id)")
    assert rows == ["T-1", "T-2", "T-3"]
    assert page.inner_text("main h1") == "タスク"


def test_table(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """表の「進める検討事項」の列から、その検討事項の詳細を開く（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path, "#tab=tasks&view=table")
    # 実行
    page.click('table.grid tr[data-id="T-1"] button.idlink')
    # 検証
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "D-2の題"
