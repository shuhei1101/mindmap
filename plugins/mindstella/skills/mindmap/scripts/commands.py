"""コマンドごとの処理（標準入力の解釈 → 各機能 → 出力の辞書と終了コード）。"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

from builder import build_preview, export_preview, validate_export_out
from checker import check_workspace
from errors import ItemNotFoundError, OptionNotFoundError, SchemaMismatchError
from graph import judge_goal, list_next_candidates, summarize_status, trace_impact
from kinds import KINDS, Kind
from migration_ops import DESTRUCTIVE_OPS, describe_step
from migrator import MigrationReport, apply_migration, plan_migration, record_version, set_values
from query import SearchFilter, list_attrs, search_items, show_item
from store import (
    BodyWrite,
    Change,
    clear_release,
    create_workspace,
    find_item,
    is_legacy_problem,
    load_workspace,
    next_id,
    now_utc,
    save_change,
)
from versions import Version, read_plugin_version

# 前の版の形式の問題の詳細に続ける案内
MIGRATE_HINT = "（/mindstella:upgrade で今の形式に移せます）"

# 標準入力で渡させない、スクリプトが付けるキー
RESERVED_KEYS = ("id", "created", "updated", "body")

# 標準入力で本文の Markdown を渡すキー（YAML には残さない）
BODY_INPUT_KEY = "body_markdown"

# 標準入力のエラーの行に付けるファイル名の代わり
STDIN_NAME = "標準入力"

# コマンドの結果（出力の辞書と終了コード）
type Result = tuple[dict[str, Any], int]

# 今の日時を返す関数
type NowFn = Callable[[], str]


def read_json_object(text: str) -> dict[str, Any]:
    """標準入力を JSON のオブジェクトとして読む。"""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise SchemaMismatchError([f"{STDIN_NAME}: (全体): JSON として読めません"]) from error
    # オブジェクト以外（配列・数値など）は受け付けない
    if not isinstance(data, dict):
        raise SchemaMismatchError([f"{STDIN_NAME}: (全体): オブジェクトではありません"])
    return data


def validate_input_keys(kind: Kind, data: dict[str, Any]) -> None:
    """スクリプトが付けるキーと、本文を持てない種類への `body_markdown` を弾く。"""
    lines = [
        f"{STDIN_NAME}: {key}: スクリプトが付けるキーです" for key in RESERVED_KEYS if key in data
    ]
    # 本文を持てない種類に本文を渡した
    if BODY_INPUT_KEY in data and not KINDS[kind].has_body:
        lines.append(f"{STDIN_NAME}: {BODY_INPUT_KEY}: この種類は本文を持てません")
    if lines:
        raise SchemaMismatchError(lines)


def merge_changes(
    item: dict[str, Any], changes: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """渡したキーを値ごと置き換え、`None` のキーを消した新しい項目と、変わったキーを返す。"""
    merged = dict(item)
    changed: list[str] = []
    for key, value in changes.items():
        # 値が None: キーがあれば消す
        if value is None:
            if key in merged:
                del merged[key]
                changed.append(key)
        # 元の値と違う（新しいキーを含む）: 置き換える（新しいキーは末尾に足される）
        elif key not in merged or merged[key] != value:
            merged[key] = value
            changed.append(key)
    return merged, changed


def switch_adopted(item: dict[str, Any], key: str) -> tuple[dict[str, Any], str | None]:
    """指定した記号の案だけを採用にした新しい項目と、それまで採用していた案の記号を返す。"""
    options = [option for option in item.get("options") or [] if isinstance(option, dict)]
    keys = [str(option.get("key")) for option in options]
    # 検討事項がその記号の案を持たない
    if key not in keys:
        raise OptionNotFoundError(f"案がありません: {key}（持っている案: {', '.join(keys)}）")
    # それまで採用していた最初の案の記号を控える
    previous = next(
        (str(option["key"]) for option in options if option.get("adopted") is True), None
    )
    switched = [{**option, "adopted": str(option.get("key")) == key} for option in options]
    return {**item, "options": switched}, previous


def run_init(root: Path, stdin_text: str) -> Result:
    """標準入力の設定でワークスペースを作る。"""
    settings = read_json_object(stdin_text)
    files = create_workspace(root, settings, version=str(read_plugin_version()))
    return {"workspace": str(root.resolve()), "files": files}, 0


def run_clear_release(root: Path) -> Result:
    """`release/` の中身を消し、消したものを返す。"""
    return {"removed": clear_release(root)}, 0


def run_add(root: Path, kind: Kind, stdin_text: str, now: NowFn = now_utc) -> Result:
    """ID・日時・本文を付けて 1 項目を足す。"""
    workspace = load_workspace(root)
    data = read_json_object(stdin_text)
    validate_input_keys(kind, data)
    item_id = next_id(workspace, kind)
    timestamp = now()
    # id を先頭に、created・updated を末尾に置く
    item: dict[str, Any] = {"id": item_id}
    item.update({key: value for key, value in data.items() if key != BODY_INPUT_KEY})
    body = _body_write(item_id, data)
    # 本文を渡したときだけ、項目の body を `{ID}.md` にする
    if body is not None:
        item["body"] = body.name
    item["created"] = timestamp
    item["updated"] = timestamp
    save_change(workspace, Change(kind=kind, items=[*workspace.items[kind], item], body=body))
    return {
        "id": item_id,
        "file": KINDS[kind].file,
        "body": f"docs/{body.name}" if body is not None else None,
    }, 0


def run_update(root: Path, item_id: str, stdin_text: str, now: NowFn = now_utc) -> Result:
    """1 項目のキーを置き換え、更新日時を変える。"""
    workspace = load_workspace(root)
    ref = find_item(workspace, item_id)
    data = read_json_object(stdin_text)
    validate_input_keys(ref.kind, data)
    changes = {key: value for key, value in data.items() if key != BODY_INPUT_KEY}
    merged, changed = merge_changes(ref.item, changes)
    merged["updated"] = now()
    body = _body_write(item_id, data)
    # 本文を渡したときは body を `{ID}.md` にする（changed に入れるのは値が変わったときだけ）
    if body is not None and merged.get("body") != body.name:
        merged["body"] = body.name
        changed.append("body")
    items = list(workspace.items[ref.kind])
    items[ref.index] = merged
    save_change(workspace, Change(kind=ref.kind, items=items, body=body))
    return {"id": item_id, "file": KINDS[ref.kind].file, "changed": changed}, 0


def run_adopt(root: Path, item_id: str, key: str, now: NowFn = now_utc) -> Result:
    """検討事項の採用する案を切り替えて書き込む。"""
    workspace = load_workspace(root)
    ref = find_item(workspace, item_id)
    # 検討事項以外の項目は案を持たない
    if ref.kind != "decision":
        raise ItemNotFoundError(f"検討事項がありません: {item_id}")
    switched, previous = switch_adopted(ref.item, key)
    switched["updated"] = now()
    items = list(workspace.items["decision"])
    items[ref.index] = switched
    save_change(workspace, Change(kind="decision", items=items))
    return {"id": item_id, "adopted": key, "previous": previous}, 0


def run_check(root: Path) -> Result:
    """点検して、問題があれば終了コード 1 を返す。前の版の形式の問題には /mindstella:upgrade を案内する。"""
    workspace = load_workspace(root)
    problems = check_workspace(workspace)
    rows = []
    for problem in problems:
        row = asdict(problem)
        # 前の版の形式から来た問題: 詳細に移し替えのスキルでの移し方を続ける
        if is_legacy_problem(problem, workspace):
            row["detail"] += MIGRATE_HINT
        rows.append(row)
    return {"ok": not problems, "problems": rows}, 1 if problems else 0


def run_build(root: Path, now: NowFn = now_utc) -> Result:
    """プレビューを書き出してそのパスを返す。"""
    path = build_preview(load_workspace(root), built_at=now())
    return {"path": str(path)}, 0


def run_export(root: Path, out: Path, now: NowFn = now_utc) -> Result:
    """書き出す先を確かめて配る書き出しを書き、そのパスを返す。"""
    # ワークスペースを読む前に確かめる（誤った out では何も読まず、書かない）
    resolved = validate_export_out(out, root=root)
    path = export_preview(load_workspace(root), out=resolved, built_at=now())
    return {"path": str(path)}, 0


def run_impact(root: Path, item_id: str) -> Result:
    """影響を出力の形にする。"""
    affected = trace_impact(load_workspace(root), item_id)
    return {"id": item_id, "affected": [asdict(row) for row in affected]}, 0


def run_next(root: Path, limit: int | None) -> Result:
    """次の候補を出力の形にする。"""
    candidates = list_next_candidates(load_workspace(root), limit=limit)
    return {"candidates": [asdict(candidate) for candidate in candidates]}, 0


def run_status(root: Path) -> Result:
    """再開時の状況を出力の形にする。"""
    return asdict(summarize_status(load_workspace(root))), 0


def run_goal(root: Path) -> Result:
    """ゴールに届いたかの判定を出力の形にする。"""
    return asdict(judge_goal(load_workspace(root))), 0


def run_find(root: Path, search_filter: SearchFilter) -> Result:
    """引数から作った条件で探し、検索結果を出力の形にする。"""
    return {"items": search_items(load_workspace(root), search_filter)}, 0


def run_show(root: Path, item_id: str) -> Result:
    """1 項目の表示を出力の形にする。"""
    return show_item(load_workspace(root), item_id), 0


def run_attrs(root: Path) -> Result:
    """属性名の一覧を出力の形にする。"""
    return {"attrs": list_attrs(load_workspace(root))}, 0


def _body_write(item_id: str, data: dict[str, Any]) -> BodyWrite | None:
    """標準入力に `body_markdown` があれば、`docs/{ID}.md` に書く本文にする。"""
    text = data.get(BODY_INPUT_KEY)
    # 本文を渡していない
    if text is None:
        return None
    return BodyWrite(name=f"{item_id}.md", text=str(text))


def run_migrate(
    root: Path,
    *,
    plan: bool,
    record: bool,
    assignments: list[tuple[str, str, str]] | None,
    from_version: Version | None,
    to_version: Version | None,
) -> Result:
    """`--plan`・`--set`・`--record` で分けて移し替えの処理を呼び、結果を出力の形にする。"""
    versions = {"from_version": from_version, "to_version": to_version}
    if plan:
        report = plan_migration(root, **versions)
    elif assignments:
        # 値を入れてから並べ直す（手順は当てないので steps は空）
        set_values(root, assignments)
        report = replace(plan_migration(root, **versions), steps=[])
    elif record:
        # 版を書いてから並べ直す（手順は当てないので steps は空）
        recorded = record_version(root, to_version=to_version)
        report = replace(plan_migration(root, **versions), steps=[], recorded=recorded)
    else:
        report = apply_migration(root, **versions)
    return _migration_payload(report), 0


def _migration_payload(report: MigrationReport) -> dict[str, Any]:
    """移し替えの結果を、出力の辞書にする（版は文字列、手順は 1 行の説明つき）。"""
    return {
        "workspace_version": _version_text(report.workspace_version),
        "plugin_version": str(report.plugin_version),
        "relation": report.relation,
        "steps": [
            {
                "version": str(step.version),
                "index": step.index,
                "op": step.op,
                "destructive": step.op in DESTRUCTIVE_OPS,
                "summary": describe_step(step),
            }
            for step in report.steps
        ],
        "needs_values": [asdict(value) for value in report.needs_values],
        "backup": asdict(report.backup) if report.backup is not None else None,
        "recorded": _version_text(report.recorded),
    }


def _version_text(version: Version | None) -> str | None:
    """版を文字列にする。None（版を記録する前の形式・書いていない）はそのまま None。"""
    return str(version) if version is not None else None
