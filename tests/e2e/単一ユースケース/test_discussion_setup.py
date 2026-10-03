"""話し合いのセットアップ（利用者が依存を確かめ、新しいワークスペースを作るか既存の続きを選ぶ）のうち、版の比較の E2E テスト。

モデルを呼ばず、スキルの手順が連ねるコマンドを決めた引数で順に再生して、ワークスペースの状態を確かめる。
"""

from __future__ import annotations

import json

from workspace_fixtures import MakeLegacyWorkspace, MakeWorkspace, RunMindmap, SnapshotTree

# ワークスペースの版を持つファイルの名前
VERSION_FILE = "mindstella-version.ini"

# 版が新しいワークスペースに書く版
NEWER_VERSION = "v99.0.0"


def test_normal_when_older_version(
    make_legacy_workspace: MakeLegacyWorkspace,
    run_mindmap: RunMindmap,
    python_path: str,
    snapshot_tree: SnapshotTree,
) -> None:
    """版が古いワークスペースでは、状況を示さず、移し替えのスキルを案内して止まる（正常系）。"""
    # 準備
    root = make_legacy_workspace(legacy_docs={"A-1": True})
    before = snapshot_tree(root)
    # 実行
    # 手順が連ねるのは版の比較までで、status は呼ばない
    plan = run_mindmap("migrate", "--workspace", str(root), "--plan", python=python_path)
    # 検証
    # 版の比較が、ワークスペースの版を「版を記録する前の形式」、プラグインより古いと返す
    assert plan.returncode == 0
    payload = json.loads(plan.stdout)
    assert payload["workspace_version"] is None
    assert payload["relation"] == "older"
    # ワークスペースの全てのファイルの中身が、呼ぶ前と同じである
    assert snapshot_tree(root) == before


def test_error_when_newer_version(
    make_workspace: MakeWorkspace,
    run_mindmap: RunMindmap,
    python_path: str,
    snapshot_tree: SnapshotTree,
) -> None:
    """版が新しいワークスペースでは、状況を示さず、プラグインを更新するよう案内して止まる（異常系）。"""
    # 準備
    root = make_workspace(raw_files={VERSION_FILE: f"{NEWER_VERSION}\n"})
    before = snapshot_tree(root)
    # 実行
    # 手順が連ねるのは版の比較までで、status は呼ばない
    plan = run_mindmap("migrate", "--workspace", str(root), "--plan", python=python_path)
    # 検証
    # 版の比較が、ワークスペースの版がプラグインより新しいと返す
    assert plan.returncode == 0
    assert json.loads(plan.stdout)["relation"] == "newer"
    # ワークスペースの全てのファイルの中身が、呼ぶ前と同じである
    assert snapshot_tree(root) == before
