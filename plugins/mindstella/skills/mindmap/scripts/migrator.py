"""前の版の形式のワークスペース（資料の `done`・題名の無い設定）を今の形式に書き換える。"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import store
from errors import SummaryRequiredError
from kinds import KINDS, SETTINGS_FILE

# 資料の `done` の値 → `status`
DONE_TO_STATUS = {True: "完成", False: "下書き"}

# 書き換える資料のファイル名
DOCS_FILE = KINDS["doc"].file


@dataclass(frozen=True, slots=True, kw_only=True)
class MigrationEntry:
    """書き換えた 1 件（`migrate` の出力の `migrated[]` と同じキー）。"""

    # 書き換えた項目の ID。`mindmap.yaml` は None
    id: str | None
    # ワークスペースからの相対パス
    file: str
    # 書き換えの中身
    change: str


def migrate_settings(
    settings: dict[str, Any], *, summary: str | None
) -> tuple[dict[str, Any], MigrationEntry | None]:
    """題名を持たない設定に題名を足した設定を返す（持つ設定はそのまま返す）。"""
    # 題名を持つ: 何も移さない（summary 引数は使わない）
    if "summary" in settings:
        return settings, None
    text = (summary or "").strip()
    # 題名が無く、引数も空
    if not text:
        raise SummaryRequiredError(
            "ワークスペースに題名がありません。--summary で題名を渡してください"
        )
    migrated = {"summary": text, **settings}
    return migrated, MigrationEntry(id=None, file=SETTINGS_FILE, change="summary を足した")


def migrate_docs_items(
    items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[MigrationEntry]]:
    """資料の `done` を `status` に置き換えた並びと、移した項目を返す。"""
    migrated: list[dict[str, Any]] = []
    entries: list[MigrationEntry] = []
    for item in items:
        done = item.get("done")
        # 移さない: done が無い・status を既に持つ・done が真偽値でない（検証が止める）
        if "done" not in item or "status" in item or not isinstance(done, bool):
            migrated.append(item)
            continue
        status = DONE_TO_STATUS[done]
        # done の位置に status を置く（ほかのキーの並びと更新日時は変えない）
        migrated.append(
            {
                ("status" if key == "done" else key): status if key == "done" else value
                for key, value in item.items()
            }
        )
        entries.append(
            MigrationEntry(
                id=item.get("id"),
                file=DOCS_FILE,
                change=f"done: {'true' if done else 'false'} → status: {status}",
            )
        )
    return migrated, entries


def migrate_workspace(root: Path, *, summary: str | None) -> list[MigrationEntry]:
    """設定と資料を移し、検証してから 2 ファイルを置き換える。移すものが無ければ書かない。"""
    workspace = store.load_workspace(root)
    settings, settings_entry = migrate_settings(workspace.settings, summary=summary)
    docs_items, doc_entries = migrate_docs_items(workspace.items["doc"])
    entries = ([settings_entry] if settings_entry else []) + doc_entries
    # 移すものが無い: 何も書かない
    if not entries:
        return []

    # 移した後の値に差し替えたワークスペースを検証する（合わなければ何も書かない）
    raw = dict(workspace.raw)
    raw[SETTINGS_FILE] = settings
    raw[DOCS_FILE] = {**_as_mapping(workspace.raw.get(DOCS_FILE)), "items": docs_items}
    migrated = replace(
        workspace, raw=raw, settings=settings, items={**workspace.items, "doc": docs_items}
    )
    problems = store.validate_workspace(migrated)
    if problems:
        raise store.build_mismatch_error(problems)

    # 書き換えるファイル（docs.yaml → mindmap.yaml の順）
    targets: list[tuple[str, Any]] = []
    if doc_entries:
        targets.append((DOCS_FILE, raw[DOCS_FILE]))
    if settings_entry:
        targets.append((SETTINGS_FILE, settings))

    # 一時ファイルを先に全て書く
    temps: dict[str, Path] = {}
    try:
        for name, value in targets:
            temps[name] = store.write_temp(root / name, store.dump_yaml(value))
    except OSError as error:
        _remove(temps)
        raise store.write_failed(root / name, error) from error

    # docs.yaml を置き換える前に前の中身を控え、順に置き換える
    previous_docs = (root / DOCS_FILE).read_bytes() if DOCS_FILE in temps else None
    replaced: list[str] = []
    for name, _ in targets:
        try:
            os.replace(temps[name], root / name)
        except OSError as error:
            # 置き換えに失敗した: 先に置き換えた docs.yaml を控えに戻し、残った一時ファイルを消す
            if previous_docs is not None and DOCS_FILE in replaced:
                (root / DOCS_FILE).write_bytes(previous_docs)
            _remove(temps)
            raise store.write_failed(root / name, error) from error
        replaced.append(name)
    return entries


def _as_mapping(value: Any) -> dict[str, Any]:
    """辞書ならそのまま、そうでなければ空の辞書を返す。"""
    return value if isinstance(value, dict) else {}


def _remove(temps: dict[str, Path]) -> None:
    """残った一時ファイルを消す。"""
    for path in temps.values():
        path.unlink(missing_ok=True)
