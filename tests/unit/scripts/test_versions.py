"""versions.py（版の解釈・比較・読み書き）の単体テスト。"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import versions
from errors import SchemaMismatchError, WriteFailedError
from fixture_types import FailingReplace
from versions import Version

# ワークスペースの版を持つファイルの名前
VERSION_FILE = "mindstella-version.ini"


def test_parse_release_version() -> None:
    """版を解釈し、整数で比べる（正常系）。"""
    # 実行
    parsed = versions.parse_release_version(" v0.10.2\n")
    # 検証
    assert parsed == Version(0, 10, 2)
    assert parsed > versions.parse_release_version("v0.9.9")
    assert str(parsed) == "v0.10.2"


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("0.3.0", id="no_prefix"),
        pytest.param("v0.3", id="two_parts"),
        pytest.param("v0.3.0-rc1", id="suffix"),
        pytest.param("", id="empty"),
    ],
)
def test_parse_release_version_when_invalid(text: str) -> None:
    """版の形でなければ送る（異常系）。"""
    # 実行・検証
    with pytest.raises(ValueError, match=re.escape("v{メジャー}")):
        versions.parse_release_version(text)


@pytest.mark.parametrize(
    ("workspace", "plugin", "expected"),
    [
        pytest.param(None, Version(0, 3, 0), "older", id="unrecorded"),
        pytest.param(Version(0, 2, 0), Version(0, 3, 0), "older", id="older"),
        pytest.param(Version(0, 3, 0), Version(0, 3, 0), "same", id="same"),
        pytest.param(Version(0, 10, 0), Version(0, 3, 0), "newer", id="newer"),
    ],
)
def test_compare_versions(workspace: Version | None, plugin: Version, expected: str) -> None:
    """古い・同じ・新しいを返す（正常系）。"""
    # 実行
    result = versions.compare_versions(workspace, plugin)
    # 検証
    assert result == expected


def test_read_workspace_version(tmp_path: Path) -> None:
    """1 行目の版を読む（正常系）。"""
    # 準備
    (tmp_path / VERSION_FILE).write_text("v0.3.0\nほかの文字\n", encoding="utf-8")
    # 実行
    result = versions.read_workspace_version(tmp_path)
    # 検証
    assert result == Version(0, 3, 0)


def test_read_workspace_version_when_missing(tmp_path: Path) -> None:
    """版のファイルが無ければ None を返す（正常系）。"""
    # 実行
    result = versions.read_workspace_version(tmp_path)
    # 検証
    assert result is None


def test_read_workspace_version_when_invalid(tmp_path: Path) -> None:
    """1 行目が版の形でなければ送る（異常系）。"""
    # 準備
    (tmp_path / VERSION_FILE).write_text("0.3\n", encoding="utf-8")
    # 実行・検証
    with pytest.raises(SchemaMismatchError) as exc_info:
        versions.read_workspace_version(tmp_path)
    assert len(exc_info.value.lines) == 1
    assert exc_info.value.lines[0].startswith(f"{VERSION_FILE}: ")


def test_read_plugin_version(tmp_path: Path) -> None:
    """プラグインの版を読む（正常系）。"""
    # 準備
    path = tmp_path / "version.ini"
    path.write_text("v0.3.0\n", encoding="utf-8")
    # 実行
    result = versions.read_plugin_version(path=path)
    # 検証
    assert result == Version(0, 3, 0)


def test_write_workspace_version(tmp_path: Path) -> None:
    """版を 1 行で書く（正常系）。"""
    # 実行
    versions.write_workspace_version(tmp_path, Version(0, 3, 0))
    # 検証
    assert (tmp_path / VERSION_FILE).read_text(encoding="utf-8") == "v0.3.0\n"


def test_write_workspace_version_when_write_fails(
    tmp_path: Path, failing_replace: FailingReplace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """置き換えられなければ送る（異常系）。"""
    # 準備
    # versions モジュールの参照を、版のファイルへの置き換えが失敗するものに差し替える
    monkeypatch.setattr(versions.os, "replace", failing_replace(VERSION_FILE))
    # 実行・検証
    with pytest.raises(WriteFailedError):
        versions.write_workspace_version(tmp_path, Version(0, 3, 0))
    assert not (tmp_path / VERSION_FILE).exists()
    assert list(tmp_path.rglob("*.tmp")) == []
