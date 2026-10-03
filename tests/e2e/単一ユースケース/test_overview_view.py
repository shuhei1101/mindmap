"""概要を見る（プレビューの概要のタイルを読み、タイルから条件の一覧を開く）の E2E テスト。"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page
from preview_helpers import BuildPreview, OpenPreview, row_ids
from workspace_fixtures import MakeItem

# ゴールまでのタイルが、納品物を全て出す上限の件数
DELIVERABLE_LIMIT = 5

# 納品物の資料の件数（上限を超える数）
MANY_DELIVERABLES = 6

# 保留の検討事項の件数（すべて表示の件数）
HOLD_COUNT = 2


def _goal_settings(valid_settings: dict[str, Any], doc_ids: list[str]) -> dict[str, Any]:
    """納品物が資料 doc_ids を指す設定を返す。"""
    return {
        **valid_settings,
        "goal": {
            "phase": "構成",
            "summary": "作り始められる",
            "deliverables": [{"title": f"{doc_id}の納品物", "doc": doc_id} for doc_id in doc_ids],
        },
    }


def _chips(page: Page) -> list[str]:
    """表の上に並んでいる条件のチップの文字を返す。"""
    return page.eval_on_selector_all(".chips .chip", "chips => chips.map(c => c.textContent)")


def test_normal(
    build_preview: BuildPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """タイルで次に検討する項目・ゴールまでの進捗・要見直し・保留・進行中のタスクを読み、要見直しの一覧を開く（正常系）。"""
    # 準備
    path = build_preview(
        make_item("D-2"),
        make_item("D-6", depends_on=["D-2"]),
        make_item("D-3", status="要見直し"),
        make_item("D-4", status="保留", depends_on=["D-6"]),
        make_item("T-3", status="保留"),
        make_item("T-2", status="進行中"),
        make_item("A-1", deliverable=True, status="完成"),
        make_item("A-2", deliverable=True, status="確認中"),
        settings=_goal_settings(valid_settings, ["A-1", "A-2"]),
        bodies={"A-1.md": "完成した資料\n", "A-2.md": "確認中の資料\n"},
    )
    # 実行
    page = open_preview(path)
    # 検証
    next_ids = page.eval_on_selector_all(
        "#tile-next button[data-id]", "buttons => buttons.map(b => b.dataset.id)"
    )
    assert next_ids == ["D-2"]
    assert page.inner_text("#h-goal") == "ゴールまでの進捗"
    checklist = page.eval_on_selector_all(
        "#tile-goal .checklist li",
        "items => items.map(i => [i.querySelector('button').textContent, i.classList.contains('done')])",
    )
    assert checklist == [["A-1の納品物", True], ["A-2の納品物", False]]
    review_ids = page.eval_on_selector_all(
        "#tile-review button[data-id]", "buttons => buttons.map(b => b.dataset.id)"
    )
    assert review_ids == ["D-3"]
    # 保留のタイルには名前だけを出し、待っている前提の補足の行と保留のタスクは出さない
    hold_ids = page.eval_on_selector_all(
        "#tile-hold button[data-id]", "buttons => buttons.map(b => b.dataset.id)"
    )
    assert hold_ids == ["D-4"]
    hold_text = page.inner_text("#tile-hold")
    assert "D-6" not in hold_text
    assert "T-3" not in hold_text
    running_ids = page.eval_on_selector_all(
        "#tile-running button[data-id]", "buttons => buttons.map(b => b.dataset.id)"
    )
    assert running_ids == ["T-2"]
    # 要見直しの「すべて表示」を押すと、検討事項の表を 状態 = 要見直し で絞って開く
    page.click("#tile-review .t-link")
    page.wait_for_selector("table.grid")
    assert _chips(page) == ["状態: 要見直し"]
    assert row_ids(page) == ["D-3"]
    hash_text = page.evaluate("location.hash")
    assert "tab=decisions" in hash_text
    assert "view=table" in hash_text


def test_normal_when_show_all_holds(
    build_preview: BuildPreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """保留のタイルのすべて表示で、保留の検討事項だけを表に出す（正常系）。"""
    # 準備
    path = build_preview(
        make_item("D-4", status="保留"),
        make_item("D-7", status="保留"),
        make_item("T-3", status="保留"),
    )
    # 実行
    page = open_preview(path)
    # 検証
    assert page.locator("#tile-hold .t-link").count() == 1
    assert page.inner_text("#tile-hold .t-link") == f"すべて表示（{HOLD_COUNT} 件）"
    assert "T-3" not in page.inner_text("#tile-hold")
    page.click("#tile-hold .t-link")
    page.wait_for_selector("table.grid")
    assert _chips(page) == ["状態: 保留"]
    assert row_ids(page) == ["D-4", "D-7"]


def test_normal_when_many_deliverables(
    build_preview: BuildPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """納品物が上限を超えると、先頭だけを出して、すべて表示で資料を納品物で絞って開く（正常系）。"""
    # 準備
    deliverable_ids = [f"A-{number}" for number in range(1, MANY_DELIVERABLES + 1)]
    other_id = f"A-{MANY_DELIVERABLES + 1}"
    path = build_preview(
        *[make_item(doc_id, deliverable=True, status="完成") for doc_id in deliverable_ids],
        make_item(other_id, deliverable=False),
        settings=_goal_settings(valid_settings, deliverable_ids),
        bodies={f"{doc_id}.md": "本文\n" for doc_id in [*deliverable_ids, other_id]},
    )
    # 実行
    page = open_preview(path)
    # 検証
    assert page.locator("#tile-goal .checklist li").count() == DELIVERABLE_LIMIT
    show_all = page.locator("#tile-goal .t-link")
    assert show_all.count() == 1
    show_all.click()
    page.wait_for_selector(".doc-card")
    assert _chips(page) == ["納品物: 納品物"]
    cards = page.eval_on_selector_all(".doc-card", "cards => cards.map(c => c.dataset.id)")
    assert sorted(cards) == deliverable_ids
    assert other_id not in cards
