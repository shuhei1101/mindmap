"""画面設計『記録の表』（調査・用語集・メモ・会話ログ）の結合テスト。"""

from __future__ import annotations

import pytest
from preview_fixture_types import OpenPreview, WriteSamplePreview


@pytest.mark.parametrize(
    ("tab", "name", "row_id", "headers"),
    [
        pytest.param(
            "research", "調査", "R-1", ["ID", "タイトル", "問い", "結論", "確度", "タグ"], id="research"
        ),
        pytest.param(
            "terms", "用語集", "G-1", ["ID", "用語", "意味", "別名", "使わない表記", "タグ"], id="terms"
        ),
        pytest.param(
            "notes", "メモ", "N-1", ["ID", "タイトル", "内容", "タグ", "関連"], id="notes"
        ),
        pytest.param(
            "logs", "会話ログ", "L-1", ["ID", "日付", "タイトル", "更新した項目"], id="logs"
        ),
    ],
)
def test_table(
    write_sample_preview: WriteSamplePreview,
    open_preview: OpenPreview,
    tab: str,
    name: str,
    row_id: str,
    headers: list[str],
) -> None:
    """種類ごとの列を持つ表だけを出し（表示形式の切り替えは出さない）、行を押すと詳細を開く（正常系）。"""
    # 準備
    path = write_sample_preview()
    # 実行
    page = open_preview(path, f"#tab={tab}")
    # 検証
    assert page.inner_text("main h1") == name
    assert page.locator(".segment").count() == 0
    assert page.get_attribute(".table-block", "data-kind") == tab
    assert page.eval_on_selector_all(
        "table.grid thead .th-sort", "buttons => buttons.map(b => b.textContent)"
    ) == headers
    page.click(f'table.grid tr[data-id="{row_id}"] button.row-open')
    page.wait_for_selector("aside.panel.open")
    assert row_id in page.inner_text("aside.panel .panel-kind")
