"""conftest の fixture が返す関数の型（テストの引数の注釈に使う）。"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

type RunMindmap = Callable[..., subprocess.CompletedProcess[str]]
type MakeItem = Callable[..., dict[str, Any]]
type MakeWorkspace = Callable[..., Path]
type SnapshotTree = Callable[[Path], dict[str, bytes]]
type LockDirs = Callable[..., None]
type MakeVenv = Callable[..., Path]
type FindOldPython = Callable[[], str]
