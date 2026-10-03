"""開発側の点検：ワークスペースの形（スキーマ）を変えた PR が、版を上げて移し替えの手順を足しているか。

最新のタグを読むため、タグを取っていない clone では先に `git fetch --tags` を流す（タグが 1 つも無ければ skip する）。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import migrator
import versions
from versions import Version

# このファイルから見たリポジトリの直下（tests/unit/scripts の 3 つ上）
REPO_ROOT_PARENT_DEPTH = 3
REPO_ROOT = Path(__file__).resolve().parents[REPO_ROOT_PARENT_DEPTH]

# スキーマの置き場所（リポジトリの直下からの相対パス）
SCHEMA_RELATIVE_DIR = "plugins/mindstella/skills/mindmap/schemas"

# 移し替えの手順の形のスキーマ。ワークスペースの形ではないので、比べない
STEPS_SCHEMA_NAME = "migration-steps.schema.json"


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    """リポジトリの直下で git を呼び、終了コードが 0 以外でも例外にせず返す。"""
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def _latest_tag() -> Version | None:
    """`v{メジャー}.{マイナー}.{パッチ}` のタグのうち、版が最も新しいものを返す。タグが無ければ None。"""
    tags: list[Version] = []
    for name in _git("tag", "--list", "v*").stdout.split():
        # 版の形でないタグは、版の順に並べないので飛ばす
        try:
            tags.append(versions.parse_release_version(name))
        except ValueError:
            continue
    return max(tags) if tags else None


def _schema_names_at(tag: Version) -> set[str]:
    """タグの時点のスキーマのファイル名を返す（手順の形のスキーマを除く）。"""
    listed = _git("ls-tree", "--name-only", str(tag), f"{SCHEMA_RELATIVE_DIR}/").stdout.split()
    return {Path(name).name for name in listed if Path(name).name != STEPS_SCHEMA_NAME}


def _schemas_changed_since(tag: Version) -> bool:
    """タグの時点から、スキーマのファイルが増減したか中身が変わったかを返す。"""
    current_dir = REPO_ROOT / SCHEMA_RELATIVE_DIR
    current_names = {
        path.name for path in current_dir.glob("*.json") if path.name != STEPS_SCHEMA_NAME
    }
    # ファイルの増減
    if current_names != _schema_names_at(tag):
        return True
    # 中身の違い
    for name in sorted(current_names):
        shown = _git("show", f"{tag}:{SCHEMA_RELATIVE_DIR}/{name}")
        if shown.stdout != (current_dir / name).read_text(encoding="utf-8"):
            return True
    return False


def test_schema_changes_have_migration() -> None:
    """最新のタグからスキーマが変わったら、タグより新しくプラグインの版以下の手順がある（正常系）。"""
    # 準備
    latest = _latest_tag()
    if latest is None:
        pytest.skip("版のタグが 1 つも無い clone では確かめない")
    changed = _schemas_changed_since(latest)
    plugin_version = versions.read_plugin_version()
    covering = [
        version for version in migrator.list_versions() if latest < version <= plugin_version
    ]
    # 検証
    assert covering != [] or not changed, (
        f"スキーマが {latest} から変わっているのに、{latest} より新しく {plugin_version} 以下の"
        "版の手順が migrations/ にありません。版を上げて手順を足してください"
    )


def test_plugin_version_not_behind_latest_tag() -> None:
    """プラグインの版が最新のタグより前でない（正常系）。"""
    # 準備
    latest = _latest_tag()
    if latest is None:
        pytest.skip("版のタグが 1 つも無い clone では確かめない")
    # 実行
    plugin_version = versions.read_plugin_version()
    # 検証
    assert plugin_version >= latest
