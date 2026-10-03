"""conftest の fixture が返す関数の型（テストの引数の注釈に使う）。共有の型は tests/workspace_fixtures.py から取る。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from workspace_fixtures import (
    MakeItem,
    MakeLegacyItem,
    MakeLegacyWorkspace,
    MakeWorkspace,
    SnapshotTree,
)

__all__ = [
    "FailingReplace",
    "FailingWriteText",
    "MakeItem",
    "MakeLegacyItem",
    "MakeLegacyWorkspace",
    "MakeWorkspace",
    "SnapshotTree",
]

type FailingReplace = Callable[[str], Callable[[Any, Any], None]]
type FailingWriteText = Callable[[str], None]
