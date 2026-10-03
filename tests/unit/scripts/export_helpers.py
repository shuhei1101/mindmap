"""配る書き出しの単体テストが共有する、外の読み込みを持つ雛形・取る中身・ライブラリの組み立て。"""

from __future__ import annotations

import base64
import hashlib
from collections.abc import Callable
from pathlib import Path
from typing import Any

import builder

# 外の読み込みの版（雛形の <script src> と、取るライセンスの本文の URL に入る）
EXTERNAL_VERSION = "1.0.0"

# 外の読み込み 1 つ（パッケージ名・配布ファイルの中身）
type Script = tuple[str, bytes]

# URL を受けて本文を返す関数と、呼ばれた URL の記録
type FetchSpy = tuple[Callable[[str], bytes], list[str]]


def package_url(package: str, path: str) -> str:
    """jsDelivr の、版を固定したパッケージの中のファイルの URL を返す。"""
    return f"https://cdn.jsdelivr.net/npm/{package}@{EXTERNAL_VERSION}/{path}"


def dist_url(package: str) -> str:
    """パッケージの配布ファイルの URL を返す。"""
    return package_url(package, f"{package}.js")


def license_url(package: str) -> str:
    """パッケージのライセンスの本文の URL を返す。"""
    return package_url(package, "LICENSE")


def integrity_of(content: bytes) -> str:
    """配布ファイルの中身の sha384 を `sha384-{Base64}` の形にして返す。"""
    digest = base64.b64encode(hashlib.sha384(content).digest()).decode("ascii")
    return f"sha384-{digest}"


def external_template(scripts: list[Script]) -> str:
    """外の読み込みの印の間に、パッケージごとの `<script src integrity>` を置いた雛形を返す。"""
    tags = "".join(
        f'<script src="{dist_url(package)}" integrity="{integrity_of(content)}"'
        ' crossorigin="anonymous" defer></script>'
        for package, content in scripts
    )
    return (
        f"{builder.STYLE_SLOT}{builder.EXTERNAL_START}{tags}{builder.EXTERNAL_END}"
        f"{builder.DATA_ELEMENT}{builder.SCRIPT_SLOT}"
    )


def make_responses(
    scripts: list[Script], license_texts: dict[str, str] | None = None
) -> dict[str, bytes]:
    """URL → 取れる中身（配布ファイルと、既定は `本文 {パッケージ}` のライセンスの本文）を返す。"""
    responses: dict[str, bytes] = {}
    for package, content in scripts:
        responses[dist_url(package)] = content
        text = (license_texts or {}).get(package, f"本文 {package}")
        responses[license_url(package)] = text.encode("utf-8")
    return responses


def make_fetch(responses: dict[str, bytes]) -> FetchSpy:
    """URL ごとに決めた中身を返し、呼ばれた URL を記録する関数と、その記録を返す。"""
    calls: list[str] = []

    def _fetch(url: str) -> bytes:
        """呼ばれた URL を記録して、決めた中身を返す。"""
        calls.append(url)
        return responses[url]

    return _fetch, calls


def make_library(package: str, **overrides: Any) -> builder.VendorLibrary:
    """ライセンスの表示に使うライブラリを作る。入手先は https:// を持たない値にする。"""
    values: dict[str, Any] = {
        "package": package,
        "name": package.upper(),
        "notice": f"(c) {package}",
        "license": "MIT",
        "license_path": "LICENSE",
        "bundled_license_file": None,
        "repository": f"example.invalid/{package}",
        "tag": "{version}",
    }
    values.update(overrides)
    return builder.VendorLibrary(**values)


def write_preview_dir(folder: Path, template: str) -> None:
    """雛形のフォルダに template.html と、STYLE_FILES・SCRIPT_FILES の名前のファイルを書く。"""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "template.html").write_text(template, encoding="utf-8")
    for name in (*builder.STYLE_FILES, *builder.SCRIPT_FILES):
        path = folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"/* {name} */", encoding="utf-8")
