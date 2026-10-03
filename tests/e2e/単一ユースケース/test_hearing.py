"""ヒアリング（前提が揃った未決定を 1 ラウンドにまとめて聞き、答えを記録する）の E2E テスト。

モデルを呼ばず、スキルの手順が連ねるコマンドを決めた引数で順に再生して、ワークスペースの状態を確かめる。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from workspace_fixtures import MakeItem, MakeWorkspace

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import Replay


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """前提が揃った未決定だけを聞いて決定済みにし、依存していた問いが次の候補に上がる（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"),
        make_item("D-2"),
        make_item("D-3", depends_on=["D-1"]),
    )
    ws = ["--workspace", str(root)]
    # 実行
    before = replay("next", *ws)["candidates"]
    replay("update", "D-1", *ws, data={"status": "決定済み", "answer": "YAML"})
    replay("update", "D-2", *ws, data={"status": "決定済み", "answer": "種類ごとに分ける"})
    replay(
        "add",
        "log",
        *ws,
        data={"title": "ヒアリング", "date": "2026-10-02", "related": ["D-1", "D-2"]},
    )
    replay("build", *ws)
    after = replay("next", *ws)["candidates"]
    # 検証
    decisions = {item["id"]: item for item in read_yaml(root, "decisions.yaml")["items"]}
    # next の候補に D-1・D-2 があり、D-3 が無い
    assert [candidate["id"] for candidate in before] == ["D-1", "D-2"]
    # D-1・D-2 が決定済みで answer を持つ
    assert [decisions["D-1"]["status"], decisions["D-1"]["answer"]] == ["決定済み", "YAML"]
    assert [decisions["D-2"]["status"], decisions["D-2"]["answer"]] == [
        "決定済み",
        "種類ごとに分ける",
    ]
    # 書き込みの後の next の候補に D-3 がある
    assert [candidate["id"] for candidate in after] == ["D-3"]
    # 会話ログが 1 件足されている
    assert [item["id"] for item in read_yaml(root, "logs.yaml")["items"]] == ["L-1"]
