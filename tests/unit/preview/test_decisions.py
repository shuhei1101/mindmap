"""screens/decisions.ts（検討事項の画面とマップの木）の単体テスト。"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts, MakeData, MakeItem


def test_build_decision_tree(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_data: MakeData,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """非表示の状態だけの枝を落とす（正常系）。"""
    # 準備
    settings = {
        **valid_settings,
        "categories": [
            {"name": "カテゴリー甲", "target": "mindmap", "summary": "甲"},
            {"name": "カテゴリー乙", "target": "mindmap", "summary": "乙"},
        ],
    }
    data = make_data(
        settings=settings,
        decisions=[
            make_item(
                "D-1", target="mindmap", category="カテゴリー甲", phase="要件", status="未決定"
            ),
            make_item(
                "D-2", target="mindmap", category="カテゴリー乙", phase="要件", status="決定済み"
            ),
        ],
    )
    load_preview_scripts()
    # 実行
    tree = preview_page.evaluate(
        """({data, shown}) => {
            const index = MindmapPreview.buildIndex(data);
            const graph = MindmapPreview.buildDecisionTree({index, shownStatuses: new Set(shown)});
            // 節は入れ子でも平らでも数えられるよう、再帰で集める
            const collect = (nodes) => nodes.flatMap((node) => [node.id, ...collect(node.children ?? [])]);
            return {nodeIds: collect(graph.children), edgeCount: graph.edges.length};
        }""",
        {"data": data, "shown": ["未決定"]},
    )
    # 検証
    node_ids = tree["nodeIds"]
    assert "D-1" in node_ids
    assert "D-2" not in node_ids
    # 検討事項 D-1 とその対象・カテゴリー・フェーズの 4 つだけが残り、枝は 3 本
    assert len(node_ids) == 4
    assert len([node_id for node_id in node_ids if node_id.startswith("target:")]) == 1
    assert tree["edgeCount"] == 3
