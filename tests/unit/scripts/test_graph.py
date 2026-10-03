"""graph.py（逆向きの参照・影響・後続の件数・次の候補・再開時の状況）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest

import graph
import store
from fixture_types import MakeItem, MakeWorkspace


def _id_and_followers(candidates: list[graph.Candidate]) -> list[tuple[str, int]]:
    """候補から ID と後続の件数の組を並びのまま取り出す。"""
    return [(candidate.id, candidate.followers) for candidate in candidates]


@pytest.fixture
def next_workspace(make_workspace: MakeWorkspace, make_item: MakeItem) -> store.Workspace:
    """次の候補を並べるためのワークスペース（フェーズは 目的 → 要件 → 構成）を読み込んで返す。"""
    root = make_workspace(
        make_item("D-1", phase="要件", weight="小"),
        make_item("D-2", phase="目的", weight="小"),
        make_item("D-3", phase="要件", weight="大"),
        make_item("D-4", phase="要件", weight="大"),
        make_item("D-5", depends_on=["D-1"]),
        make_item("D-6", depends_on=["D-4"]),
        make_item("D-7", depends_on=["D-6"]),
    )
    return store.load_workspace(root)


def test_build_reverse_edges(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """depends_on・parent・for を逆向きにし、related は含めない（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"),
        make_item("D-2", depends_on=["D-1"]),
        make_item("D-3", parent="D-1"),
        make_item("D-4", related=["D-1"]),
        make_item("T-1", **{"for": ["D-1"]}),
    )
    workspace = store.load_workspace(root)
    # 実行
    edges = graph.build_reverse_edges(workspace)
    # 検証
    assert edges["D-1"] == [("D-2", "depends_on"), ("D-3", "parent"), ("T-1", "for")]


def test_trace_impact(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """間接の影響まで、経路つきで近い順に返す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"),
        make_item("D-2", title="直接の依存", depends_on=["D-1"]),
        make_item("D-3", title="派生", parent="D-2"),
        make_item("D-4", related=["D-1"]),
        make_item("T-1", title="進めるタスク", **{"for": ["D-3"]}),
    )
    workspace = store.load_workspace(root)
    # 実行
    affected = graph.trace_impact(workspace, "D-1")
    # 検証
    assert affected == [
        graph.Affected(id="D-2", title="直接の依存", status="未決定", via=[], key="depends_on"),
        graph.Affected(id="D-3", title="派生", status="未決定", via=["D-2"], key="parent"),
        graph.Affected(
            id="T-1",
            title="進めるタスク",
            status="未着手",
            via=["D-2", "D-3"],
            key="for",
        ),
    ]


def test_trace_impact_when_cycle(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """循環があっても同じ項目を 2 度出さず終わる（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", depends_on=["D-2"]),
        make_item("D-2", title="循環の相手", depends_on=["D-1"]),
    )
    workspace = store.load_workspace(root)
    # 実行
    affected = graph.trace_impact(workspace, "D-1")
    # 検証
    assert affected == [
        graph.Affected(id="D-2", title="循環の相手", status="未決定", via=[], key="depends_on"),
    ]


@pytest.mark.parametrize(
    ("kind", "item", "expected"),
    [
        pytest.param("decision", {"status": "決定済み"}, True, id="decision_settled"),
        pytest.param("decision", {"status": "保留"}, False, id="decision_on_hold"),
        pytest.param("task", {"status": "中止"}, True, id="task_cancelled"),
        pytest.param("task", {"status": "進行中"}, False, id="task_in_progress"),
    ],
)
def test_is_settled(kind: str, item: dict[str, Any], expected: bool) -> None:
    """種類ごとの決着を見分ける（正常系）。"""
    # 実行
    settled = graph.is_settled(kind, item)
    # 検証
    assert settled is expected


def test_is_settled_when_missing() -> None:
    """無い項目は未完了として扱う（正常系）。"""
    # 実行
    settled = graph.is_settled("decision", None)
    # 検証
    assert settled is False


def test_count_followers(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """間接の後続も数え、決着したものは数えない（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-4"),
        make_item("D-6", depends_on=["D-4"]),
        make_item("D-7", depends_on=["D-6"]),
        make_item("D-8", depends_on=["D-4"], status="決定済み"),
    )
    workspace = store.load_workspace(root)
    # 実行
    followers = graph.count_followers(workspace, "D-4")
    # 検証
    assert followers == 2


def test_list_next_candidates(next_workspace: store.Workspace) -> None:
    """前提が揃った未決定を決めた順に並べる（正常系）。"""
    # 実行
    candidates = graph.list_next_candidates(next_workspace)
    # 検証
    assert _id_and_followers(candidates) == [
        ("D-2", 0),
        ("D-4", 2),
        ("D-3", 0),
        ("D-1", 1),
    ]


def test_list_next_candidates_when_phase_unknown(
    make_workspace: MakeWorkspace, make_item: MakeItem
) -> None:
    """フェーズが無い・設定に無い候補は最後に並べる（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"),
        make_item("D-2", phase="その他"),
        make_item("D-3", phase="構成"),
    )
    workspace = store.load_workspace(root)
    # 実行
    candidates = graph.list_next_candidates(workspace)
    # 検証
    assert _id_and_followers(candidates) == [("D-3", 0), ("D-1", 0), ("D-2", 0)]


