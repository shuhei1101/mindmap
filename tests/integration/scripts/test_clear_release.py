"""clear-release（リリースの片付け）の結合テスト。"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .fixture_types import LockDirs, MakeWorkspace, RunMindmap, SnapshotTree


def test_normal(
    make_workspace: MakeWorkspace, run_mindmap: RunMindmap, snapshot_tree: SnapshotTree
) -> None:
    """release/ の中身を消し、消したものを名前の順に返す（正常系）。"""
    # 準備
    root = make_workspace()
    (root / "release" / "古い資料.md").write_text("古い\n", encoding="utf-8")
    (root / "release" / "図").mkdir()
    (root / "release" / "図" / "構成.md").write_text("図\n", encoding="utf-8")
    # release/ の外のファイルの写し
    outside_before = {
        name: content
        for name, content in snapshot_tree(root).items()
        if not name.startswith("release/")
    }
    # 実行
    result = run_mindmap("clear-release", "--workspace", str(root))
    # 検証
    assert result.returncode == 0
    assert json.loads(result.stdout) == {"removed": ["古い資料.md", "図/"]}
    assert (root / "release").is_dir()
    assert list((root / "release").iterdir()) == []
    assert snapshot_tree(root) == outside_before


def test_normal_when_release_dir_missing(
    make_workspace: MakeWorkspace, run_mindmap: RunMindmap, snapshot_tree: SnapshotTree
) -> None:
    """release/ が無ければ空の release/ を作り、前の版の handoff/ は触らない（正常系）。"""
    # 準備
    root = make_workspace()
    shutil.rmtree(root / "release")
    (root / "handoff").mkdir()
    (root / "handoff" / "資料.md").write_text("前の版の資料\n", encoding="utf-8")
    handoff_before = snapshot_tree(root / "handoff")
    # 実行
    result = run_mindmap("clear-release", "--workspace", str(root))
    # 検証
    assert result.returncode == 0
    assert json.loads(result.stdout) == {"removed": []}
    assert (root / "release").is_dir()
    assert list((root / "release").iterdir()) == []
    assert snapshot_tree(root / "handoff") == handoff_before


def test_error_when_workspace_not_found(tmp_path: Path, run_mindmap: RunMindmap) -> None:
    """mindmap.yaml が無いフォルダを指すと、何も消さずにエラーで終わる（異常系）。"""
    # 準備
    (tmp_path / "release").mkdir()
    (tmp_path / "release" / "資料.md").write_text("資料\n", encoding="utf-8")
    # 実行
    result = run_mindmap("clear-release", "--workspace", str(tmp_path))
    # 検証
    assert result.returncode == 1
    assert str(tmp_path) in result.stderr
    assert (tmp_path / "release" / "資料.md").read_text(encoding="utf-8") == "資料\n"


def test_error_when_remove_fails(
    make_workspace: MakeWorkspace, run_mindmap: RunMindmap, lock_dirs: LockDirs
) -> None:
    """消せないものに当たった時点でエラーで終わり、それまでに消したものは消えたままになる（異常系）。"""
    # 準備
    root = make_workspace()
    (root / "release" / "一.md").write_text("一\n", encoding="utf-8")
    # 二.md は中のファイルを消せないフォルダにする（名前の順に消すので、一.md の後で止まる）
    stuck = root / "release" / "二.md"
    stuck.mkdir()
    (stuck / "中.md").write_text("中\n", encoding="utf-8")
    lock_dirs(stuck)
    # 実行
    result = run_mindmap("clear-release", "--workspace", str(root))
    # 検証
    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.startswith("エラー: ")
    assert str(stuck) in result.stderr
    assert "Traceback" not in result.stderr
    assert stuck.exists()
    assert not (root / "release" / "一.md").exists()
