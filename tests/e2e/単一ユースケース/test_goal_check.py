"""ゴール判定（ゴールに届いたかを確かめ、確定の後に release/ へ書き出す）の E2E テスト。

モデルを呼ばず、スキルの手順が連ねるコマンドと release/ への書き出しを決めた引数で順に再生して、ワークスペースの状態を確かめる。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from workspace_fixtures import MakeItem, MakeWorkspace

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import Replay

# システム開発の進め方ガイドのフェーズ
PHASES = ["目的", "要件", "構成", "インターフェース", "コンテンツ"]


def _goal_settings(valid_settings: dict[str, Any]) -> dict[str, Any]:
    """ゴールがインターフェースまでで、納品物が資料 A-1 の設定を返す。"""
    return {
        **valid_settings,
        "phases": PHASES,
        "goal": {
            "phase": "インターフェース",
            "summary": "インターフェースまで決まる",
            "deliverables": [{"title": "要件定義書", "doc": "A-1"}],
        },
    }


def test_normal_when_reached(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """ゴールに届いたら、確定の後に決まった検討事項と納品物を release/ に書き出す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", phase="目的", status="決定済み", answer="記録する"),
        make_item("D-2", phase="要件", status="決定済み", answer="YAML に残す"),
        make_item("D-3", phase="構成", status="対象外"),
        make_item("D-4", phase="インターフェース", status="決定済み", answer="コマンドで書く"),
        # ゴールより後ろのフェーズは判定に入らない
        make_item("D-9", phase="コンテンツ", status="未決定"),
        make_item("A-1", deliverable=True, status="完成"),
        settings=_goal_settings(valid_settings),
        bodies={"A-1.md": "# 要件定義書\n\n支出を記録する。"},
    )
    # 前回のゴール判定で書き出した資料
    (root / "release" / "古い資料.md").write_text("前回の資料\n", encoding="utf-8")
    ws = ["--workspace", str(root)]
    # 実行
    goal = replay("goal", *ws)
    deliverable = replay("show", "A-1", *ws)
    # 利用者の確定の後に、スキルが release/ を片付けてから Markdown を書く
    replay("clear-release", *ws)
    (root / "release" / "決定事項.md").write_text(
        "# 決定事項\n\n- D-1: 記録する\n- D-2: YAML に残す\n- D-4: コマンドで書く\n",
        encoding="utf-8",
    )
    (root / "release" / "要件定義書.md").write_text(deliverable["body_markdown"], encoding="utf-8")
    replay("add", "log", *ws, data={"title": "リリース", "date": "2026-10-02", "related": ["A-1"]})
    replay("build", *ws)
    # 検証
    # goal の出力が「届いた」で、残りの検討事項と納品物が 0 件である（ゴールより後ろの D-9 を含まない）
    assert goal["reached"] is True
    assert goal["remaining_decisions"] == []
    assert goal["remaining_deliverables"] == []
    # release/ に、決まった検討事項の一覧と納品物 A-1 の本文がある
    assert "D-2" in (root / "release" / "決定事項.md").read_text(encoding="utf-8")
    assert "支出を記録する" in (root / "release" / "要件定義書.md").read_text(encoding="utf-8")
    # release/ に前回の古い資料.md が残っていない
    assert not (root / "release" / "古い資料.md").exists()
    # 会話ログが 1 件足されている
    assert [item["id"] for item in read_yaml(root, "logs.yaml")["items"]] == ["L-1"]


def test_normal_when_not_reached(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    replay: Replay,
) -> None:
    """ゴールに届いていなければ、残りを示して release/ には何も書かない（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", phase="目的", status="未決定"),
        make_item("A-1", deliverable=True, status="確認中"),
        settings=_goal_settings(valid_settings),
        bodies={"A-1.md": "要件定義書の下書き"},
    )
    ws = ["--workspace", str(root)]
    # 実行
    goal = replay("goal", *ws)
    # 検証
    # goal の出力が「届いていない」で、残りに D-1 と A-1 がある
    assert goal["reached"] is False
    assert [decision["id"] for decision in goal["remaining_decisions"]] == ["D-1"]
    assert goal["remaining_deliverables"] == [{"title": "要件定義書", "doc": "A-1"}]
    # release/ に何も書かれていない
    assert list((root / "release").iterdir()) == []
