"""migrator.py（前の版の形式の記録を今の形式に移す）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
import yaml

import migrator
from errors import SchemaMismatchError, SummaryRequiredError, WriteFailedError
from fixture_types import (
    FailingReplace,
    MakeItem,
    MakeLegacyItem,
    MakeLegacyWorkspace,
    MakeWorkspace,
    SnapshotTree,
)


def test_migrate_settings(valid_settings: dict[str, Any]) -> None:
    """題名を先頭に足す（正常系）。"""
    # 準備
    settings = {key: value for key, value in valid_settings.items() if key != "summary"}
    # 実行
    migrated, entry = migrator.migrate_settings(settings, summary=" 題名 ")
    # 検証
    assert list(migrated)[0] == "summary"
    assert migrated["summary"] == "題名"
    assert list(migrated)[1:] == list(settings)
    assert entry is not None
    assert entry.id is None
    assert entry.file == "mindmap.yaml"


def test_migrate_settings_when_summary_present(valid_settings: dict[str, Any]) -> None:
    """題名を持つ設定は変えない（正常系）。"""
    # 実行
    migrated, entry = migrator.migrate_settings(valid_settings, summary="別の題名")
    # 検証
    assert migrated == valid_settings
    assert entry is None


@pytest.mark.parametrize(
    "summary",
    [
        pytest.param(None, id="none"),
        pytest.param("  ", id="blank"),
    ],
)
def test_migrate_settings_when_summary_missing(
    valid_settings: dict[str, Any], summary: str | None
) -> None:
    """題名が無く引数も無ければ送る（異常系）。"""
    # 準備
    settings = {key: value for key, value in valid_settings.items() if key != "summary"}
    # 実行・検証
    with pytest.raises(SummaryRequiredError, match="--summary"):
        migrator.migrate_settings(settings, summary=summary)


def test_migrate_docs_items(make_legacy_item: MakeLegacyItem, make_item: MakeItem) -> None:
    """done を状態に置き換える（正常系）。"""
    # 準備
    items = [
        make_legacy_item("A-1", True),
        make_legacy_item("A-2", False),
        make_item("A-3", status="確認中"),
    ]
    # 実行
    migrated, entries = migrator.migrate_docs_items(items)
    # 検証
    assert migrated[0]["status"] == "完成"
    assert migrated[1]["status"] == "下書き"
    assert "done" not in migrated[0]
    assert "done" not in migrated[1]
    # キーの位置と更新日時は元のまま
    assert list(migrated[0]) == list(make_item("A-1"))
    assert migrated[0]["updated"] == items[0]["updated"]
    assert migrated[2] == items[2]
    assert [(entry.id, entry.file, entry.change) for entry in entries] == [
        ("A-1", "docs.yaml", "done: true → status: 完成"),
        ("A-2", "docs.yaml", "done: false → status: 下書き"),
    ]


def test_migrate_docs_items_when_not_bool(make_legacy_item: MakeLegacyItem) -> None:
    """真偽値でない done は移さない（正常系）。"""
    # 準備
    item = make_legacy_item("A-1", True)
    item["done"] = "yes"
    # 実行
    migrated, entries = migrator.migrate_docs_items([item])
    # 検証
    assert migrated == [item]
    assert entries == []


def test_migrate_workspace(make_legacy_workspace: MakeLegacyWorkspace) -> None:
    """題名を足し、資料の done を移す（正常系）。"""
    # 準備
    root = make_legacy_workspace(legacy_docs={"A-1": True}, without_summary=True)
    # 実行
    entries = migrator.migrate_workspace(root, summary="題名")
    # 検証
    assert [(entry.id, entry.file) for entry in entries] == [
        (None, "mindmap.yaml"),
        ("A-1", "docs.yaml"),
    ]
    settings = yaml.safe_load((root / "mindmap.yaml").read_text(encoding="utf-8"))
    docs = yaml.safe_load((root / "docs.yaml").read_text(encoding="utf-8"))
    assert settings["summary"] == "題名"
    assert docs["items"][0]["status"] == "完成"
    assert "done" not in docs["items"][0]


def test_migrate_workspace_when_nothing(
    make_workspace: MakeWorkspace, make_item: MakeItem, snapshot_tree: SnapshotTree
) -> None:
    """移すものが無ければ書かない（正常系）。"""
    # 準備
    root = make_workspace(make_item("A-1", status="完成"))
    before = snapshot_tree(root)
    mtimes = {name: (root / name).stat().st_mtime_ns for name in ("mindmap.yaml", "docs.yaml")}
    # 実行
    entries = migrator.migrate_workspace(root, summary=None)
    # 検証
    assert entries == []
    assert snapshot_tree(root) == before
    assert {name: (root / name).stat().st_mtime_ns for name in mtimes} == mtimes


def test_migrate_workspace_when_schema_mismatch(
    make_legacy_workspace: MakeLegacyWorkspace, make_item: MakeItem, snapshot_tree: SnapshotTree
) -> None:
    """移しても合わなければ書かない（異常系）。"""
    # 準備
    root = make_legacy_workspace(make_item("D-1", status="完了"), legacy_docs={"A-1": True})
    before = snapshot_tree(root)
    # 実行・検証
    with pytest.raises(SchemaMismatchError) as exc_info:
        migrator.migrate_workspace(root, summary=None)
    assert any(line.startswith("decisions.yaml: items[0].status:") for line in exc_info.value.lines)
    assert snapshot_tree(root) == before


def test_migrate_workspace_when_replace_fails(
    make_legacy_workspace: MakeLegacyWorkspace,
    snapshot_tree: SnapshotTree,
    failing_replace: FailingReplace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """2 つ目の置き換えに失敗したら 1 つ目を戻す（異常系）。"""
    # 準備
    root = make_legacy_workspace(legacy_docs={"A-1": True}, without_summary=True)
    before = snapshot_tree(root)
    # migrator モジュールの参照を、mindmap.yaml への置き換えが失敗するものに差し替える
    monkeypatch.setattr(migrator.os, "replace", failing_replace("mindmap.yaml"))
    # 実行・検証
    with pytest.raises(WriteFailedError):
        migrator.migrate_workspace(root, summary="題名")
    assert snapshot_tree(root) == before
    assert list(root.rglob("*.tmp")) == []
