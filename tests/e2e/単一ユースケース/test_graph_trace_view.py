"""つながりを辿る（3D のつながりで玉を押して詳細を開き、種類を非表示にする）の E2E テスト。"""

from __future__ import annotations

from typing import Any

from preview_helpers import BuildPreview, OpenPreview, click_item_ball
from workspace_fixtures import MakeItem

# 種類の切り替えの並びの key
KIND_VALUES = ["decisions", "tasks", "research", "docs", "terms", "notes", "logs"]

# 非表示にした種類の色の点の不透明度
HIDDEN_DOT_OPACITY = "0.25"

# 種類の色の点を色ごとに読む
DOT_COLORS_SCRIPT = """() => [...document.querySelectorAll('.legend label')].map(
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
        ".legend input", "inputs => inputs.map(i => i.value)"
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
