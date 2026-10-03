"""ワークスペースの記録を 1 つの JSON にまとめ、プレビューの雛形に埋め込んで書き出す。"""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import Any

import store
from graph import is_settled, judge_goal, list_next_candidates
from kinds import KINDS
from store import Workspace

# このファイルから見た `skills/mindmap/preview/`
PREVIEW_DIR = Path(__file__).resolve().parent.parent / "preview"

# 雛形のフォルダの中の雛形の HTML
TEMPLATE_FILE = "template.html"

# 雛形がちょうど 1 つ持つ、中身が空の埋め込み先の要素
DATA_ELEMENT = '<script type="application/json" id="mindmap-data"></script>'

# ワークスペースに書き出すファイル名
PREVIEW_FILE = "preview.html"

# 差し込む CSS（雛形のフォルダからの相対パス。並びの順につなぐ）
STYLE_FILES = ("tokens.css", "style.css")

# 差し込む JavaScript（tsc が `.ts` から生成した `.js`。並びの順につなぎ、起動する `app.js` が最後）
SCRIPT_FILES = (
    "core/dom.js",
    "core/records.js",
    "core/libs.js",
    "core/router.js",
    "components/view-switch.js",
    "components/topbar.js",
    "components/table.js",
    "screens/overview.js",
    "screens/decisions.js",
    "screens/tasks.js",
    "screens/docs.js",
    "screens/records.js",
    "screens/detail.js",
    "screens/search.js",
    "screens/diagram-viewer.js",
    "graph/graph.js",
    "app.js",
)

# `template.html` がちょうど 1 つ持つ、CSS を入れる空の要素
STYLE_SLOT = '<style id="mindmap-style"></style>'

# `template.html` がちょうど 1 つ持つ、JavaScript を入れる空の要素（埋め込み先より後ろ）
SCRIPT_SLOT = '<script id="mindmap-app"></script>'

# 埋め込み先・差し込み口の要素を閉じるタグ
CLOSE_TAG = "</script>"
STYLE_CLOSE_TAG = "</style>"


def build_preview(workspace: Workspace, *, built_at: str, preview_dir: Path = PREVIEW_DIR) -> Path:
    """検証してからデータを雛形に埋め込み、`preview.html` を置き換える。"""
    # 問題があるときは書かない（前の preview.html を残す）
    problems = store.validate_workspace(workspace)
    if problems:
        raise store.build_mismatch_error(problems, workspace)

    data = collect_preview_data(workspace, built_at=built_at)
    html = embed_data(assemble_template(preview_dir=preview_dir), data)

    # 一時ファイルに書いて置き換える（途中で止まっても前の preview.html を壊さない）
    path = workspace.root / PREVIEW_FILE
    temp: Path | None = None
    try:
        temp = store.write_temp(path, html)
        os.replace(temp, path)
    except OSError as error:
        # 置き換えに失敗した: 残った一時ファイルを消す
        if temp is not None:
            temp.unlink(missing_ok=True)
        raise store.write_failed(path, error) from error
    return path


def collect_preview_data(workspace: Workspace, *, built_at: str) -> dict[str, Any]:
    """設定・7 種類・本文・画面に出す値・書き出した日時を 1 つの辞書にまとめる。"""
    data: dict[str, Any] = {"settings": workspace.settings}
    # 種類ごとの items を、ファイル名から `.yaml` を落としたキーで入れる
    for kind, spec in KINDS.items():
        data[spec.file.removesuffix(".yaml")] = workspace.items[kind]
    # 項目の body が指す本文だけを集める（読めないものは入れない）
    bodies: dict[str, str] = {}
    for kind in KINDS:
        for item in workspace.items[kind]:
            body = item.get("body")
            if not isinstance(body, str):
                continue
            text = store.read_body(workspace, body)
            if text is not None:
                bodies[body] = text
    data["bodies"] = bodies
    data["derived"] = derive_preview_values(workspace)
    data["built_at"] = built_at
    return data


