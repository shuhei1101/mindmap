"""依存をたどって、影響・次の候補・再開時の状況を出す（読むだけで、ファイルを書かない）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, cast

from kinds import KINDS, Kind, id_number, kind_of_id
from store import Workspace, as_ids, find_item

# 再開時の状況に載せる次の候補の件数
STATUS_NEXT_LIMIT = 3

# ゴールの成果物ができたとみなす資料の状態
DOC_COMPLETE_STATUS = "完成"

# 影響度 → 並べる順。影響度が無いものは最後
WEIGHT_ORDER = {"大": 0, "中": 1, "小": 2}

# 種類 → 参照先から参照元へ逆向きにたどるキー
IMPACT_KEYS: dict[Kind, tuple[str, ...]] = {
    "decision": ("depends_on", "parent"),
    "task": ("for", "depends_on"),
}

# ID → 項目の種類と中身
type ItemIndex = dict[str, tuple[Kind, dict[str, Any]]]

# 影響をたどるキー
type ImpactKey = Literal["depends_on", "parent", "for"]


@dataclass(frozen=True, slots=True, kw_only=True)
class Affected:
    """影響の洗い出しの出力の `affected[]` の 1 行。"""

    id: str
    title: str
    status: str
    # 起点とこの項目の間にある項目の ID
    via: list[str]
    # 直前の項目とつなぐキー
    key: ImpactKey


@dataclass(frozen=True, slots=True, kw_only=True)
class Candidate:
    """次の候補の出力の `candidates[]` の 1 行。"""

    id: str
    title: str
    phase: str | None
    weight: Literal["大", "中", "小"] | None
    # 後続の件数
    followers: int


@dataclass(frozen=True, slots=True, kw_only=True)
class Waiting:
    """再開時の状況の `waiting[]` の 1 行。"""

    id: str
    title: str
    # 未完了の `depends_on` の ID
    waiting_for: list[str]


@dataclass(frozen=True, slots=True, kw_only=True)
class StatusSummary:
    """再開時の状況の出力全体。"""

    needs_review: list[dict[str, str]]
    in_progress: list[dict[str, str]]
    resumable: list[dict[str, str]]
    waiting: list[Waiting]
    on_hold: list[dict[str, str | None]]
    next: list[Candidate]


@dataclass(frozen=True, slots=True, kw_only=True)
class GoalReport:
    """ゴール判定の結果。ゴールに届いたかと、残りの検討事項・成果物。"""

    # 届いたか（残りがどちらも空のときだけ真）
    reached: bool
    # 設定の `goal.phase`
    goal_phase: str
    # 判定に入れたフェーズ
    phases: list[str]
    # 決着していない検討事項（`id`・`title`・`phase`・`status`）
    remaining_decisions: list[dict[str, str]]
    # 揃っていない成果物（`title`・`doc`）
    remaining_deliverables: list[dict[str, str | None]]


def build_reverse_edges(workspace: Workspace) -> dict[str, list[tuple[str, str]]]:
    """参照先の ID → それを参照する項目とキーの並びを作る。"""
    edges: dict[str, list[tuple[str, str]]] = {}
    for kind, keys in IMPACT_KEYS.items():
        for item in workspace.items[kind]:
            for key in keys:
                # 参照元の並びはファイルの並び
                for target_id in as_ids(item.get(key)):
                    edges.setdefault(target_id, []).append((item["id"], key))
    return edges


def trace_impact(workspace: Workspace, start_id: str) -> list[Affected]:
    """起点から逆向きの参照を幅優先でたどり、影響を受ける項目を近い順に返す。"""
    # 起点があるか確かめる
    find_item(workspace, start_id)
    edges = build_reverse_edges(workspace)
    index = _index_items(workspace)
    # 起点から各項目までの途中の項目の ID（最初に届いた経路）
    via_of: dict[str, list[str]] = {start_id: []}
    visited = {start_id}
    frontier = [start_id]
    affected: list[Affected] = []
    while frontier:
        # 同じ距離で初めて届いた項目と、その直前の項目・キー
        found: dict[str, tuple[str, str]] = {}
        for current in frontier:
            for ref_id, key in edges.get(current, []):
                # 一度出た項目・ワークスペースに無い項目はたどらない
                if ref_id in visited or ref_id in found or ref_id not in index:
                    continue
                found[ref_id] = (current, key)
        # 同じ距離の中は ID の順に並べる
        frontier = sorted(found, key=_order_key)
        for node in frontier:
            parent, key = found[node]
            via_of[node] = [] if parent == start_id else [*via_of[parent], parent]
            item = index[node][1]
            affected.append(
                Affected(
                    id=node,
                    title=str(item.get("title", "")),
                    status=str(item.get("status", "")),
                    via=via_of[node],
                    key=cast(ImpactKey, key),
                )
            )
        visited.update(found)
    return affected


def judge_goal(workspace: Workspace) -> GoalReport:
    """ゴールのフェーズまでの検討事項が決着し、ゴールの成果物が揃ったかを判定する。"""
    settings = workspace.settings
    phases = settings.get("phases")
    phase_order = [str(phase) for phase in phases] if isinstance(phases, list) else []
    goal = settings.get("goal")
    goal_settings = goal if isinstance(goal, dict) else {}
    goal_phase = str(goal_settings.get("phase", ""))
    # ゴールのフェーズが phases にあれば先頭からそこまで、無ければ全てのフェーズ（厳しい側に倒す）
    judged_phases = (
        phase_order[: phase_order.index(goal_phase) + 1]
        if goal_phase in phase_order
        else phase_order
    )
    # 判定に入るフェーズの検討事項のうち、決着していないものをフェーズの順 → 連番の順に集める
    unsettled = [
        item
        for item in workspace.items["decision"]
        if item.get("phase") in judged_phases and not is_settled("decision", item)
    ]
    unsettled.sort(key=lambda item: (judged_phases.index(item["phase"]), id_number(item["id"])))
    remaining_decisions = [
        {
            "id": item["id"],
            "title": str(item.get("title", "")),
            "phase": item["phase"],
            "status": str(item.get("status", "")),
        }
        for item in unsettled
    ]
    # ゴールの成果物のうち、資料に繋がっていないか、資料が完成していないものを並びのまま集める
    docs = {item["id"]: item for item in workspace.items["doc"]}
    deliverables = goal_settings.get("deliverables")
    remaining_deliverables: list[dict[str, str | None]] = []
    for deliverable in deliverables if isinstance(deliverables, list) else []:
        doc_id = deliverable.get("doc")
        doc = docs.get(doc_id) if doc_id is not None else None
        # 資料が無いか、状態が完成でない
        if doc is None or doc.get("status") != DOC_COMPLETE_STATUS:
            remaining_deliverables.append(
                {"title": str(deliverable.get("title", "")), "doc": doc_id}
            )
    return GoalReport(
        reached=not remaining_decisions and not remaining_deliverables,
        goal_phase=goal_phase,
        phases=judged_phases,
        remaining_decisions=remaining_decisions,
        remaining_deliverables=remaining_deliverables,
    )


def is_settled(kind: Kind, item: dict[str, Any] | None) -> bool:
    """項目の状態がその種類の決着に当たるか。無い項目（None）は未完了として偽を返す。"""
    if item is None:
        return False
    return item.get("status") in KINDS[kind].settled_statuses


def count_followers(workspace: Workspace, item_id: str) -> int:
    """影響の洗い出しと同じたどり方で得た項目のうち、未完了のものを数える。"""
    index = _index_items(workspace)
    return sum(
        1 for affected in trace_impact(workspace, item_id) if not _is_id_settled(index, affected.id)
    )


def list_next_candidates(workspace: Workspace, *, limit: int | None = None) -> list[Candidate]:
    """前提が揃った未決定の検討事項を、フェーズ → 影響度 → 後続の件数 → 連番の順に並べる。"""
    index = _index_items(workspace)
    phases = workspace.settings.get("phases")
    phase_order = phases if isinstance(phases, list) else []
    candidates: list[Candidate] = []
    for item in workspace.items["decision"]:
        if item.get("status") != "未決定":
            continue
        # 前提（depends_on）が全て決着していないものは候補にしない（無い ID は未完了）
        if not all(_is_id_settled(index, dep) for dep in as_ids(item.get("depends_on"))):
            continue
        candidates.append(
            Candidate(
                id=item["id"],
                title=str(item.get("title", "")),
                phase=item.get("phase"),
                weight=item.get("weight"),
                followers=count_followers(workspace, item["id"]),
            )
        )

    def _sort_key(candidate: Candidate) -> tuple[int, int, int, int]:
        """フェーズの並び（無い・設定に無いものは最後）→ 影響度 → 後続の多い順 → 連番。"""
        phase_rank = (
            phase_order.index(candidate.phase)
            if candidate.phase in phase_order
            else len(phase_order)
        )
        weight_rank = WEIGHT_ORDER.get(candidate.weight or "", len(WEIGHT_ORDER))
        return (phase_rank, weight_rank, -candidate.followers, id_number(candidate.id))

    ordered = sorted(candidates, key=_sort_key)
    return ordered if limit is None else ordered[:limit]


def summarize_status(workspace: Workspace) -> StatusSummary:
    """要見直し・進行中・再開可能・決定待ち・そのほかの保留・次の候補をまとめる。"""
    index = _index_items(workspace)
    needs_review: list[dict[str, str]] = []
    in_progress: list[dict[str, str]] = []
    resumable: list[dict[str, str]] = []
    waiting: list[Waiting] = []
    on_hold: list[dict[str, str | None]] = []
    # 種類の順（検討事項 → タスク）・連番の小さい順に見る
    for kind in ("decision", "task"):
        for item in sorted(workspace.items[kind], key=lambda item: id_number(item["id"])):
            row = {"id": item["id"], "title": str(item.get("title", ""))}
            status = item.get("status")
            if kind == "decision" and status == "要見直し":
                needs_review.append(row)
            elif kind == "task" and status == "進行中":
                in_progress.append(row)
            elif status == "保留":
                depends_on = as_ids(item.get("depends_on"))
                unsettled = [dep for dep in depends_on if not _is_id_settled(index, dep)]
                # depends_on が無い: 再開できるかは reason を読んで判断する保留
                if not depends_on:
                    on_hold.append({**row, "reason": item.get("reason")})
                # 全て決着している: 再開できる
                elif not unsettled:
                    resumable.append(row)
                # 未完了が残る: 決定待ち
                else:
                    waiting.append(Waiting(waiting_for=unsettled, **row))
    return StatusSummary(
        needs_review=needs_review,
        in_progress=in_progress,
        resumable=resumable,
        waiting=waiting,
        on_hold=on_hold,
        next=list_next_candidates(workspace, limit=STATUS_NEXT_LIMIT),
    )


def _index_items(workspace: Workspace) -> ItemIndex:
    """ID → 項目の種類と中身の引き当て表を作る。"""
    return {
        item["id"]: (kind, item)
        for kind in KINDS
        for item in workspace.items[kind]
        if isinstance(item.get("id"), str)
    }


def _is_id_settled(index: ItemIndex, item_id: str) -> bool:
    """ID の項目が決着しているか。ワークスペースに無い ID は未完了として扱う。"""
    entry = index.get(item_id)
    return entry is not None and is_settled(entry[0], entry[1])


def _order_key(item_id: str) -> tuple[int, int]:
    """種類の順（D・T・R・A・G・N・L）→ 連番の順に並べるためのキーを返す。"""
    kind = kind_of_id(item_id)
    kind_rank = list(KINDS).index(kind) if kind is not None else len(KINDS)
    return (kind_rank, id_number(item_id))
