"""ワークスペースの記録を 1 つの JSON にまとめ、プレビューの雛形に埋め込んで書き出す。"""

from __future__ import annotations

import base64
import hashlib
import http.client
import json
import os
import re
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from http import HTTPStatus
from pathlib import Path
from typing import Any

import store
from errors import DownloadFailedError, OutPathError
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

# jsDelivr への 1 回の要求で、接続と 1 回の読み取りをそれぞれ待つ秒数
FETCH_TIMEOUT_SEC = 30

# jsDelivr の、版を固定したパッケージの中のファイルの URL の形（ライセンスの本文を取るのに使う）
CDN_PACKAGE_URL = "https://cdn.jsdelivr.net/npm/{package}@{version}/{path}"

# `template.html` がちょうど 1 つ持つ、外の読み込み（描画のライブラリ・文字）の前後に置くコメント
EXTERNAL_START = "<!-- mindmap-external:start -->"
EXTERNAL_END = "<!-- mindmap-external:end -->"

# 配る書き出しに置く、ライセンスの表示を中身に持つ要素の開きタグ（画面には出ない）
LICENSES_OPEN = '<script type="text/plain" id="mindmap-licenses">'

# 雛形の外の読み込みの `src`（jsDelivr の版を固定した URL）を、パッケージ名・版・ファイルに分ける
_EXTERNAL_SRC = re.compile(
    r"^https://cdn\.jsdelivr\.net/npm/(?P<package>(?:@[^/@]+/)?[^/@]+)@(?P<version>[^/]+)/.+$"
)

# 差し込む中身が、script 要素を閉じる・開くタグを含むかを見る文字列（小文字で比べる）
_SCRIPT_TAGS = ("</script", "<script")


@dataclass(frozen=True, slots=True, kw_only=True)
class VendorLibrary:
    """雛形の描画のライブラリ 1 つの、ライセンスの表示に使う値。"""

    # npm のパッケージ名（雛形の `<script src>` の URL のパッケージ名と結ぶ）
    package: str
    # 表示する名前
    name: str
    # 著作権の表示
    notice: str
    # 配るときのライセンスの名前（選べるライセンスを持つときは選んだもの）
    license: str
    # パッケージの中のライセンスの本文のファイル
    license_path: str
    # 配布ファイルが中に束ねた依存のライセンスを並べたファイル（雛形のフォルダからの相対パス）。無ければ None
    bundled_license_file: str | None
    # ソースコードのリポジトリの URL
    repository: str
    # 版のタグの形（`{version}` に外の読み込みの版を入れる）
    tag: str


@dataclass(frozen=True, slots=True, kw_only=True)
class ExternalScript:
    """雛形の外の読み込みの `<script src integrity>` 1 つ。"""

    url: str
    # `sha384-{Base64}`
    integrity: str
    package: str
    version: str


@dataclass(frozen=True, slots=True, kw_only=True)
class LicenseBlock:
    """ライブラリ 1 つのライセンスの表示を組み立てる材料。"""

    library: VendorLibrary
    # 外の読み込みの版
    version: str
    # 取ったライセンスの本文
    license_text: str
    # 束ねた依存のライセンス。無ければ None
    bundled_text: str | None


# 配る書き出しに入れるライブラリ（`package` で雛形の外の読み込みと結ぶ。版・URL・integrity は雛形が持つ）
VENDOR_LIBRARIES = (
    VendorLibrary(
        package="marked",
        name="marked",
        notice="Copyright (c) 2018+, MarkedJS / Copyright (c) 2011-2018, Christopher Jeffrey",
        license="MIT",
        license_path="LICENSE",
        bundled_license_file=None,
        repository="https://github.com/markedjs/marked",
        tag="v{version}",
    ),
    VendorLibrary(
        package="dompurify",
        name="DOMPurify",
        notice="(c) Cure53 and other contributors",
        license="Apache-2.0",
        license_path="LICENSE",
        bundled_license_file=None,
        repository="https://github.com/cure53/DOMPurify",
        tag="{version}",
    ),
    VendorLibrary(
        package="elkjs",
        name="elkjs",
        notice="(c) Kiel University and others",
        license="EPL-2.0",
        license_path="LICENSE.md",
        bundled_license_file=None,
        repository="https://github.com/kieler/elkjs",
        tag="{version}",
    ),
    VendorLibrary(
        package="mermaid",
        name="mermaid",
        notice="Copyright (c) 2014 - 2022 Knut Sveidqvist",
        license="MIT",
        license_path="LICENSE",
        bundled_license_file="licenses/mermaid-bundled.txt",
        repository="https://github.com/mermaid-js/mermaid",
        tag="mermaid@{version}",
    ),
)

