"""ワークスペースの移し替え（利用者がプラグインを上げた後、ワークスペースを今の版へ移し替える）の E2E テスト。

モデルを呼ばず、スキルの手順が連ねるコマンドを決めた引数で順に再生して、ワークスペースの状態を確かめる。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from workspace_fixtures import (
    REPO_ROOT,
    MakeLegacyWorkspace,
    MakeWorkspace,
    RunMindmap,
    SnapshotTree,
)

# ワークスペースの版を持つファイルの名前
VERSION_FILE = "mindstella-version.ini"

# 点検で聞かれる題名に利用者が答える内容
SUMMARY = "要件出しのスキルを設計する"

# 版が新しいワークスペースに書く版
NEWER_VERSION = "v99.0.0"

# 手順が読めない docs.yaml（閉じていないフローの配列）
BROKEN_DOCS = "items: [\n"


def _plugin_version() -> str:
    """プラグインの版（`plugins/mindstella/version.ini` の 1 行目）を返す。"""
    path = REPO_ROOT / "plugins" / "mindstella" / "version.ini"
    return path.read_text(encoding="utf-8").splitlines()[0]


def _read_docs(root: Path) -> list[dict[str, Any]]:
    """ワークスペースの資料の並びを読む。"""
    return yaml.safe_load((root / "docs.yaml").read_text(encoding="utf-8"))["items"]


def _mtimes(root: Path) -> dict[str, int]:
    """フォルダの下の全てのファイルの更新日時（ナノ秒）を、相対パス → 更新日時で返す。"""
    return {
        path.relative_to(root).as_posix(): path.stat().st_mtime_ns
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


@pytest.fixture
def current_workspace(
    tmp_path: Path, run_mindmap: RunMindmap, valid_settings: dict[str, Any]
) -> Path:
    """`init` で作り、資料 A-1（status: 完成）を足した今の版のワークスペースを返す。"""
    root = tmp_path / "current"
    created = run_mindmap(
        "init", "--workspace", str(root), stdin=json.dumps(valid_settings, ensure_ascii=False)
    )
    assert created.returncode == 0
    doc = {"title": "資料", "kind": "図", "deliverable": False, "status": "完成"}
    added = run_mindmap(
        "add",
        "doc",
        "--workspace",
        str(root),
        stdin=json.dumps({**doc, "body_markdown": "本文\n"}, ensure_ascii=False),
    )
    assert added.returncode == 0
    return root


def test_normal(
    make_legacy_workspace: MakeLegacyWorkspace, run_mindmap: RunMindmap, python_path: str
) -> None:
    """版が古いワークスペースを、手順の一覧・写し・当てる・題名の入力・版の書き換えの順で今の版へ移し替える（正常系）。"""
    # 準備
    root = make_legacy_workspace(legacy_docs={"A-1": True, "A-2": False}, without_summary=True)
    updated_before = {item["id"]: item["updated"] for item in _read_docs(root)}
    ws = ["--workspace", str(root)]
    # 実行
    # 版を比べ、当てる手順を並べる
    plan = run_mindmap("migrate", *ws, "--plan", python=python_path)
    # 写しを取って手順を当てる
    applied = run_mindmap("migrate", *ws, python=python_path)
    # 点検し、値が要るキー（題名）だけを利用者に聞いて入れる
    checked_before_set = run_mindmap("check", *ws, python=python_path)
    set_summary = run_mindmap(
        "migrate", *ws, "--set", f"mindmap.yaml:summary={SUMMARY}", python=python_path
    )
    # 版を書き換える
    recorded = run_mindmap("migrate", *ws, "--record", python=python_path)
    checked = run_mindmap("check", *ws, python=python_path)
    # 検証
    assert plan.returncode == 0
    assert json.loads(plan.stdout)["relation"] == "older"
    assert applied.returncode == 0
    assert json.loads(applied.stdout)["backup"]["kind"] == "copy"
    assert checked_before_set.returncode == 1
    assert set_summary.returncode == 0
    assert recorded.returncode == 0
    # mindstella-version.ini の 1 行目がプラグインの版である
    first_line = (root / VERSION_FILE).read_text(encoding="utf-8").splitlines()[0]
    assert first_line == _plugin_version()
    # docs.yaml の A-1 が status: 完成、A-2 が status: 下書きで、どちらも done を持たず、updated が呼ぶ前と同じである
    docs = {item["id"]: item for item in _read_docs(root)}
    assert docs["A-1"]["status"] == "完成"
    assert docs["A-2"]["status"] == "下書き"
    assert "done" not in docs["A-1"]
    assert "done" not in docs["A-2"]
    assert {doc_id: doc["updated"] for doc_id, doc in docs.items()} == updated_before
    # mindmap.yaml の summary が答えた題名である
    settings = yaml.safe_load((root / "mindmap.yaml").read_text(encoding="utf-8"))
    assert settings["summary"] == SUMMARY
    # check が問題を 0 件で返す
    assert checked.returncode == 0
    assert json.loads(checked.stdout) == {"ok": True, "problems": []}


def test_normal_when_same_version(
    current_workspace: Path,
    run_mindmap: RunMindmap,
    python_path: str,
    snapshot_tree: SnapshotTree,
) -> None:
    """今の版のワークスペースでは、移し替えるものが無いと返る（正常系）。"""
    # 準備
    before = snapshot_tree(current_workspace)
    mtimes = _mtimes(current_workspace)
    # 実行
    plan = run_mindmap(
        "migrate", "--workspace", str(current_workspace), "--plan", python=python_path
    )
    # 検証
    # 版の比較が、版が同じで当てる手順が空だと返す
    assert plan.returncode == 0
    payload = json.loads(plan.stdout)
    assert payload["relation"] == "same"
    assert payload["steps"] == []
    # ワークスペースの全てのファイルの中身と更新日時が、呼ぶ前と同じである
    assert snapshot_tree(current_workspace) == before
    assert _mtimes(current_workspace) == mtimes


def test_error_when_step_fails(
    make_workspace: MakeWorkspace,
    run_mindmap: RunMindmap,
    python_path: str,
    snapshot_tree: SnapshotTree,
) -> None:
    """手順を当てる途中で失敗すると、写しから戻して、失敗した版・手順・理由を返す（異常系）。"""
    # 準備
    root = make_workspace(raw_files={"docs.yaml": BROKEN_DOCS})
    before = snapshot_tree(root)
    ws = ["--workspace", str(root)]
    # 実行
    plan = run_mindmap("migrate", *ws, "--plan", python=python_path)
    applied = run_mindmap("migrate", *ws, python=python_path)
    # 検証
    assert plan.returncode == 0
    # 手順を当てるコマンドが終了コード 1 で終わり、出力に失敗した版・手順・docs.yaml を読めない理由がある
    assert applied.returncode == 1
    assert applied.stderr.startswith(f"エラー: {_plugin_version()} の手順 ")
    assert "docs.yaml" in applied.stderr
    assert "Traceback" not in applied.stderr
    # ワークスペースの全てのファイルの中身が、呼ぶ前と同じである
    assert snapshot_tree(root) == before
    # mindstella-version.ini が無いままである
    assert not (root / VERSION_FILE).exists()


def test_error_when_workspace_newer(
    current_workspace: Path,
    run_mindmap: RunMindmap,
    python_path: str,
    snapshot_tree: SnapshotTree,
) -> None:
    """版が新しいワークスペースでは、プラグインを更新するよう案内される（異常系）。"""
    # 準備
    (current_workspace / VERSION_FILE).write_text(f"{NEWER_VERSION}\n", encoding="utf-8")
    before = snapshot_tree(current_workspace)
    # 実行
    plan = run_mindmap(
        "migrate", "--workspace", str(current_workspace), "--plan", python=python_path
    )
    # 検証
    # 版の比較が、ワークスペースの版がプラグインより新しいと返す
    assert plan.returncode == 0
    payload = json.loads(plan.stdout)
    assert payload["workspace_version"] == NEWER_VERSION
    assert payload["relation"] == "newer"
    # ワークスペースの全てのファイルの中身が、呼ぶ前と同じである
    assert snapshot_tree(current_workspace) == before


def test_error_when_session_on_older_workspace(
    make_legacy_workspace: MakeLegacyWorkspace,
    run_mindmap: RunMindmap,
    python_path: str,
    snapshot_tree: SnapshotTree,
) -> None:
    """話し合いを進めるスキルを版が古いワークスペースへ呼ぶと、移し替えるよう案内される（異常系）。"""
    # 準備
    root = make_legacy_workspace(legacy_docs={"A-1": True})
    before = snapshot_tree(root)
    # 実行
    plan = run_mindmap("migrate", "--workspace", str(root), "--plan", python=python_path)
    # 検証
    # 版の比較が、ワークスペースの版がプラグインより古いと返す
    assert plan.returncode == 0
    assert json.loads(plan.stdout)["relation"] == "older"
    # ワークスペースの全てのファイルの中身が、呼ぶ前と同じである
    assert snapshot_tree(root) == before


def test_error_when_session_on_newer_workspace(
    current_workspace: Path,
    run_mindmap: RunMindmap,
    python_path: str,
    snapshot_tree: SnapshotTree,
) -> None:
    """話し合いを進めるスキルを版が新しいワークスペースへ呼ぶと、プラグインを更新するよう案内される（異常系）。"""
    # 準備
    (current_workspace / VERSION_FILE).write_text(f"{NEWER_VERSION}\n", encoding="utf-8")
    before = snapshot_tree(current_workspace)
    # 実行
    plan = run_mindmap(
        "migrate", "--workspace", str(current_workspace), "--plan", python=python_path
    )
    # 検証
    # 版の比較が、ワークスペースの版がプラグインより新しいと返す
    assert plan.returncode == 0
    assert json.loads(plan.stdout)["relation"] == "newer"
    # ワークスペースの全てのファイルの中身が、呼ぶ前と同じである
    assert snapshot_tree(current_workspace) == before
