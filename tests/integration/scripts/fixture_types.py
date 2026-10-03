"""conftest の fixture が返す関数の型（テストの引数の注釈に使う）。共有の型は tests/workspace_fixtures.py から取る。"""

from __future__ import annotations

from collections.abc import Callable

from workspace_fixtures import (
    MakeItem,
    MakeLegacyWorkspace,
    MakeVenv,
    MakeWorkspace,
    RunMindmap,
    SnapshotTree,
)

__all__ = [
    "FindOldPython",
    "LockDirs",
    "MakeItem",
    "MakeLegacyWorkspace",
    "MakeVenv",
    "MakeWorkspace",
    "RunMindmap",
    "SnapshotTree",
]

type LockDirs = Callable[..., None]
type FindOldPython = Callable[[], str]
