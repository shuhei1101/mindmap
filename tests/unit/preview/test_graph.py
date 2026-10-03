"""graph/graph.ts（つながり）の単体テスト。"""

from __future__ import annotations

from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts, MakeData, MakeItem

# 表示する種類（メモを外す）
SHOWN_KINDS = ["decisions", "tasks", "research", "docs", "terms", "logs"]


def test_build_graph(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    make_data: MakeData,
    make_item: MakeItem,
) -> None:
    """線の種類を分け、非表示の種類の線を落とす（正常系）。"""
    # 準備
    data = make_data(
        decisions=[make_item("D-1"), make_item("D-2", depends_on=["D-1"], sources=["R-1"])],
        tasks=[make_item("T-1", **{"for": ["D-1"]})],
        research=[make_item("R-1")],
        notes=[make_item("N-1", related=["D-1"])],
    )
    load_preview_scripts()
    # 実行
    graph = preview_page.evaluate(
        """({data, shown}) => {
            const index = MindmapPreview.buildIndex(data);
            return MindmapPreview.buildGraph({index, shownKinds: new Set(shown)});
        }""",
        {"data": data, "shown": SHOWN_KINDS},
    )
    # 検証
    links = sorted((link["type"], link["source"], link["target"]) for link in graph["links"])
    assert links == [
        ("depends", "D-2", "D-1"),
        ("for", "T-1", "D-1"),
        ("source", "D-2", "R-1"),
    ]
    assert "N-1" not in [node["id"] for node in graph["nodes"]]