# URL を受けて本文のバイト列を返す関数（取れなければ DownloadFailedError を送る）
type FetchFn = Callable[[str], bytes]


def build_preview(workspace: Workspace, *, built_at: str, preview_dir: Path = PREVIEW_DIR) -> Path:
    """検証してからデータを雛形に埋め込み、`preview.html` を置き換える。"""
    # 問題があるときは書かない（前の preview.html を残す）
    problems = store.validate_workspace(workspace)
    if problems:
        raise store.build_mismatch_error(problems, workspace)

    data = collect_preview_data(workspace, built_at=built_at)
    html = embed_data(assemble_template(preview_dir=preview_dir), data)

    path = workspace.root / PREVIEW_FILE
    replace_file(path, html)
    return path


def replace_file(path: Path, text: str) -> None:
    """同じフォルダの一時ファイルに書いてから `os.replace` で置き換える（途中で止まっても前のファイルを壊さない）。"""
    temp: Path | None = None
    try:
        temp = store.write_temp(path, text)
        os.replace(temp, path)
    except OSError as error:
        # 書き込みか置き換えに失敗した（親のフォルダが無いときも）: 残った一時ファイルを消す
        if temp is not None:
            temp.unlink(missing_ok=True)
        raise store.write_failed(path, error) from error


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


def validate_export_out(out: Path, *, root: Path) -> Path:
    """`--out` が `.html` で終わり、ワークスペースの `preview.html` を指さないことを確かめ、絶対パスにして返す。"""
    # 拡張子は大文字・小文字を区別しない
    if out.suffix.lower() != ".html":
        raise OutPathError(f"--out は .html のファイルを指してください: {out}")
    resolved = out.resolve()
    # `build` が書き出す preview.html を指すと、配る書き出しで置き換えてしまう
    if resolved == (root / PREVIEW_FILE).resolve():
        raise OutPathError(f"--out にワークスペースの {PREVIEW_FILE} は指せません: {out}")
    return resolved


def fetch_url(url: str, timeout: float = FETCH_TIMEOUT_SEC) -> bytes:
    """URL を GET して本文のバイト列を返す（取り直さない）。"""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            status = response.status
            body = response.read()
    except (OSError, http.client.HTTPException) as error:
        # 届かない・待ちの上限を超えた・200 以外が返った（HTTPError も OSError）
        reason = getattr(error, "reason", None) or error
        raise DownloadFailedError(f"取れませんでした: {url}（{reason}）") from error
    # 200 以外の成功（204 など）も、配布ファイルとして使えない
    if status != HTTPStatus.OK:
        raise DownloadFailedError(f"取れませんでした: {url}（HTTP {status}）")
    return body


