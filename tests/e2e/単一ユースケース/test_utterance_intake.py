"""発言の取り込み（利用者の発言を記録し、派生の検討事項・タスクを積む）の E2E テスト。

モデルを呼ばず、スキルの手順が連ねる書き込みを決めた引数で順に再生して、ワークスペースの状態を確かめる。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from preview_helpers import preview_reflects_yaml
from workspace_fixtures import MakeItem, MakeWorkspace, RunMindmap

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import Replay

# valid_settings の対象・カテゴリー（記録した項目に付ける）
PLACE = {"target": "mindmap", "category": "データ構造", "phase": "要件"}

# 会話の日付
TODAY = "2026-10-02"


def test_normal(
    make_workspace: MakeWorkspace,
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """決め事・派生の検討事項・未整理・タスク・会話ログを積み、プレビューを書き出し直す（正常系）。"""
    # 準備
    root = make_workspace()
    ws = ["--workspace", str(root)]
    # 実行
    replay(
        "add",
        "decision",
        *ws,
        data={
            "title": "保存先",
            "status": "決定済み",
            "answer": "YAML",
            "reason": "手で読める",
            **PLACE,
        },
    )
    replay(
        "add",
        "decision",
        *ws,
        data={"title": "ファイルの分け方", "status": "未決定", "parent": "D-1", **PLACE},
    )
    replay("add", "decision", *ws, data={"title": "いつか使うかも", "status": "未整理", **PLACE})
    replay(
        "add",
        "task",
        *ws,
        data={
            "title": "分け方の案を出す",
            "kind": "作業",
            "status": "未着手",
            "for": ["D-2"],
            **PLACE,
        },
    )
    replay("add", "log", *ws, data={"title": "発言", "date": TODAY, "related": ["D-1"], **PLACE})
    replay("build", *ws)
    # 検証
    decisions = {item["id"]: item for item in read_yaml(root, "decisions.yaml")["items"]}
    tasks = read_yaml(root, "tasks.yaml")["items"]
    logs = read_yaml(root, "logs.yaml")["items"]
    # D-1 が決定済みで answer を持つ
    assert decisions["D-1"]["status"] == "決定済み"
    assert decisions["D-1"]["answer"] == "YAML"
    # D-2 が parent: D-1 を持ち、未決定である
    assert decisions["D-2"]["parent"] == "D-1"
    assert decisions["D-2"]["status"] == "未決定"
    # D-3 が未整理である
    assert decisions["D-3"]["status"] == "未整理"
    # T-1 が for: [D-2] を持つ
    assert tasks[0]["id"] == "T-1"
    assert tasks[0]["for"] == ["D-2"]
    # 会話ログ L-1 がある
    assert logs[0]["id"] == "L-1"
    # 足した全ての項目が target・category・phase を持つ
    assert [
        decisions["D-1"]["phase"],
        decisions["D-2"]["category"],
        decisions["D-3"]["target"],
    ] == [
        "要件",
        "データ構造",
        "mindmap",
    ]
    assert [tasks[0]["target"], logs[0]["category"], logs[0]["phase"]] == [
        "mindmap",
        "データ構造",
        "要件",
    ]
    # preview.html が最後の書き込みより後に書き出されている（埋め込んだ記録が今の YAML と同じ）
    assert preview_reflects_yaml(root)


def test_normal_when_diagram_kept_as_doc(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    replay: Replay,
    run_mindmap: RunMindmap,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """会話で出した図を、本文を持つ資料に残す（正常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    ws = ["--workspace", str(root)]
    # 実行
    replay(
        "add",
        "doc",
        *ws,
        data={
            "title": "保存の流れ",
            "kind": "図",
            "deliverable": False,
            "status": "下書き",
            "related": ["D-1"],
            "body_markdown": "```mermaid\nflowchart TD\n  A --> B\n```\n",
        },
    )
    replay("add", "log", *ws, data={"title": "図を出した", "date": TODAY, "related": ["A-1"]})
    replay("build", *ws)
    checked = run_mindmap("check", *ws)
    # 検証
    doc = read_yaml(root, "docs.yaml")["items"][0]
    # 資料 A-1 が kind: 図 と related: [D-1] を持つ
    assert doc["id"] == "A-1"
    assert doc["kind"] == "図"
    assert doc["related"] == ["D-1"]
    # docs/ に A-1 の本文の Markdown がある
    assert "flowchart TD" in (root / "docs" / "A-1.md").read_text(encoding="utf-8")
    # check が YAML と Markdown のずれを 0 件で返す
    assert checked.returncode == 0
    assert json.loads(checked.stdout)["problems"] == []


def test_normal_when_off_topic_question(
    make_workspace: MakeWorkspace,
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """脱線した質問を、言葉は用語集に・それ以外はメモに残し、タスクにはしない（正常系）。"""
    # 準備
    root = make_workspace()
    ws = ["--workspace", str(root)]
    # 実行
    replay("add", "term", *ws, data={"title": "検討事項", "meaning": "問いと答えの 1 件"})
    replay(
        "add",
        "note",
        *ws,
        data={"title": "他社の例", "content": "他社は DB を使う", "tags": ["脱線"]},
    )
    replay("add", "log", *ws, data={"title": "脱線", "date": TODAY, "related": ["G-1", "N-1"]})
    replay("build", *ws)
    # 検証
    # 用語集 G-1 が meaning を持つ
    term = read_yaml(root, "terms.yaml")["items"][0]
    assert term["id"] == "G-1"
    assert term["meaning"] == "問いと答えの 1 件"
    # メモ N-1 がタグ 脱線 を持つ
    note = read_yaml(root, "notes.yaml")["items"][0]
    assert note["id"] == "N-1"
    assert note["tags"] == ["脱線"]
    # タスクが 0 件のままである
    assert replay("find", *ws, "--kind", "task")["items"] == []
