"""話し合いをゴールまで進める（セットアップから取り込み・ヒアリング・リサーチ・方針転換を重ね、ゴール判定で引き渡すまで）の E2E テスト。

モデルを呼ばず、スキルの手順が連ねるコマンドを決めた引数で順に再生して、ワークスペースの状態を確かめる。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from workspace_fixtures import MakeItem, MakeWorkspace, RunMindmap

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import Replay

# 話し合いの対象・カテゴリー
TARGET = "家計簿アプリ"
CATEGORY = "機能"

# 会話の日付
TODAY = "2026-10-02"

# 新しい話し合いで /mindmap:setup が決める設定（分野: システム開発、ゴール: インターフェースまで）
SETTINGS: dict[str, Any] = {
    "field": "システム開発",
    "target_label": "システム",
    "phases": ["目的", "要件", "構成", "インターフェース", "コンテンツ"],
    "targets": [{"name": TARGET, "summary": "支出を記録する"}],
    "categories": [{"name": CATEGORY, "target": TARGET, "summary": "利用者ができること"}],
    "goal": {
        "phase": "インターフェース",
        "summary": "インターフェースまで決まる",
        "deliverables": [{"title": "要件定義書", "doc": "A-1"}],
    },
    "links": [],
}


def _placed(title: str, phase: str, **keys: Any) -> dict[str, Any]:
    """対象・カテゴリー・フェーズを付けた項目の中身を作る。"""
    return {"title": title, "target": TARGET, "category": CATEGORY, "phase": phase, **keys}


def _log(title: str, related: list[str], summary: str) -> dict[str, Any]:
    """会話ログの項目の中身を作る。"""
    return {"title": title, "date": TODAY, "related": related, "body_markdown": summary}


def _newest_yaml_mtime(root: Path) -> int:
    """ワークスペースの YAML の更新時刻のうち、一番新しいものを返す。"""
    return max(path.stat().st_mtime_ns for path in root.glob("*.yaml"))


def test_normal_when_new_discussion(
    tmp_path: Path,
    replay: Replay,
    run_mindmap: RunMindmap,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """セットアップから、取り込み・ヒアリング・リサーチ・方針転換・ゴール判定を通してゴールまで進める（正常系）。"""
    # 準備
    root = tmp_path / "workspace"
    ws = ["--workspace", str(root)]

    # 実行
    # セットアップ: 新しいワークスペースを作る
    replay("init", *ws, data=SETTINGS)
    replay("build", *ws)
    # 取り込み: 決め事・派生の検討事項・タスク・会話ログを積む
    replay(
        "add",
        "decision",
        *ws,
        data=_placed(
            "保存先を決める",
            "構成",
            status="決定済み",
            answer="YAML ファイルに保存する",
            reason="手で読める",
            options=[
                {"key": "A", "content": "YAML ファイルに保存する", "adopted": True},
                {"key": "B", "content": "DB に保存する"},
            ],
        ),
    )
    replay(
        "add",
        "decision",
        *ws,
        data=_placed(
            "保存先のファイル分け",
            "インターフェース",
            status="未決定",
            parent="D-1",
            depends_on=["D-1"],
        ),
    )
    replay(
        "add",
        "task",
        *ws,
        data=_placed(
            "保存先の候補を調べる", "構成", kind="調査", status="未着手", **{"for": ["D-1"]}
        ),
    )
    replay("add", "log", *ws, data=_log("1 回目の会話", ["D-1", "D-2", "T-1"], "保存先を決めた"))
    replay("build", *ws)
    # ヒアリング: 前提が揃った未決定を聞いて、答えを記録する
    candidates = replay("next", *ws)["candidates"]
    replay("update", "D-2", *ws, data={"status": "決定済み", "answer": "種類ごとに分ける"})
    replay("add", "log", *ws, data=_log("ヒアリング", ["D-2"], "ファイル分けを決めた"))
    replay("build", *ws)
    # リサーチ: 調査を検討事項に繋ぎ、タスクを完了にする
    replay(
        "add",
        "research",
        *ws,
        data=_placed(
            "保存先の候補の比較",
            "構成",
            question="YAML と DB のどちらが手で直しやすいか",
            conclusion="YAML",
            confidence="高",
            angles=["可読性", "手で直せるか"],
            related=["D-1"],
        ),
    )
    replay("update", "T-1", *ws, data={"status": "完了", "result": "比較を調査 R-1 に書いた"})
    replay("add", "log", *ws, data=_log("リサーチ", ["R-1", "T-1"], "候補を比べた"))
    replay("build", *ws)
    # 方針転換: 採用する案を切り替え、影響を要見直しにして見直しのタスクを積む
    replay("adopt", "D-1", "B", *ws)
    affected = replay("impact", "D-1", *ws)["affected"]
    replay("update", "D-1", *ws, data={"answer": "DB に保存する", "reason": "検索しやすい"})
    replay("update", "D-2", *ws, data={"status": "要見直し", "reason": "保存先が DB に変わった"})
    replay(
        "add",
        "task",
        *ws,
        data=_placed(
            "ファイル分けを見直す",
            "インターフェース",
            kind="作業",
            status="未着手",
            **{"for": ["D-2"]},
        ),
    )
    replay("add", "log", *ws, data=_log("方針転換", ["D-1", "D-2", "T-2"], "保存先を DB にした"))
    replay("build", *ws)
    # 取り込み: 要見直しを決め直し、見直しのタスクを完了する
    replay(
        "update", "D-2", *ws, data={"status": "決定済み", "answer": "テーブルを種類ごとに分ける"}
    )
    replay("update", "T-2", *ws, data={"status": "完了", "result": "テーブルの分け方を決めた"})
    # 成果物の資料を作る
    replay(
        "add",
        "doc",
        *ws,
        data=_placed(
            "要件定義書",
            "要件",
            kind="文書",
            deliverable=True,
            done=True,
            body_markdown="# 要件定義書\n\n支出を DB に記録する。",
        ),
    )
    # プレビュー: 記録を書き出す
    replay("build", *ws)
    # ゴール判定: 届いたかを確かめ、確定の後に handoff/ へ書き出す
    goal = replay("goal", *ws)
    deliverable = replay("show", "A-1", *ws)
    (root / "handoff" / "決定事項.md").write_text(
        "# 決定事項\n\n- D-1: DB に保存する\n- D-2: テーブルを種類ごとに分ける\n", encoding="utf-8"
    )
    (root / "handoff" / "要件定義書.md").write_text(deliverable["body_markdown"], encoding="utf-8")
    replay("add", "log", *ws, data=_log("ゴール判定", ["A-1"], "ゴールに届いたので引き渡した"))
    replay("build", *ws)
    checked = run_mindmap("check", *ws)

    # 検証
    # mindmap.yaml に、分野・最上位の軸の呼び名・フェーズ・カテゴリー・ゴールが入っている
    settings = read_yaml(root, "mindmap.yaml")
    assert settings["field"] == "システム開発"
    assert settings["target_label"] == "システム"
    assert settings["phases"] == SETTINGS["phases"]
    assert settings["categories"][0]["name"] == CATEGORY
    assert settings["goal"]["phase"] == "インターフェース"
    # 取り込みで足した検討事項・派生の検討事項（parent を持つ）・タスク・会話ログがある
    decisions = {item["id"]: item for item in read_yaml(root, "decisions.yaml")["items"]}
    tasks = {item["id"]: item for item in read_yaml(root, "tasks.yaml")["items"]}
    assert decisions["D-2"]["parent"] == "D-1"
    assert tasks["T-1"]["for"] == ["D-1"]
    assert len(read_yaml(root, "logs.yaml")["items"]) == 5
    # ヒアリングで聞いた候補は D-2 だけだった
    assert [candidate["id"] for candidate in candidates] == ["D-2"]
    # リサーチで足した調査が、元の検討事項と related でつながっている
    assert read_yaml(root, "research.yaml")["items"][0]["related"] == ["D-1"]
    # D-1 の採用する案が B で、D-2 が決め直されて決定済み、D-2 の見直しのタスクが完了である
    adopted = [option["key"] for option in decisions["D-1"]["options"] if option.get("adopted")]
    assert adopted == ["B"]
    assert [item["id"] for item in affected] == ["D-2", "T-1"]
    assert decisions["D-2"]["status"] == "決定済み"
    assert tasks["T-2"]["status"] == "完了"
    # goal の出力が「届いた」である
    assert goal["reached"] is True
    assert goal["remaining_decisions"] == []
    assert goal["remaining_deliverables"] == []
    # handoff/ に、確定した検討事項と成果物の資料が書き出されている
    assert "D-2" in (root / "handoff" / "決定事項.md").read_text(encoding="utf-8")
    assert "支出を DB に記録する" in (root / "handoff" / "要件定義書.md").read_text(
        encoding="utf-8"
    )
    # check が参照切れと、YAML と Markdown のずれを 0 件で返す
    assert checked.returncode == 0
    assert json.loads(checked.stdout)["problems"] == []
    # preview.html が最後の編集より後に書き出されている
    assert (root / "preview.html").stat().st_mtime_ns >= _newest_yaml_mtime(root)


def test_normal_when_resume(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    replay: Replay,
    read_yaml: Callable[[Path, str], Any],
) -> None:
    """途中まで進んだワークスペースの状況を読み、続きの番号で項目を足す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1", title="見直しの問い", status="要見直し"),
        make_item("T-1", title="進めている作業", status="進行中"),
        make_item("D-2", title="次に決める問い"),
    )
    ws = ["--workspace", str(root)]
    # 実行
    # セットアップ: 既存のワークスペースの状況を読む
    status = replay("status", *ws)
    # 取り込み: 続きの番号で検討事項を足す
    added = replay("add", "decision", *ws, data={"title": "続きで出た問い", "status": "未決定"})
    # 検証
    # status の出力に、要見直しの D-1・進行中の T-1・次の候補の D-2 がある
    assert status["needs_review"] == [{"id": "D-1", "title": "見直しの問い"}]
    assert status["in_progress"] == [{"id": "T-1", "title": "進めている作業"}]
    assert status["next"][0]["id"] == "D-2"
    # 既存の項目の ID が変わらず、取り込みで足した検討事項が D-3 になっている
    assert added["id"] == "D-3"
    ids = [item["id"] for item in read_yaml(root, "decisions.yaml")["items"]]
    assert ids == ["D-1", "D-2", "D-3"]
