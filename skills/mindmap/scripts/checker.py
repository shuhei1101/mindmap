"""スキーマ違反・ID の重複・参照切れ・本文のずれの点検（読むだけで、ファイルを書かない）。"""

from __future__ import annotations

from typing import Any

from kinds import BODY_DIR, KINDS, SETTINGS_FILE, kind_of_id
from store import Problem, Workspace, as_ids, read_body, validate_workspace

# 設定の成果物の資料を指すキー（`REF_RULES` の参照する側の種類に使う）
SETTINGS_KIND = "settings"
DELIVERABLE_DOC_KEY = "goal.deliverables[].doc"

# （参照する側の種類, キー）→ 指してよい種類。表に無い組はそのキーを持たない
REF_RULES: dict[tuple[str, str], frozenset[str]] = {
    ("decision", "depends_on"): frozenset({"decision"}),
    ("decision", "parent"): frozenset({"decision"}),
    ("decision", "sources"): frozenset({"log"}),
    ("task", "depends_on"): frozenset({"task"}),
    ("task", "for"): frozenset({"decision"}),
    **{(kind, "related"): frozenset(KINDS) for kind in KINDS},
    (SETTINGS_KIND, DELIVERABLE_DOC_KEY): frozenset({"doc"}),
}


def check_workspace(workspace: Workspace) -> list[Problem]:
    """全ての問題をファイル名の順、同じファイルの中は拾った順に返す。"""
    problems = [
        *validate_workspace(workspace),
        *_check_duplicate_ids(workspace),
        *_check_refs(workspace),
        *_check_bodies(workspace),
    ]
    # ファイル名の順に並べる（sorted は安定なので、同じファイルの中は拾った順を保つ）
    return sorted(problems, key=lambda problem: problem.file)


def _check_duplicate_ids(workspace: Workspace) -> list[Problem]:
    """同じ ID を 2 つ目以降に持つ項目を `duplicate_id` にする。"""
    problems: list[Problem] = []
    seen: set[str] = set()
    for kind, spec in KINDS.items():
        for index, item in enumerate(workspace.items[kind]):
            item_id = item.get("id")
            if not isinstance(item_id, str):
                continue
            # 既に出た ID: 2 つ目以降の項目を問題にする
            if item_id in seen:
                problems.append(
                    Problem(
                        kind="duplicate_id",
                        file=spec.file,
                        id=item_id,
                        key=f"items[{index}].id",
                        detail=f"ID が重複しています: {item_id}",
                    )
                )
            seen.add(item_id)
    return problems


def _check_refs(workspace: Workspace) -> list[Problem]:
    """存在しない ID と、`REF_RULES` に合わない種類の ID を指す参照を `broken_ref` にする。"""
    existing = {kind: {item.get("id") for item in workspace.items[kind]} for kind in KINDS}
    problems: list[Problem] = []
    for kind, spec in KINDS.items():
        for item in workspace.items[kind]:
            for (rule_kind, key), allowed in REF_RULES.items():
                if rule_kind != kind:
                    continue
                for ref in as_ids(item.get(key)):
                    detail = _ref_error(ref, allowed, existing)
                    if detail is not None:
                        problems.append(
                            Problem(
                                kind="broken_ref",
                                file=spec.file,
                                id=item.get("id"),
                                key=key,
                                detail=detail,
                            )
                        )
    allowed_docs = REF_RULES[(SETTINGS_KIND, DELIVERABLE_DOC_KEY)]
    for index, deliverable in enumerate(_deliverables(workspace.settings)):
        for ref in as_ids(deliverable.get("doc")):
            detail = _ref_error(ref, allowed_docs, existing)
            if detail is not None:
                problems.append(
                    Problem(
                        kind="broken_ref",
                        file=SETTINGS_FILE,
                        id=None,
                        key=f"goal.deliverables[{index}].doc",
                        detail=detail,
                    )
                )
    return problems


def _check_bodies(workspace: Workspace) -> list[Problem]:
    """指す本文が無い項目と、どこからも指されない `docs/*.md` を拾う。"""
    problems: list[Problem] = []
    referenced: set[str] = set()
    for kind, spec in KINDS.items():
        for index, item in enumerate(workspace.items[kind]):
            body = item.get("body")
            if not isinstance(body, str):
                continue
            referenced.add(body)
            # body が指す本文のファイルが無い
            if read_body(workspace, body) is None:
                problems.append(
                    Problem(
                        kind="missing_body",
                        file=spec.file,
                        id=item.get("id"),
                        key=f"items[{index}].body",
                        detail=f"本文がありません: {BODY_DIR}/{body}",
                    )
                )
    body_dir = workspace.root / BODY_DIR
    # どの項目の body にも無い本文は、どこからも指されていない
    for path in sorted(body_dir.glob("*.md")) if body_dir.is_dir() else []:
        if path.name not in referenced:
            problems.append(
                Problem(
                    kind="orphan_body",
                    file=f"{BODY_DIR}/{path.name}",
                    id=None,
                    key=None,
                    detail="どの項目の body からも指されていません",
                )
            )
    return problems


def _ref_error(ref: str, allowed: frozenset[str], existing: dict[str, set[Any]]) -> str | None:
    """参照が指してはいけない種類か、存在しない ID なら理由を返す（正しければ None）。"""
    ref_kind = kind_of_id(ref)
    # 指してよい種類でない
    if ref_kind is None or ref_kind not in allowed:
        return f"指してはいけない種類: {ref}"
    # その種類に ID が無い
    if ref not in existing[ref_kind]:
        return f"存在しない ID: {ref}"
    return None


def _deliverables(settings: dict[str, Any]) -> list[dict[str, Any]]:
    """設定のゴールの成果物のうち、辞書のものを取り出す。"""
    goal = settings.get("goal")
    deliverables = goal.get("deliverables") if isinstance(goal, dict) else None
    if not isinstance(deliverables, list):
        return []
    return [deliverable for deliverable in deliverables if isinstance(deliverable, dict)]
