"""migrate（記録の形式の移行）の結合テスト。"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import yaml

from .fixture_types import (
    MakeItem,
    MakeLegacyWorkspace,
    MakeWorkspace,
    RunMindmap,
    SnapshotTree,
)

# プラグインの版（plugins/mindstella/version.ini の 1 行目）
PLUGIN_VERSION = "v0.3.0"

# ワークスペースの版を持つファイルの名前
VERSION_FILE = "mindstella-version.ini"

# 渡す題名
SUMMARY = "要件出しのスキルを設計する"

# 手順が読めない docs.yaml（閉じていないフローの配列）
BROKEN_DOCS = "items: [\n"

# 版が新しいワークスペースに書く版
NEWER_VERSION = "v99.0.0"


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


def _git(cwd: Path, *args: str) -> str:
    """cwd で git を呼び、標準出力を返す。失敗したら例外にする。"""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout


def _init_git(path: Path) -> None:
    """フォルダを git の作業ツリーにし、コミットに要る作者をそのリポジトリの設定に置く。"""
    _git(path, "init", "-q")
    _git(path, "config", "user.name", "テスト")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "commit.gpgsign", "false")


def _create_current_workspace(
    tmp_path: Path, run_mindmap: RunMindmap, valid_settings: dict[str, Any]
) -> Path:
    """init で今の版のワークスペースを作り、そのフォルダを返す。"""
    root = tmp_path / "current"
    result = run_mindmap(
        "init",
        "--workspace",
        str(root),
        stdin=json.dumps(valid_settings, ensure_ascii=False),
    )
    assert result.returncode == 0
    return root


def test_normal_when_plan(
    make_legacy_workspace: MakeLegacyWorkspace,
    run_mindmap: RunMindmap,
    snapshot_tree: SnapshotTree,
) -> None:
    """版を記録する前の形式に v0.3.0 の手順と値が要るキーを並べる（正常系）。"""
    # 準備
    root = make_legacy_workspace(legacy_docs={"A-1": True}, without_summary=True)
    before = snapshot_tree(root)
    mtimes = _mtimes(root)
    # 実行
    result = run_mindmap("migrate", "--workspace", str(root), "--plan")
    # 検証
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["workspace_version"] is None
    assert payload["plugin_version"] == PLUGIN_VERSION
    assert payload["relation"] == "older"
    assert payload["steps"] != []
    assert all(step["version"] == PLUGIN_VERSION for step in payload["steps"])
    assert all(step["destructive"] is False for step in payload["steps"])
    assert {"file": "mindmap.yaml", "key": "summary"} in [
        {"file": value["file"], "key": value["key"]} for value in payload["needs_values"]
    ]
    assert snapshot_tree(root) == before
    assert _mtimes(root) == mtimes


def test_normal_when_apply(
    make_legacy_workspace: MakeLegacyWorkspace, run_mindmap: RunMindmap
) -> None:
    """写しを取って v0.3.0 の手順を当て、版のファイルは書かない（正常系）。"""
    # 準備
    root = make_legacy_workspace(legacy_docs={"A-1": True, "A-2": False}, without_summary=True)
    before = {item["id"]: item for item in _read_docs(root)}
    docs_before = (root / "docs.yaml").read_bytes()
    # 実行
    result = run_mindmap("migrate", "--workspace", str(root))
    # 検証
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    after = {item["id"]: item for item in _read_docs(root)}
    assert after["A-1"]["status"] == "完成"
    assert after["A-2"]["status"] == "下書き"
    assert "done" not in after["A-1"]
    assert "done" not in after["A-2"]
    assert after["A-1"]["updated"] == before["A-1"]["updated"]
    assert after["A-2"]["updated"] == before["A-2"]["updated"]
    assert {"file": "mindmap.yaml", "key": "summary"} in [
        {"file": value["file"], "key": value["key"]} for value in payload["needs_values"]
    ]
    assert payload["backup"]["kind"] == "copy"
    assert (Path(payload["backup"]["ref"]) / "docs.yaml").read_bytes() == docs_before
    assert not (root / VERSION_FILE).exists()


def test_normal_when_backup_git(
    tmp_path: Path,
    make_legacy_workspace: MakeLegacyWorkspace,
    run_mindmap: RunMindmap,
) -> None:
    """git の作業ツリーの中のワークスペースでは、ワークスペースのパスだけをコミットして写しにする（正常系）。"""
    # 準備
    root = make_legacy_workspace(legacy_docs={"A-1": True}, without_summary=True)
    # ワークスペースの親を作業ツリーにし、外のファイルはどちらもコミットしない
    _init_git(tmp_path)
    (tmp_path / "other.txt").write_text("外のファイル\n", encoding="utf-8")
    (tmp_path / "staged.txt").write_text("ステージしたファイル\n", encoding="utf-8")
    _git(tmp_path, "add", "staged.txt")
    # 実行
    result = run_mindmap("migrate", "--workspace", str(root))
    # 検証
    assert result.returncode == 0
    backup = json.loads(result.stdout)["backup"]
    assert backup["kind"] == "git"
    committed = _git(tmp_path, "show", "--name-only", "--pretty=format:", backup["ref"]).split()
    assert committed != []
    assert all(name.startswith(f"{root.name}/") for name in committed)
    assert _git(tmp_path, "diff", "--cached", "--name-only").split() == ["staged.txt"]


def test_normal_when_set(
    make_legacy_workspace: MakeLegacyWorkspace, run_mindmap: RunMindmap
) -> None:
    """--set で値が要るキーに値を入れる（正常系）。"""
    # 準備
    root = make_legacy_workspace(without_summary=True)
    # 実行
    result = run_mindmap(
        "migrate", "--workspace", str(root), "--set", f"mindmap.yaml:summary={SUMMARY}"
    )
    # 検証
    assert result.returncode == 0
    settings = yaml.safe_load((root / "mindmap.yaml").read_text(encoding="utf-8"))
    assert settings["summary"] == SUMMARY
    assert not (root / VERSION_FILE).exists()


def test_normal_when_record(
    make_workspace: MakeWorkspace, make_item: MakeItem, run_mindmap: RunMindmap
) -> None:
    """点検に合うワークスペースで --record が版のファイルを書く（正常系）。"""
    # 準備
    root = make_workspace(make_item("A-1", status="完成"))
    # 実行
    result = run_mindmap("migrate", "--workspace", str(root), "--record")
    # 検証
    assert result.returncode == 0
    assert json.loads(result.stdout)["recorded"] == PLUGIN_VERSION
    first_line = (root / VERSION_FILE).read_text(encoding="utf-8").splitlines()[0]
    assert first_line == PLUGIN_VERSION


def test_normal_when_same(
    tmp_path: Path, run_mindmap: RunMindmap, valid_settings: dict[str, Any]
) -> None:
    """今の版のワークスペースでは並べる手順が無い（正常系）。"""
    # 準備
    root = _create_current_workspace(tmp_path, run_mindmap, valid_settings)
    # 実行
    result = run_mindmap("migrate", "--workspace", str(root), "--plan")
    # 検証
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["relation"] == "same"
    assert payload["steps"] == []
    assert payload["needs_values"] == []


def test_normal_when_plan_newer(
    tmp_path: Path, run_mindmap: RunMindmap, valid_settings: dict[str, Any]
) -> None:
    """版が新しいワークスペースでも --plan はエラーにせず newer を返す（正常系）。"""
    # 準備
    root = _create_current_workspace(tmp_path, run_mindmap, valid_settings)
    (root / VERSION_FILE).write_text(f"{NEWER_VERSION}\n", encoding="utf-8")
    # 実行
    result = run_mindmap("migrate", "--workspace", str(root), "--plan")
    # 検証
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["workspace_version"] == NEWER_VERSION
    assert payload["relation"] == "newer"
    assert payload["steps"] == []


def test_normal_when_backup_ignored(
    tmp_path: Path,
    make_legacy_workspace: MakeLegacyWorkspace,
    run_mindmap: RunMindmap,
) -> None:
    """git の作業ツリーの中でも、ignore されたファイルを持つワークスペースは複製で写しを取る（正常系）。"""
    # 準備
    root = make_legacy_workspace(legacy_docs={"A-1": True}, without_summary=True)
    _init_git(tmp_path)
    (tmp_path / ".gitignore").write_text("*\n", encoding="utf-8")
    # 実行
    result = run_mindmap("migrate", "--workspace", str(root))
    # 検証
    assert result.returncode == 0
    backup = json.loads(result.stdout)["backup"]
    assert backup["kind"] == "copy"
    assert (Path(backup["ref"]) / "docs.yaml").exists()
    assert _git(tmp_path, "rev-list", "--all", "--count").strip() == "0"


def test_normal_when_already_current(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    run_mindmap: RunMindmap,
    snapshot_tree: SnapshotTree,
) -> None:
    """v0.2.0 で作った形に当てても、何も変えずに成功する（正常系）。"""
    # 準備
    root = make_workspace(make_item("A-1", status="完成"))
    before = snapshot_tree(root)
    mtimes = _mtimes(root)
    # 実行
    result = run_mindmap("migrate", "--workspace", str(root))
    # 検証
    assert result.returncode == 0
    assert json.loads(result.stdout)["needs_values"] == []
    assert snapshot_tree(root) == before
    assert _mtimes(root) == mtimes


def test_error_when_newer(
    tmp_path: Path,
    run_mindmap: RunMindmap,
    valid_settings: dict[str, Any],
    snapshot_tree: SnapshotTree,
) -> None:
    """版が新しいワークスペースには手順を当てない（異常系）。"""
    # 準備
    root = _create_current_workspace(tmp_path, run_mindmap, valid_settings)
    (root / VERSION_FILE).write_text(f"{NEWER_VERSION}\n", encoding="utf-8")
    before = snapshot_tree(root)
    # 実行
    result = run_mindmap("migrate", "--workspace", str(root))
    # 検証
    assert result.returncode == 1
    assert NEWER_VERSION in result.stderr
    assert PLUGIN_VERSION in result.stderr
    assert snapshot_tree(root) == before
    assert list(root.parent.glob(f"{root.name}.before-*")) == []


def test_error_when_step_fails(
    make_workspace: MakeWorkspace, run_mindmap: RunMindmap, snapshot_tree: SnapshotTree
) -> None:
    """手順が読めないファイルに当たると、写しから戻して終わる（異常系）。"""
    # 準備
    root = make_workspace(raw_files={"docs.yaml": BROKEN_DOCS})
    before = snapshot_tree(root)
    # 実行
    result = run_mindmap("migrate", "--workspace", str(root))
    # 検証
    assert result.returncode == 1
    assert result.stderr.startswith(f"エラー: {PLUGIN_VERSION} の手順 ")
    assert "docs.yaml" in result.stderr
    assert "Traceback" not in result.stderr
    assert snapshot_tree(root) == before
    assert not (root / VERSION_FILE).exists()


def test_error_when_schema_mismatch(
    make_legacy_workspace: MakeLegacyWorkspace,
    run_mindmap: RunMindmap,
    snapshot_tree: SnapshotTree,
) -> None:
    """値が要るキーが無いままでは、版を書かない（異常系）。"""
    # 準備
    root = make_legacy_workspace(without_summary=True)
    before = snapshot_tree(root)
    # 実行
    result = run_mindmap("migrate", "--workspace", str(root), "--record")
    # 検証
    assert result.returncode == 1
    assert any(
        line.startswith("mindmap.yaml: ") and "summary" in line
        for line in result.stderr.splitlines()
    )
    assert snapshot_tree(root) == before
    assert not (root / VERSION_FILE).exists()


def test_error_when_workspace_not_found(
    tmp_path: Path, run_mindmap: RunMindmap, snapshot_tree: SnapshotTree
) -> None:
    """mindmap.yaml が無いフォルダを指すと、何も書かずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = run_mindmap("migrate", "--workspace", str(root), "--plan")
    # 検証
    assert result.returncode == 1
    assert str(root) in result.stderr
    assert snapshot_tree(root) == {}
