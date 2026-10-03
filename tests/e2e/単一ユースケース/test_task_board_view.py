"""タスクをボードで見る（状態ごとの列のボードで見て、カードから詳細を開く）の E2E テスト。"""

from __future__ import annotations

from typing import Any

from preview_helpers import BuildPreview, OpenPreview, row_ids
from workspace_fixtures import MakeItem

# ボードの列の並び（タスクの状態の順）
TASK_COLUMNS = ["未着手", "進行中", "保留", "完了", "中止"]


def test_normal(
    build_preview: BuildPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """状態ごとの 5 列にタスクを並べ、カードから進める検討事項を読み、表に切り替える（正常系）。"""
    # 準備
    path = build_preview(
        make_item("D-3", status="要見直し"),
        make_item("T-1", status="未着手"),
        make_item("T-2", status="進行中", **{"for": ["D-3"]}),
        make_item("T-3", status="保留"),
        make_item("T-4", status="完了"),
        make_item("T-5", status="中止"),
        settings=valid_settings,
    )
    # 実行
    page = open_preview(path, "#tab=tasks")
    columns = page.eval_on_selector_all(
        ".board section.board-col",
        "cols => cols.map(c => [c.getAttribute('aria-label'), [...c.querySelectorAll('.card')].map(k => k.dataset.id)])",
    )
    # 検証（ボード）
    assert [name for name, _ in columns] == TASK_COLUMNS
    assert dict(columns) == {
        "未着手": ["T-1"],
        "進行中": ["T-2"],
        "保留": ["T-3"],
        "完了": ["T-4"],
        "中止": ["T-5"],
    }
    # T-2 の詳細パネルに、進める検討事項として D-3 がある
    page.click('.board button.card[data-id="T-2"]')
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "T-2の題"
    targets = page.eval_on_selector_all(
        "aside.panel .d-sec:has(h3:text-is('進める検討事項')) button.idlink",
        "buttons => buttons.map(b => b.textContent)",
    )
    assert targets == ["D-3"]
    # 表に切り替えると 5 行ある
    page.click('.segment button[data-view="table"]')
    page.wait_for_selector("table.grid")
    assert row_ids(page) == ["T-1", "T-2", "T-3", "T-4", "T-5"]
