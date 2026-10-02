"""query.py（検索・1 件の表示と参照元・属性名の一覧）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest

import query
import store
from fixture_types import MakeItem, MakeWorkspace


def _ids(rows: list[dict[str, Any]]) -> list[str]:
    """検索結果の行から ID だけを並びのまま取り出す。"""
    return [row["id"] for row in rows]


@pytest.fixture
def schema_workspace(make_workspace: MakeWorkspace, make_item: MakeItem) -> store.Workspace:
    """文字と属性で探すためのワークスペース（D-1・D-2・T-1）を読み込んで返す。"""
    root = make_workspace(
        make_item("D-1", title="スキーマの設計", attrs={"担当": "自分"}),
        make_item(
            "D-2",
            title="別の問い",
            options=[{"key": "A", "content": "スキーマを分ける"}],
        ),
        make_item("T-1", title="作業", attrs={"担当": "自分"}),
    )
    return store.load_workspace(root)


@pytest.fixture
def field_workspace(make_workspace: MakeWorkspace, make_item: MakeItem) -> store.Workspace:
    """種類・状態・タグ・対象・カテゴリー・フェーズで絞るためのワークスペースを読み込んで返す。"""
    root = make_workspace(
        make_item(
            "D-1",
            status="未決定",
            tags=["データ"],
            target="mindmap",
            category="データ構造",
            phase="要件",
        ),
        make_item(
            "D-2",
            status="決定済み",
            target="別の対象",
            category="別のカテゴリー",
            phase="目的",
        ),
        make_item(
            "T-1",
            status="未着手",
            tags=["データ"],
            target="mindmap",
            category="データ構造",
            phase="要件",
        ),
    )
    return store.load_workspace(root)


def test_search_items_when_text_and_attr(schema_workspace: store.Workspace) -> None:
    """文字と属性の両方に合う項目だけを返す（正常系）。"""
    # 準備
    search_filter = query.SearchFilter(text="スキーマ", attrs=[("担当", "自分")])
    # 実行
    result = query.search_items(schema_workspace, search_filter)
    # 検証
    assert result == [
        {
            "id": "D-1",
            "kind": "decision",
            "title": "スキーマの設計",
            "status": "未決定",
        },
    ]


def test_search_items_when_nested_text(schema_workspace: store.Workspace) -> None:
    """入れ子の文字列にも当たる（正常系）。"""
    # 準備
    search_filter = query.SearchFilter(text="スキーマ")
    # 実行
    result = query.search_items(schema_workspace, search_filter)
    # 検証
    assert _ids(result) == ["D-1", "D-2"]


@pytest.mark.parametrize(
    ("conditions", "expected_ids"),
    [
        pytest.param({"kind": "task"}, ["T-1"], id="kind"),
        pytest.param({"status": "未決定"}, ["D-1"], id="status"),
        pytest.param({"tag": "データ"}, ["D-1", "T-1"], id="tag"),
        pytest.param({"target": "別の対象"}, ["D-2"], id="target"),
        pytest.param({"category": "別のカテゴリー"}, ["D-2"], id="category"),
        pytest.param({"phase": "目的"}, ["D-2"], id="phase"),
    ],
)
def test_search_items_when_fields(
    field_workspace: store.Workspace,
    conditions: dict[str, str],
    expected_ids: list[str],
) -> None:
    """種類・状態・タグ・対象・カテゴリー・フェーズで絞る（正常系）。"""
    # 準備
    search_filter = query.SearchFilter(**conditions)
    # 実行
    result = query.search_items(field_workspace, search_filter)
    # 検証
    assert _ids(result) == expected_ids


def test_search_items_when_no_filter(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """条件が無ければ全てを種類の順に返す（正常系）。"""
    # 準備
    root = make_workspace(make_item("T-1"), make_item("D-2"), make_item("D-1"))
    workspace = store.load_workspace(root)
    # 実行
    result = query.search_items(workspace, query.SearchFilter())
    # 検証
    assert _ids(result) == ["D-1", "D-2", "T-1"]


@pytest.mark.parametrize(
    ("value", "needle", "expected"),
    [
        pytest.param({"a": ["Schema"]}, "schema", True, id="nested_value"),
        pytest.param({"schema": 1}, "schema", False, id="dict_key"),
        pytest.param(3, "3", False, id="number"),
    ],
)
def test_contains_text(value: Any, needle: str, expected: bool) -> None:
    """入れ子の値をたどり、キーと数値は見ない（正常系）。"""
    # 実行
    found = query._contains_text(value, needle)
    # 検証
    assert found is expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("担当=自分", ("担当", "自分"), id="name_and_value"),
        pytest.param("担当", ("担当", None), id="name_only"),
        pytest.param("式=a=b", ("式", "a=b"), id="value_with_equal"),
    ],
)
def test_parse_attr(text: str, expected: tuple[str, str | None]) -> None:
    """名前と値に分ける（正常系）。"""
    # 実行
    parsed = query.parse_attr(text)
    # 検証
    assert parsed == expected


def test_show_item(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """中身・本文・参照元をまとめる（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", body="D-1.md"),
        make_item("D-2", depends_on=["D-1"], related=["D-1"]),
        make_item("T-1", **{"for": ["D-1"]}),
        bodies={"D-1.md": "本文\n"},
    )
    workspace = store.load_workspace(root)
    # 実行
    shown = query.show_item(workspace, "D-1")
    # 検証
    assert shown["item"] == make_item("D-1", body="D-1.md")
    assert shown["kind"] == "decision"
    assert shown["body_markdown"] == "本文\n"
    assert shown["referenced_by"] == [
        {"id": "D-2", "key": "depends_on"},
        {"id": "D-2", "key": "related"},
        {"id": "T-1", "key": "for"},
    ]


def test_show_item_when_body_missing(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """本文を持たない項目は body_markdown が None になる（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace(make_item("D-1")))
    # 実行
    shown = query.show_item(workspace, "D-1")
    # 検証
    assert shown["body_markdown"] is None


def test_list_referrers(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """parent・sources を含む全ての参照のキーを拾い、キーごとに行を分ける（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("L-1"),
        make_item("D-1", sources=["L-1"]),
        make_item("D-2", related=["L-1"]),
        make_item("D-3", parent="D-1"),
    )
    workspace = store.load_workspace(root)
    # 実行
    to_log = query.list_referrers(workspace, "L-1")
    to_decision = query.list_referrers(workspace, "D-1")
    # 検証
    assert to_log == [{"id": "D-1", "key": "sources"}, {"id": "D-2", "key": "related"}]
    assert to_decision == [{"id": "D-3", "key": "parent"}]


def test_list_attrs(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """種類をまたいで数える（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", attrs={"担当": "自分"}),
        make_item("D-2", attrs={"担当": "自分"}),
        make_item("T-1", attrs={"期限": "来週", "担当": "自分"}),
    )
    workspace = store.load_workspace(root)
    # 実行
    attrs = query.list_attrs(workspace)
    # 検証
    assert attrs == [
        {"name": "担当", "count": 3, "kinds": ["decision", "task"]},
        {"name": "期限", "count": 1, "kinds": ["task"]},
    ]


def test_list_attrs_when_none(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """属性が無ければ空の並びを返す（正常系）。"""
    # 準備
    workspace = store.load_workspace(make_workspace(make_item("D-1")))
    # 実行
    attrs = query.list_attrs(workspace)
    # 検証
    assert attrs == []
