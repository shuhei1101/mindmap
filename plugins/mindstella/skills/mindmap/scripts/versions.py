"""版（`v{メジャー}.{マイナー}.{パッチ}`）の解釈・比較・読み書き。"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from errors import SchemaMismatchError
from store import VERSION_FILE, write_failed, write_temp

# プラグインの版を持つファイル（このファイルから見た `plugins/mindstella/version.ini`）
PLUGIN_VERSION_FILE = Path(__file__).resolve().parents[3] / "version.ini"

# 版の文字列全体に当てる正規表現
VERSION_PATTERN = re.compile(r"v(\d+)\.(\d+)\.(\d+)")


@dataclass(frozen=True, slots=True, order=True)
class Version:
    """`v{メジャー}.{マイナー}.{パッチ}` の 3 つの整数。並びの比較はメジャー → マイナー → パッチの順。"""

    major: int
    minor: int
    patch: int

    def __str__(self) -> str:
        """`v{major}.{minor}.{patch}` の形の文字列にする。"""
        return f"v{self.major}.{self.minor}.{self.patch}"


def parse_release_version(text: str) -> Version:
    """`v{メジャー}.{マイナー}.{パッチ}` の文字列を版にする。"""
    matched = VERSION_PATTERN.fullmatch(text.strip())
    # 版の形でない
    if matched is None:
        raise ValueError(
            f"版の形が違います: {text}（v{{メジャー}}.{{マイナー}}.{{パッチ}} で書いてください）"
        )
    major, minor, patch = (int(part) for part in matched.groups())
    return Version(major, minor, patch)


def compare_versions(
    workspace: Version | None, plugin: Version
) -> Literal["older", "same", "newer"]:
    """ワークスペースの版をプラグインの版と比べる。版を記録する前の形式（None）は古いものとして扱う。"""
    # 版を記録する前の形式か、プラグインより小さい
    if workspace is None or workspace < plugin:
        return "older"
    return "same" if workspace == plugin else "newer"


def read_workspace_version(root: Path) -> Version | None:
    """`mindstella-version.ini` の 1 行目を版にする。版のファイルが無ければ None を返す。"""
    path = root / VERSION_FILE
    # 版のファイルが無い: 版を記録する前の形式
    if not path.exists():
        return None
    try:
        return parse_release_version(_first_line(path))
    except ValueError as error:
        raise SchemaMismatchError([f"{VERSION_FILE}: 1 行目: {error}"]) from error


def read_plugin_version(*, path: Path = PLUGIN_VERSION_FILE) -> Version:
    """プラグインの版のファイルの 1 行目を版にする。"""
    return parse_release_version(_first_line(path))


def write_workspace_version(root: Path, version: Version) -> None:
    """`mindstella-version.ini` に版を 1 行で書く。"""
    target = root / VERSION_FILE
    try:
        temp = write_temp(target, f"{version}\n")
    except OSError as error:
        raise write_failed(target, error) from error
    try:
        os.replace(temp, target)
    except OSError as error:
        # 置き換えられなかった一時ファイルは残さない
        temp.unlink(missing_ok=True)
        raise write_failed(target, error) from error


def _first_line(path: Path) -> str:
    """ファイルの 1 行目を返す（空のファイルは空文字）。"""
    lines = path.read_text(encoding="utf-8").splitlines()
    return lines[0] if lines else ""
