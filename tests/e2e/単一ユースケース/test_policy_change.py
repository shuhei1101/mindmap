"""方針転換（採用する案を切り替え、影響を要見直しにし、成果物を資料へ格下げする）の E2E テスト。

モデルを呼ばず、スキルの手順が連ねるコマンドと mindmap.yaml の書き換えを決めた引数で順に再生して、ワークスペースの状態を確かめる。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from workspace_fixtures import MakeItem, MakeWorkspace, RunMindmap

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import Replay

# 切り替える前と後の案の内容
OLD_CONTENT = "YAML で持つ"
NEW_CONTENT = "DB で持つ"


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """案を切り替え、影響を受けた決定済みの検討事項を要見直しにして、見直しのタスクを積む（正常系）。"""
    # 準備
    root = make_workspace(
        make_item(
            "D-1",
            status="決定済み",
            answer=OLD_CONTENT,
            options=[
                {"key": "A", "content": OLD_CONTENT, "adopted": True},
                {"key": "B", "content": NEW_CONTENT},
            ],
        ),
        make_item("D-2", status="決定済み", depends_on=["D-1"]),
        make_item("D-3", status="決定済み", depends_on=["D-2"]),
    )
    ws = ["--workspace", str(root)]
    # 実行
    replay("adopt", "D-1", "B", *ws)
    affected = replay("impact", "D-1", *ws)["affected"]
    replay("update", "D-2", *ws, data={"status": "要見直し", "reason": "保存先が変わった"})
    replay("update", "D-3", *ws, data={"status": "要見直し", "reason": "保存先が変わった"})
    replay(
        "add",
        "task",
        *ws,
        data={"title": "D-2 を見直す", "kind": "作業", "status": "未着手", "for": ["D-2"]},
    )
    replay(
        "add",
        "task",
        *ws,
        data={"title": "D-3 を見直す", "kind": "作業", "status": "未着手", "for": ["D-3"]},
    )
    replay("update", "D-1", *ws, data={"answer": NEW_CONTENT})
    replay("add", "log", *ws, data={"title": "方針転換", "date": "2026-10-02", "related": ["D-1"]})
    replay("build", *ws)
    # 検証
    decisions = {item["id"]: item for item in read_yaml(root, "decisions.yaml")["items"]}
    tasks = {item["id"]: item for item in read_yaml(root, "tasks.yaml")["items"]}
    assert [item["id"] for item in affected] == ["D-2", "D-3"]
    # D-2・D-3 が要見直しである
    assert decisions["D-2"]["status"] == "要見直し"
    assert decisions["D-3"]["status"] == "要見直し"
    # T-1・T-2 がそれぞれ for: [D-2]・for: [D-3] を持つ
    assert tasks["T-1"]["for"] == ["D-2"]
    assert tasks["T-2"]["for"] == ["D-3"]
    # D-1 の answer に A の内容が残っていない
    assert decisions["D-1"]["answer"] == NEW_CONTENT
    assert OLD_CONTENT not in decisions["D-1"]["answer"]


def test_normal_when_deliverable_no_longer_needed(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    replay: Replay,
    run_mindmap: RunMindmap,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """成果物が要らなくなったら、資料へ格下げしてゴールの成果物から外す（正常系）。"""
    # 準備
    settings = {
        **valid_settings,
        "goal": {
            "phase": "構成",
            "summary": "構成まで決まる",
            "deliverables": [{"title": "構成図", "doc": "A-1"}],
        },
    }
    root = make_workspace(
        make_item("A-1", deliverable=True, done=False),
        settings=settings,
        bodies={"A-1.md": "構成図の本文"},
    )
    ws = ["--workspace", str(root)]
    # 実行
    replay("update", "A-1", *ws, data={"deliverable": False})
    # mindmap.yaml のゴールの deliverables から A-1 を外す（スキルが Edit で直す）
    current = read_yaml(root, "mindmap.yaml")
    current["goal"]["deliverables"] = []
    (root / "mindmap.yaml").write_text(
        yaml.safe_dump(current, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    checked = run_mindmap("check", *ws)
    replay(
        "add", "log", *ws, data={"title": "スコープ変更", "date": "2026-10-02", "related": ["A-1"]}
    )
    replay("build", *ws)
    # 検証
    # A-1 が deliverable: false で、資料として残っている
    doc = read_yaml(root, "docs.yaml")["items"][0]
    assert doc["id"] == "A-1"
    assert doc["deliverable"] is False
    # ゴールの deliverables に A-1 が無い
    assert read_yaml(root, "mindmap.yaml")["goal"]["deliverables"] == []
    # check が参照切れを 0 件で返す
    assert checked.returncode == 0
    assert json.loads(checked.stdout)["problems"] == []
