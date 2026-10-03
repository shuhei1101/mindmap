"""つながりを辿る（3D のつながりで玉を押して詳細を開き、種類を非表示にする）の E2E テスト。"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page
from preview_helpers import (
    BuildPreview,
    OpenPreview,
    click_item_ball,
    count_balls,
    shown_ball_item_ids,
)
from workspace_fixtures import MakeItem

# 種類の切り替えの並びの key
KIND_VALUES = ["decisions", "tasks", "research", "docs", "terms", "notes", "logs"]

# 非表示にした種類の色の点の不透明度
HIDDEN_DOT_OPACITY = "0.35"

# まとめて切り替える箱（項目の種類の並びの右端）と、項目の種類のチェックボックス（箱を除く）
TOGGLE_ALL_BOX = ".legend .legend-all-check input"
KIND_INPUTS = ".legend label:not(.legend-all-check) input"

# 7 種類の項目を 1 つずつ指す ID（検討事項・タスク・調査・資料・用語集・メモ・会話ログ）
ONE_ITEM_PER_KIND = ["D-1", "T-2", "R-1", "A-1", "G-1", "N-1", "L-1"]

# 検討事項の ID（記録の検討事項は D-1 と D-3）
DECISION_IDS = {"D-1", "D-3"}

# 種類の色の点を色ごとに読む
DOT_COLORS_SCRIPT = """() => [...document.querySelectorAll('.legend label:not(.legend-all-check)')].map(
    l => getComputedStyle(l.querySelector('.kdot')).backgroundColor
)"""


def _records(make_item: MakeItem) -> list[dict[str, Any]]:
    """7 種類の項目を 1 件以上ずつ。D-3 は前提 D-1・進めるタスク T-2・関連 R-1 とつながる。"""
    return [
        make_item("D-1", status="決定済み"),
        make_item("D-3", status="要見直し", depends_on=["D-1"], related=["R-1"]),
        make_item("T-2", status="進行中", **{"for": ["D-3"]}),
        make_item("R-1", question="何を調べたか"),
        make_item("A-1"),
        make_item("G-1"),
        make_item("N-1"),
        make_item("L-1"),
    ]


def test_normal(
    build_preview: BuildPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """種類ごとの色で出し、D-3 の玉を押して詳細を開き、会話ログを非表示にする（正常系）。"""
    # 準備
    path = build_preview(
        *_records(make_item), settings=valid_settings, bodies={"A-1.md": "資料の本文\n"}
    )
    page = open_preview(path)
    # 実行・検証（開く）
    page.click('nav.tabbar a[data-tab="graph"]')
    page.wait_for_selector("#graph-canvas")
    kinds = page.eval_on_selector_all(
        KIND_INPUTS, "inputs => inputs.map(i => i.value)"
    )
    assert kinds == KIND_VALUES
    counts = page.eval_on_selector_all(
        ".legend label .n", "counts => counts.map(c => Number(c.textContent))"
    )
    assert all(count >= 1 for count in counts)
    colors = page.evaluate(DOT_COLORS_SCRIPT)
    assert len(set(colors)) == len(KIND_VALUES)
    # D-3 の玉を押すと、詳細パネルに D-3 が開き、URL のハッシュがつながりと D-3 を指す
    click_item_ball(page, "D-3")
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "D-3の題"
    hash_text = page.evaluate("location.hash")
    assert "tab=graph" in hash_text
    assert "id=D-3" in hash_text
    # 会話ログを非表示にすると、切り替えが非表示の見た目に変わり、押された状態も変わる
    page.click('.legend label:has(input[value="logs"])')
    assert page.is_checked('.legend input[value="logs"]') is False
    dot_opacity = page.evaluate(
        "getComputedStyle(document.querySelector('.legend label:has(input[value=\"logs\"]) .kdot')).opacity"
    )
    assert dot_opacity == HIDDEN_DOT_OPACITY
    assert page.is_checked('.legend input[value="decisions"]') is True


def _toggle_all_box(page: Page) -> dict[str, bool]:
    """まとめて切り替える箱の、チェック・横棒・項目の種類の並びの右端かを返す。"""
    return page.eval_on_selector(
        TOGGLE_ALL_BOX,
        """box => ({
            checked: box.checked,
            indeterminate: box.indeterminate,
            last: box.closest('.legend').lastElementChild === box.closest('label'),
        })""",
    )


def _kind_checks(page: Page) -> list[bool]:
    """項目の種類のチェックを、並びの順に返す。"""
    return page.eval_on_selector_all(KIND_INPUTS, "inputs => inputs.map(i => i.checked)")


def _click_ball_of_each_kind(page: Page) -> None:
    """7 種類の項目の玉を、種類ごとに 1 つずつ押して見つける（無ければ失敗する）。"""
    for item_id in ONE_ITEM_PER_KIND:
        click_item_ball(page, item_id)


def test_normal_when_toggle_all_kinds(
    build_preview: BuildPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """まとめて切り替える箱で全ての種類を隠し・出し、箱と種類のチェックをそろえる（正常系）。"""
    # 準備
    path = build_preview(
        *_records(make_item), settings=valid_settings, bodies={"A-1.md": "資料の本文\n"}
    )
    # 実行・検証（開く: 全種類の玉と線と、チェックの入った箱）
    page = open_preview(path, "#tab=graph")
    page.wait_for_selector("#graph-canvas")
    assert _toggle_all_box(page) == {"checked": True, "indeterminate": False, "last": True}
    _click_ball_of_each_kind(page)
    # 実行・検証（1 回目: 全ての種類を隠す）
    page.keyboard.press("Escape")
    page.wait_for_function("!document.querySelector('aside.panel.open')")
    page.click(TOGGLE_ALL_BOX)
    assert count_balls(page) == 0
    assert _toggle_all_box(page) == {"checked": False, "indeterminate": False, "last": True}
    assert _kind_checks(page) == [False] * len(KIND_VALUES)
    # 実行・検証（検討事項だけを表示する）
    page.click('.legend label:has(input[value="decisions"])')
    assert _toggle_all_box(page) == {"checked": False, "indeterminate": True, "last": True}
    decision_ids = shown_ball_item_ids(page)
    assert decision_ids
    assert decision_ids <= DECISION_IDS
    # 実行・検証（2 回目: 全ての種類を出す）
    page.click(TOGGLE_ALL_BOX)
    assert _toggle_all_box(page) == {"checked": True, "indeterminate": False, "last": True}
    assert _kind_checks(page) == [True] * len(KIND_VALUES)
    _click_ball_of_each_kind(page)
