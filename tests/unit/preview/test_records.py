"""core/records.ts（記録の索引・関係する項目・検索）の単体テスト。"""

from __future__ import annotations

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts, MakeData, MakeItem


def test_build_index(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """ID で引け、参照元を逆に引ける（正常系）。"""
    # 準備
    data = make_data(
        decisions=[make_item("D-1"), make_item("D-2", depends_on=["D-1"])],
        tasks=[make_item("T-1", **{"for": ["D-1"]})],
        next_ids=["D-1"],
    )
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """(data) => {
            const index = MindmapPreview.buildIndex(data);
            return {
                kind: index.byId.get("T-1").kind,
                referencedBy: index.referencedBy.get("D-1"),
                readyIds: [...index.readyIds],
            };
        }""",
        data,
    )
    # 検証
    assert result == {"kind": "tasks", "referencedBy": ["D-2", "T-1"], "readyIds": ["D-1"]}


def test_related_items(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """関係の種類ごとに分ける（正常系）。"""
    # 準備
    data = make_data(
        decisions=[
            make_item("D-1", depends_on=["D-0"]),
            make_item("D-2", depends_on=["D-1"]),
        ],
        tasks=[make_item("T-1", **{"for": ["D-1"]})],
        logs=[make_item("L-1", related=["D-1"])],
        notes=[make_item("N-1", related=["D-1"])],
    )
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """(data) => {
            const index = MindmapPreview.buildIndex(data);
            return MindmapPreview.relatedItems({id: "D-1", index});
        }""",
        data,
    )
    # 検証
    assert result["prerequisites"] == ["D-0"]
    assert result["successors"] == ["D-2"]
    assert result["tasks"] == ["T-1"]
    assert result["logs"] == ["L-1"]
    assert result["referencedBy"] == ["N-1"]


@pytest.mark.parametrize(
    ("query", "expected_ids"),
    [
        pytest.param("d-1", ["D-1"], id="id_case_insensitive"),
        pytest.param("ゼブラ", ["A-1"], id="body_only"),
        pytest.param("d-1 ゼブラ", [], id="only_one_word"),
        pytest.param("   ", [], id="blank"),
    ],
)
def test_search_items(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_data: MakeData,
    make_item: MakeItem,
    query: str,
    expected_ids: list[str],
) -> None:
    """全ての語を含む項目を返す（正常系）。"""
    # 準備
    data = make_data(
        decisions=[make_item("D-1"), make_item("D-2")],
        docs=[make_item("A-1")],
        bodies={"A-1.md": "ゼブラの話\n"},
    )
    load_preview_scripts()
    # 実行
    found = preview_page.evaluate(
        """({data, query}) => {
            const index = MindmapPreview.buildIndex(data);
            return MindmapPreview.searchItems({query, index}).map((hit) => hit.id);
        }""",
        {"data": data, "query": query},
    )
    # 検証
    assert found == expected_ids
