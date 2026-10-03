"""conftest の fixture が返す関数の型と、テストが共有する値（テストの引数の注釈・期待値に使う）。"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from playwright.sync_api import Page

__all__ = [
    "BODY_WITH_DIAGRAM",
    "ID_BUTTON_MIN_SIZE_PX",
    "ID_BUTTON_SIZE_JS",
    "MAIN_SELECTOR",
    "OpenPreview",
    "WritePreview",
    "WriteSamplePreview",
]

type WritePreview = Callable[..., Path]
type WriteSamplePreview = Callable[[], Path]
type OpenPreview = Callable[..., Page]

# 本文に見出しと mermaid の図を持つ本文
BODY_WITH_DIAGRAM = """# 要件

本文の段落

## 流れ

```mermaid
flowchart LR
  A --> B
```
"""

# 画面が描き終わったとみなす本文の領域の要素
MAIN_SELECTOR = "main#main"

# ID のボタンの見えている枠の縦横の下限（px。デザイン方針の `--target-min`）
ID_BUTTON_MIN_SIZE_PX = 24

# ID のボタンの数と、全てのボタンの外形の幅と高さのうち一番小さい値を返す（`eval_on_selector_all` に渡す）
ID_BUTTON_SIZE_JS = (
    "buttons => ({ count: buttons.length, smallest: Math.min(...buttons.flatMap("
    "b => { const r = b.getBoundingClientRect(); return [r.width, r.height]; })) })"
)
