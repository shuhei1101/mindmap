"""kinds.py（種類の定義）の単体テスト。"""

from __future__ import annotations

import pytest

import kinds


@pytest.mark.parametrize(
    ("item_id", "expected"),
    [
        pytest.param("D-12", "decision", id="decision"),
        pytest.param("L-1", "log", id="log"),
    ],
)
def test_kind_of_id_when_known_prefix(item_id: str, expected: str) -> None:
    """頭の文字から種類を引く（正常系）。"""
    # 実行
    kind = kinds.kind_of_id(item_id)
    # 検証
    assert kind == expected


@pytest.mark.parametrize(
    "item_id",
    [
        pytest.param("X-1", id="unknown_prefix"),
        pytest.param("D-", id="no_number"),
        pytest.param("D-0x", id="not_digits"),
        pytest.param("d-1", id="lowercase"),
    ],
)
def test_kind_of_id_when_unknown(item_id: str) -> None:
    """形が合わない・頭の文字が無い ID は None を返す（正常系）。"""
    # 実行
    kind = kinds.kind_of_id(item_id)
    # 検証
    assert kind is None
