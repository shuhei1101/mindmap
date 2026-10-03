"""core/router.ts（URL のハッシュの読み書きと履歴）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts, MakeData, MakeItem


@pytest.mark.parametrize(
    ("hash_text", "tab", "view", "item_id", "full", "filters"),
    [
        pytest.param("", "overview", "table", None, False, {}, id="empty"),
        pytest.param(
            "#tab=decisions&view=table&id=D-1&f.status=要見直し|保留",
            "decisions",
            "table",
            "D-1",
            False,
            {"status": ["要見直し", "保留"]},
            id="filters",
        ),
        pytest.param(
            "#tab=nope&view=cards", "overview", "table", None, False, {}, id="unknown_tab"
        ),
        pytest.param(
            "#tab=decisions&id=D-99&full=1", "decisions", "map", None, False, {}, id="unknown_id"
        ),
        pytest.param("#tab=tasks&view=map", "tasks", "board", None, False, {}, id="unknown_view"),
    ],
)
def test_parse_hash(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_data: MakeData,
    make_item: MakeItem,
    hash_text: str,
    tab: str,
    view: str,
    item_id: str | None,
    full: bool,
    filters: dict[str, list[str]],
) -> None:
    """既定と誤った値を扱う（正常系）。"""
    # 準備
    data = make_data(decisions=[make_item("D-1")])
    load_preview_scripts()
    # 実行
    route = preview_page.evaluate(
        """({data, hash}) => {
            const index = MindmapPreview.buildIndex(data);
            return MindmapPreview.parseHash({hash, index});
        }""",
        {"data": data, "hash": hash_text},
    )
    # 検証
    assert route["tab"] == tab
    assert route["view"] == view
    assert route["id"] == item_id
    assert route["full"] is full
    assert route["filters"] == filters


@pytest.mark.parametrize(
    ("route", "expected"),
    [
        pytest.param(
            {"tab": "overview", "view": "table", "id": None, "full": False, "filters": {}},
            "",
            id="defaults",
        ),
        pytest.param(
            {
                "tab": "decisions",
                "view": "table",
                "id": "D-1",
                "full": True,
                "filters": {"status": ["未決定"]},
            },
            "#tab=decisions&view=table&id=D-1&full=1",
            id="full_with_filters",
        ),
    ],
)
def test_to_hash(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    route: dict[str, Any],
    expected: str,
) -> None:
    """既定の値を書かない（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    hash_text = preview_page.evaluate("(route) => MindmapPreview.toHash(route)", route)
    # 検証
    assert hash_text == expected


@pytest.mark.parametrize(
    ("push", "history_delta"),
    [
        pytest.param(True, 1, id="push"),
        pytest.param(False, 0, id="replace"),
    ],
)
def test_navigate(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    push: bool,
    history_delta: int,
) -> None:
    """積むか置き換えるかで履歴の長さが変わる（正常系）。"""
    # 準備
    route = {"tab": "decisions", "view": "table", "id": "D-1", "full": False, "filters": {}}
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """({route, push}) => {
            const before = history.length;
            MindmapPreview.navigate({route, push});
            return {delta: history.length - before, hash: location.hash};
        }""",
        {"route": route, "push": push},
    )
    # 検証
    assert result == {"delta": history_delta, "hash": "#tab=decisions&view=table&id=D-1"}
