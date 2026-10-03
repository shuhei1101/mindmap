"""conftest の fixture が返す関数の型（テストの引数の注釈に使う）。"""

from __future__ import annotations

from collections.abc import Callable

from playwright.sync_api import Page

__all__ = ["OpenStory"]

type OpenStory = Callable[[str], Page]
