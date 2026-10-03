"""項目の検索・1 件の表示と参照元・属性名の一覧（読むだけで、ファイルを書かない）。"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from kinds import KINDS, Kind, id_number
from store import Workspace, as_ids, find_item, read_body

# 参照元として拾うキーとその並び
REFERENCE_KEYS = ("depends_on", "parent", "for", "related", "sources")


@dataclass(frozen=True, slots=True, kw_only=True)
class SearchFilter:
    """`find` の引数をまとめた条件。None の条件は絞らない。"""

    # 文字の欄に含まれる文字
    text: str | None = None
    kind: Kind | None = None
    status: str | None = None
    tag: str | None = None
    target: str | None = None
    category: str | None = None
    phase: str | None = None
    # 属性名と値（値が None ならその属性を持つことだけ）
    attrs: list[tuple[str, str | None]] = field(default_factory=list)


def search_items(workspace: Workspace, search_filter: SearchFilter) -> list[dict[str, str | None]]:
    """条件の全てに合う項目を種類の順・連番の順に返す。"""
    needle = search_filter.text.lower() if search_filter.text is not None else None
    results: list[dict[str, str | None]] = []
    for kind, item in _iter_sorted_items(workspace):
        # 種類で絞る
        if search_filter.kind is not None and kind != search_filter.kind:
            continue
        if not _matches_fields(item, search_filter):
            continue
        # 文字で絞る（項目の全ての文字列の値が対象）
        if needle is not None and not _contains_text(item, needle):
            continue
        results.append(
            {
                "id": item.get("id"),
                "kind": kind,
                "title": item.get("title"),
                "status": item.get("status"),
            }
        )
    return results


def parse_attr(text: str) -> tuple[str, str | None]:
    """`--attr` の `名前=値`・`名前` を名前と値に分ける（`=` が無ければ値は None）。"""
    name, separator, value = text.partition("=")
    # `=` が無い: その属性を持つことだけを条件にする
    if not separator:
        return name, None
    return name, value


def show_item(workspace: Workspace, item_id: str) -> dict[str, Any]:
    """1 項目の全てのキー・種類・本文・参照元をまとめる。"""
    ref = find_item(workspace, item_id)
    body_name = ref.item.get("body")
    # body があるときだけ本文を読む
    body_markdown = read_body(workspace, body_name) if isinstance(body_name, str) else None
    return {
        "item": ref.item,
        "kind": ref.kind,
        "body_markdown": body_markdown,
        "referenced_by": list_referrers(workspace, item_id),
    }


def list_referrers(workspace: Workspace, item_id: str) -> list[dict[str, str]]:
    """その ID を `REFERENCE_KEYS` のどれかで指す項目を、キーごとに 1 行で返す。"""
    referrers: list[dict[str, str]] = []
    for _, item in _iter_sorted_items(workspace):
        for key in REFERENCE_KEYS:
            # 同じ項目が複数のキーで指すときは、キーごとに行を分ける
            if item_id in as_ids(item.get(key)):
                referrers.append({"id": item["id"], "key": key})
    return referrers


def list_attrs(workspace: Workspace) -> list[dict[str, Any]]:
    """全ての項目の `attrs` の名前ごとに、持つ項目の数と種類を数える。"""
    counts: dict[str, int] = {}
    kinds_by_name: dict[str, set[Kind]] = {}
    for kind, item in _iter_sorted_items(workspace):
        attrs = item.get("attrs")
        if not isinstance(attrs, dict):
            continue
        for name in attrs:
            counts[name] = counts.get(name, 0) + 1
            kinds_by_name.setdefault(name, set()).add(kind)
    return [
        {
            "name": name,
            "count": counts[name],
            # 種類の並びは KINDS の順
            "kinds": [kind for kind in KINDS if kind in kinds_by_name[name]],
        }
        for name in sorted(counts)
    ]


def _iter_sorted_items(workspace: Workspace) -> Iterator[tuple[Kind, dict[str, Any]]]:
    """種類の順・連番の小さい順に項目を返す。"""
    for kind in KINDS:
        yield from (
            (kind, item)
            for item in sorted(
                workspace.items[kind], key=lambda item: id_number(str(item.get("id", "")))
            )
        )


def _matches_fields(item: dict[str, Any], search_filter: SearchFilter) -> bool:
    """状態・対象・カテゴリー・フェーズ・タグ・属性の条件に合うか。"""
    for name in ("status", "target", "category", "phase"):
        wanted = getattr(search_filter, name)
        if wanted is not None and item.get(name) != wanted:
            return False
    # タグは `tags` に含むか
    if search_filter.tag is not None and search_filter.tag not in (item.get("tags") or []):
        return False
    attrs = item.get("attrs")
    item_attrs = attrs if isinstance(attrs, dict) else {}
    for name, value in search_filter.attrs:
        # 名前が無い属性は合わない
        if name not in item_attrs:
            return False
        # 値の指定があるときは文字列にして一致を見る
        if value is not None and str(item_attrs[name]) != value:
            return False
    return True


def _contains_text(value: Any, needle: str) -> bool:
    """値の中の文字列（配列・辞書の値をたどる）に文字が含まれるか。"""
    # 文字列: 小文字にして含むか
    if isinstance(value, str):
        return needle in value.lower()
    # 配列は要素を、辞書は値をたどる（辞書のキーは見ない）
    if isinstance(value, list):
        return any(_contains_text(element, needle) for element in value)
    if isinstance(value, dict):
        return any(_contains_text(element, needle) for element in value.values())
    return False