def test_list_next_candidates_when_limited(next_workspace: store.Workspace) -> None:
    """上限で切る（正常系）。"""
    # 実行
    candidates = graph.list_next_candidates(next_workspace, limit=2)
    # 検証
    assert _id_and_followers(candidates) == [("D-2", 0), ("D-4", 2)]


def test_summarize_status(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """状態と依存で分ける（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", title="見直しの問い", status="要見直し"),
        make_item("T-1", title="進めている作業", status="進行中"),
        make_item("D-2", title="再開できる保留", status="保留", depends_on=["D-3"]),
        make_item("D-3", status="決定済み"),
        make_item("D-4", title="決定待ちの保留", status="保留", depends_on=["D-5"]),
        make_item("D-5"),
        make_item("D-6", title="予算待ち", status="保留", reason="予算が決まったら"),
        make_item("T-2", title="作業待ちの保留", status="保留", depends_on=["T-1"]),
    )
    workspace = store.load_workspace(root)
    # 実行
    summary = graph.summarize_status(workspace)
    # 検証
    assert summary.needs_review == [{"id": "D-1", "title": "見直しの問い"}]
    assert summary.in_progress == [{"id": "T-1", "title": "進めている作業"}]
    assert summary.resumable == [{"id": "D-2", "title": "再開できる保留"}]
    assert summary.waiting == [
        graph.Waiting(id="D-4", title="決定待ちの保留", waiting_for=["D-5"]),
        graph.Waiting(id="T-2", title="作業待ちの保留", waiting_for=["T-1"]),
    ]
    assert summary.on_hold == [{"id": "D-6", "title": "予算待ち", "reason": "予算が決まったら"}]
    assert len(summary.next) == 1
    assert summary.next[0].id == "D-5"


def test_judge_goal(
    make_workspace: MakeWorkspace, make_item: MakeItem, valid_settings: dict[str, Any]
) -> None:
    """ゴールより後ろのフェーズを入れずに届いたと判定する（正常系）。"""
    # 準備
    settings = {
        **valid_settings,
        "phases": ["目的", "要件", "構成"],
        "goal": {
            "phase": "要件",
            "summary": "要件が決まる",
            "deliverables": [{"title": "要件定義書", "doc": "A-1"}],
        },
    }
    root = make_workspace(
        make_item("D-1", phase="目的", status="決定済み"),
        make_item("D-2", phase="要件", status="対象外"),
        make_item("D-3", phase="要件", status="取り下げ"),
        make_item("D-4", phase="構成", status="未決定"),
        make_item("A-1", deliverable=True, status="完成"),
        settings=settings,
        bodies={"A-1.md": "要件定義書の本文"},
    )
    workspace = store.load_workspace(root)
    # 実行
    report = graph.judge_goal(workspace)
    # 検証
    assert report.reached is True
    assert report.goal_phase == "要件"
    assert report.phases == ["目的", "要件"]
    assert report.remaining_decisions == []
    assert report.remaining_deliverables == []


def test_judge_goal_when_remaining(
    make_workspace: MakeWorkspace, make_item: MakeItem, valid_settings: dict[str, Any]
) -> None:
    """決着していない検討事項と揃っていない成果物を集める（正常系）。"""
    # 準備
    settings = {
        **valid_settings,
        "phases": ["目的", "要件", "構成"],
        "goal": {
            "phase": "要件",
            "summary": "要件が決まる",
            "deliverables": [
                {"title": "要件定義書", "doc": "A-1"},
                {"title": "用語集"},
                {"title": "図", "doc": "A-9"},
            ],
        },
    }
    root = make_workspace(
        make_item("D-2", phase="要件", status="要見直し"),
        make_item("D-1", phase="目的", status="未決定"),
        make_item("D-3", phase="要件", status="決定済み"),
        make_item("A-1", deliverable=True, status="確認中"),
        settings=settings,
        bodies={"A-1.md": "要件定義書の本文"},
    )
    workspace = store.load_workspace(root)
    # 実行
    report = graph.judge_goal(workspace)
    # 検証
    assert report.reached is False
    assert report.remaining_decisions == [
        {"id": "D-1", "title": "D-1の題", "phase": "目的", "status": "未決定"},
        {"id": "D-2", "title": "D-2の題", "phase": "要件", "status": "要見直し"},
    ]
    assert report.remaining_deliverables == [
        {"title": "要件定義書", "doc": "A-1"},
        {"title": "用語集", "doc": None},
        {"title": "図", "doc": "A-9"},
    ]


def test_judge_goal_when_goal_phase_unknown(
    make_workspace: MakeWorkspace, make_item: MakeItem, valid_settings: dict[str, Any]
) -> None:
    """ゴールのフェーズが phases に無ければ全てのフェーズを判定に入れる（正常系）。"""
    # 準備
    settings = {
        **valid_settings,
        "phases": ["目的", "要件"],
        "goal": {"phase": "実装", "summary": "実装まで", "deliverables": []},
    }
    root = make_workspace(
        make_item("D-1", phase="要件", status="未決定"),
        settings=settings,
    )
    workspace = store.load_workspace(root)
    # 実行
    report = graph.judge_goal(workspace)
    # 検証
    assert report.phases == ["目的", "要件"]
    assert [decision["id"] for decision in report.remaining_decisions] == ["D-1"]
