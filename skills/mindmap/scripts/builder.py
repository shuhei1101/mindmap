"""ワークスペースの記録を 1 つの JSON にまとめ、プレビューの雛形に埋め込んで書き出す。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import store
from kinds import KINDS
from store import Workspace

# このファイルから見た `skills/mindmap/preview/template.html`
TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "preview" / "template.html"

# 雛形がちょうど 1 つ持つ、中身が空の要素
DATA_ELEMENT = '<script type="application/json" id="mindmap-data"></script>'

# ワークスペースに書き出すファイル名
PREVIEW_FILE = "preview.html"

# 埋め込み先の要素を閉じるタグ
CLOSE_TAG = "</script>"


def build_preview(
    workspace: Workspace, *, built_at: str, template_path: Path = TEMPLATE_PATH
) -> Path:
    """検証してからデータを雛形に埋め込み、`preview.html` を置き換える。"""
    # 問題があるときは書かない（前の preview.html を残す）
    problems = store.validate_workspace(workspace)
    if problems:
        raise store.build_mismatch_error(problems)

    data = collect_preview_data(workspace, built_at=built_at)
    html = embed_data(template_path.read_text(encoding="utf-8"), data)

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
    """設定・7 種類・本文・書き出した日時を 1 つの辞書にまとめる。"""
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
