"""conftest の fixture が返す関数の型（テストの引数の注釈に使う）。共有の型は tests/workspace_fixtures.py から取る。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from workspace_fixtures import MakeItem

__all__ = ["LoadLibrary", "LoadPreviewScripts", "MakeData", "MakeItem"]

type LoadPreviewScripts = Callable[..., None]
type LoadLibrary = Callable[[str], None]
type MakeData = Callable[..., dict[str, Any]]
