"""部品設計『表示形式の切り替え』の状態（ストーリー）の結合テスト。"""

from __future__ import annotations

import pytest
from storybook_fixture_types import OpenStory

# 部品設計の CSS カスタムプロパティ `--view-switch-item-width` の既定値（px）
ITEM_WIDTH = 96

# ボタンの並びと押されている形式を読む
BUTTONS_SCRIPT = """() => [...document.querySelectorAll('.segment button')].map(b => [
    b.dataset.view, b.textContent.trim(), b.getAttribute('aria-pressed'),
    Math.round(b.getBoundingClientRect().width), Math.round(b.getBoundingClientRect().left),
])"""


@pytest.mark.parametrize(
    ("story_id", "expected"),
    [
        pytest.param(
            "preview-viewswitch--decisions",
            [("map", "マップ", "true"), ("board", "ボード", "false"), ("table", "表", "false")],
            id="decisions",
        ),
        pytest.param(
            "preview-viewswitch--tasks",
            [("board", "ボード", "false"), ("table", "表", "true")],
            id="tasks",
        ),
        pytest.param(
            "preview-viewswitch--docs",
            [("cards", "カード", "true"), ("table", "表", "false")],
            id="docs",
        ),
    ],
)
def test_states(
    open_story: OpenStory, story_id: str, expected: list[tuple[str, str, str]]
) -> None:
    """形式ごとのボタンを並べ、選んでいる形式を aria-pressed で伝える。ボタンは同じ幅（正常系）。"""
    # 準備・実行
    page = open_story(story_id)
    buttons = page.evaluate(BUTTONS_SCRIPT)
    # 検証
    assert [tuple(row[:3]) for row in buttons] == expected
    assert {row[3] for row in buttons} == {ITEM_WIDTH}
    group = page.locator(".segment")
    assert group.get_attribute("role") == "group"
    assert group.get_attribute("aria-label") == "表示形式"


def test_same_left_position_across_states(open_story: OpenStory) -> None:
    """形式の数が違っても、左端の位置が同じになる（正常系）。"""
    # 準備・実行
    lefts = []
    for story_id in ("preview-viewswitch--decisions", "preview-viewswitch--tasks"):
        page = open_story(story_id)
        lefts.append(page.evaluate(BUTTONS_SCRIPT)[0][4])
    # 検証
    assert lefts[0] == lefts[1]