class _ExternalScriptParser(HTMLParser):
    """外の読み込みの範囲の `<script src integrity>` を、並びの順に集める。"""

    def __init__(self) -> None:
        """集めた `src` と `integrity` の並びを空で持つ。"""
        super().__init__()
        # (src, integrity) の並び
        self.found: list[tuple[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """src を持つ script の開きタグの src と integrity を控える。"""
        if tag != "script":
            return
        values = dict(attrs)
        # src を持たない script（中身を持つもの）は外の読み込みではない
        if values.get("src") is not None:
            self.found.append((values["src"] or "", values.get("integrity")))


def list_external_scripts(template: str) -> list[ExternalScript]:
    """雛形の外の読み込みの印の間の `<script src integrity>` を、並びの順に返す。"""
    start = template.find(EXTERNAL_START)
    end = template.find(EXTERNAL_END)
    # 同梱の雛形の誤り: 印が 1 つずつでないか、順が逆
    if template.count(EXTERNAL_START) != 1 or template.count(EXTERNAL_END) != 1 or start > end:
        raise ValueError("雛形に外の読み込みの印が 1 つずつありません")
    parser = _ExternalScriptParser()
    parser.feed(template[start:end])
    parser.close()
    scripts: list[ExternalScript] = []
    for src, integrity in parser.found:
        matched = _EXTERNAL_SRC.match(src)
        # 同梱の雛形の誤り: integrity が無いか、版を固定した jsDelivr の URL でない
        if integrity is None or matched is None:
            raise ValueError(
                f"雛形の外の読み込みが版を固定した jsDelivr の URL と integrity を持ちません: {src}"
            )
        scripts.append(
            ExternalScript(
                url=src,
                integrity=integrity,
                package=matched["package"],
                version=matched["version"],
            )
        )
    return scripts


def assemble_standalone_template(
    *,
    preview_dir: Path = PREVIEW_DIR,
    libraries: tuple[VendorLibrary, ...] = VENDOR_LIBRARIES,
    fetch: FetchFn = fetch_url,
) -> str:
    """`assemble_template` の外の読み込みを、取った描画のライブラリの `<script>` とライセンスの表示に置き換える。"""
    template = assemble_template(preview_dir=preview_dir)
    scripts = list_external_scripts(template)
    # 取る前に、外の読み込みごとのライセンスの表示の材料（VendorLibrary）を引く
    by_package = {library.package: library for library in libraries}
    for script in scripts:
        if script.package not in by_package:
            raise ValueError(f"ライセンスの表示が無い外の読み込み: {script.package}")

    script_elements: list[str] = []
    blocks: list[LicenseBlock] = []
    for script in scripts:
        library = by_package[script.package]
        dist = fetch(script.url)
        # 配布ファイルは雛形の integrity（sha384）と同じ中身であること
        digest = base64.b64encode(hashlib.sha384(dist).digest()).decode("ascii")
        if f"sha384-{digest}" != script.integrity:
            raise DownloadFailedError(f"integrity が合いません: {script.url}")
        license_url = CDN_PACKAGE_URL.format(
            package=script.package, version=script.version, path=library.license_path
        )
        license_text = fetch(license_url).decode("utf-8")
        bundled_text = (
            (preview_dir / library.bundled_license_file).read_text(encoding="utf-8")
            if library.bundled_license_file is not None
            else None
        )
        dist_text = dist.decode("utf-8")
        # 取った中身が script 要素を閉じる・開くタグを含むと、埋め込んだ要素が壊れる
        for source, text in (
            (script.url, dist_text),
            (license_url, license_text),
            (library.bundled_license_file, bundled_text),
        ):
            _reject_script_tags(source, text)
        script_elements.append(f"<script>{dist_text}{CLOSE_TAG}")
        blocks.append(
            LicenseBlock(
                library=library,
                version=script.version,
                license_text=license_text,
                bundled_text=bundled_text,
            )
        )

    # 印から印まで（両方を含む）を、取った配布ファイルとライセンスの表示に置き換える
    start = template.index(EXTERNAL_START)
    end = template.index(EXTERNAL_END) + len(EXTERNAL_END)
    licenses = f"{LICENSES_OPEN}{format_licenses(blocks)}{CLOSE_TAG}"
    return template[:start] + "".join(script_elements) + licenses + template[end:]


def _reject_script_tags(source: str | None, text: str | None) -> None:
    """text が `</script`・`<script` を含むときは ValueError にする（大文字・小文字を区別しない）。"""
    if text is None:
        return
    lowered = text.lower()
    for tag in _SCRIPT_TAGS:
        if tag in lowered:
            raise ValueError(f"取った {source} が {tag} を含みます")


def format_licenses(blocks: list[LicenseBlock]) -> str:
    """ライブラリごとの名前・版・著作権・ライセンス・入手先・本文・束ねた依存のライセンスを並べた文字列を返す。"""
    texts: list[str] = []
    for block in blocks:
        library = block.library
        tag = library.tag.replace("{version}", block.version)
        lines = [
            f"{library.name} {block.version}",
            library.notice,
            f"License: {library.license}",
            f"Source: {library.repository}/tree/{tag}",
            "",
            block.license_text.rstrip("\n"),
        ]
        # 束ねた依存のライセンスを持つライブラリは、本文の後に見出しと一緒に続ける
        if block.bundled_text is not None:
            lines += [
                "",
                f"{library.name} が中に持つライブラリ",
                "",
                block.bundled_text.rstrip("\n"),
            ]
        texts.append("\n".join(lines))
    return "\n\n".join(texts)


def export_preview(
    workspace: Workspace,
    *,
    out: Path,
    built_at: str,
    preview_dir: Path = PREVIEW_DIR,
    fetch: FetchFn = fetch_url,
) -> Path:
    """検証してから、描画のライブラリとライセンスの表示を中に持つ雛形にデータを埋め込み、`out` を置き換える。"""
    # 問題があるときは取らず、書かない（前の out を残す）
    problems = store.validate_workspace(workspace)
    if problems:
        raise store.build_mismatch_error(problems, workspace)

    # 取れないときは DownloadFailedError がそのまま上がる（書かない）
    template = assemble_standalone_template(preview_dir=preview_dir, fetch=fetch)
    data = collect_preview_data(workspace, built_at=built_at)
    replace_file(out, embed_data(template, data))
    return out