def escape_for_script(json_text: str) -> str:
    """JSON の文字列の `<`・`>`・`&` を、JSON の Unicode エスケープに置き換える。"""
    # `&` を先に置き換える（後の置き換えが作る文字を巻き込まない）
    return json_text.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")


def embed_data(template: str, data: dict[str, Any]) -> str:
    """雛形の `DATA_ELEMENT` の中身にデータの JSON を入れた HTML を返す。"""
    count = template.count(DATA_ELEMENT)
    # 同梱の雛形の誤り: 埋め込み先が 1 つだけでない
    if count != 1:
        raise ValueError(f"雛形に埋め込み先が 1 つだけありません（{count} 個）")
    json_text = escape_for_script(json.dumps(data, ensure_ascii=False))
    opened = DATA_ELEMENT.removesuffix(CLOSE_TAG)
    return template.replace(DATA_ELEMENT, f"{opened}{json_text}{CLOSE_TAG}")


def assemble_template(*, preview_dir: Path = PREVIEW_DIR) -> str:
    """`template.html` に CSS・JavaScript を差し込んだ HTML を返す（`DATA_ELEMENT` は空のまま）。"""
    template = (preview_dir / TEMPLATE_FILE).read_text(encoding="utf-8")
    styles = [(name, (preview_dir / name).read_text(encoding="utf-8")) for name in STYLE_FILES]
    scripts = [(name, (preview_dir / name).read_text(encoding="utf-8")) for name in SCRIPT_FILES]
    # 同梱の雛形の誤り: 差し込む中身が、差し込み先の要素を閉じてしまう
    for files, close_tag in ((styles, STYLE_CLOSE_TAG), (scripts, CLOSE_TAG)):
        for name, text in files:
            if close_tag.removesuffix(">") in text.lower():
                raise ValueError(f"雛形の {name} が {close_tag.removesuffix('>')} を含みます")
    # 同梱の雛形の誤り: 差し込み口が 1 つだけでない
    for slot in (STYLE_SLOT, SCRIPT_SLOT):
        count = template.count(slot)
        if count != 1:
            raise ValueError(f"雛形に差し込み口 {slot} が 1 つだけありません（{count} 個）")
    css = "\n".join(text for _, text in styles)
    js = "\n".join(text for _, text in scripts)
    template = template.replace(STYLE_SLOT, f'<style id="mindmap-style">{css}{STYLE_CLOSE_TAG}')
    return template.replace(SCRIPT_SLOT, f'<script id="mindmap-app">{js}{CLOSE_TAG}')


def derive_preview_values(workspace: Workspace) -> dict[str, Any]:
    """概要と表に出す次の候補・ゴールまで・カテゴリー別の進み具合を、コマンドと同じ関数で計算する。"""
    next_candidates = [
        asdict(candidate) for candidate in list_next_candidates(workspace, limit=None)
    ]
    report = judge_goal(workspace)
    goal = asdict(report)
    # 判定に入れたフェーズごとの、決着した検討事項の数と全体の数
    goal["phase_progress"] = [_count_decisions(workspace, phase) for phase in report.phases]
    # カテゴリーごとに、フェーズの順のセルと合計を並べる
    progress = []
    for category in workspace.settings.get("categories", []):
        cells = [
            _count_decisions(workspace, phase, category=category["name"])
            for phase in workspace.settings.get("phases", [])
        ]
        progress.append(
            {
                "category": category["name"],
                "cells": cells,
                "settled": sum(cell["settled"] for cell in cells),
                "total": sum(cell["total"] for cell in cells),
            }
        )
    return {"next": next_candidates, "goal": goal, "progress": progress}


def _count_decisions(
    workspace: Workspace, phase: str, *, category: str | None = None
) -> dict[str, Any]:
    """フェーズ（と、あればカテゴリー）の検討事項のうち、決着した数と全体の数を返す。"""
    rows = [
        item
        for item in workspace.items["decision"]
        if item.get("phase") == phase and (category is None or item.get("category") == category)
    ]
    settled = sum(1 for item in rows if is_settled("decision", item))
    return {"phase": phase, "settled": settled, "total": len(rows)}
