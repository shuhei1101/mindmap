"""components/table.ts（表と、並べ替え・絞り込みの計算）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# 列の定義を作る JavaScript（値を取る get は関数なので、ページの中で作る）
COLUMNS_JS = """
    const makeColumns = (specs) => specs.map(({key, order}) => ({
        key,
        label: key,
        filterable: true,
        order,
        get: (row) => row[key],
    }));
"""

# 絞り込みの行
FILTER_ROWS = [
    {"id": "D-1", "status": "要見直し", "ready": "なし", "tags": ["a", "b"]},
    {"id": "D-2", "status": "保留", "ready": "なし", "tags": ["c"]},
    {"id": "D-3", "status": "未決定", "ready": "着手可能", "tags": ["a"]},
    {"id": "D-4", "status": "未決定", "ready": "前提待ち", "tags": []},
]


@pytest.mark.parametrize(
    ("filters", "expected_ids"),
    [
        pytest.param({"status": ["要見直し", "保留"]}, ["D-1", "D-2"], id="any_in_column"),
        pytest.param({"status": ["未決定"], "ready": ["着手可能"]}, ["D-3"], id="all_columns"),
        pytest.param({"tags": ["a"]}, ["D-1", "D-3"], id="array_value"),
        pytest.param({}, ["D-1", "D-2", "D-3", "D-4"], id="no_filter"),
    ],
)
def test_filter_rows(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    filters: dict[str, list[str]],
    expected_ids: list[str],
) -> None:
    """列の中はどれか、列の間は全て（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    ids = preview_page.evaluate(
        f"""({{rows, filters}}) => {{
            {COLUMNS_JS}
            const columns = makeColumns([{{key: "status"}}, {{key: "ready"}}, {{key: "tags"}}]);
            return MindmapPreview.filterRows({{rows, columns, filters}}).map((row) => row.id);
        }}""",
        {"rows": FILTER_ROWS, "filters": filters},
    )
    # 検証
    assert ids == expected_ids


@pytest.mark.parametrize(
    ("sort", "expected_ids"),
    [
        pytest.param({"key": "title", "dir": "asc"}, ["R-2", "R-3", "R-1"], id="title_asc"),
        pytest.param({"key": "status", "dir": "desc"}, ["R-3", "R-2", "R-1"], id="order_desc"),
        pytest.param(None, ["R-1", "R-2", "R-3"], id="none"),
    ],
)
def test_sort_rows(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    sort: dict[str, Any] | None,
    expected_ids: list[str],
) -> None:
    """昇順・降順・解除（正常系）。"""
    # 準備
    rows = [
        {"id": "R-1", "title": "うさぎ", "status": "未決定"},
        {"id": "R-2", "title": "あひる", "status": "決定済み"},
        {"id": "R-3", "title": "いぬ", "status": "保留"},
    ]
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        f"""({{rows, sort}}) => {{
            {COLUMNS_JS}
            const columns = makeColumns([
                {{key: "title"}},
                {{key: "status", order: ["未決定", "決定済み", "保留"]}},
            ]);
            const sorted = MindmapPreview.sortRows({{rows, columns, sort}});
            return {{sorted: sorted.map((row) => row.id), original: rows.map((row) => row.id)}};
        }}""",
        {"rows": rows, "sort": sort},
    )
    # 検証
    assert result["sorted"] == expected_ids
    # 渡した配列は変わらない
    assert result["original"] == ["R-1", "R-2", "R-3"]


def test_filter_counts(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """ほかの列の条件だけを当てて数える（正常系）。"""
    # 準備
    rows = [
        {"id": "D-1", "status": "未決定", "category": "A"},
        {"id": "D-2", "status": "決定済み", "category": "A"},
        {"id": "D-3", "status": "未決定", "category": "B"},
        {"id": "D-4", "status": "未決定", "category": "A"},
    ]
    filters = {"status": ["未決定"], "category": ["A"]}
    load_preview_scripts()
    # 実行
    counts = preview_page.evaluate(
        f"""({{rows, filters}}) => {{
            {COLUMNS_JS}
            const columns = makeColumns([
                {{key: "status", order: ["未決定", "決定済み"]}},
                {{key: "category"}},
            ]);
            return MindmapPreview.filterCounts({{rows, columns, filters, key: "status"}});
        }}""",
        {"rows": rows, "filters": filters},
    )
    # 検証
    assert counts == [{"value": "未決定", "count": 2}, {"value": "決定済み", "count": 1}]
