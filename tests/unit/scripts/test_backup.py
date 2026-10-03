"""backup.py（写しの取り方と戻し方）の単体テスト。git は一時フォルダの作業ツリーで実際に呼ぶ。"""

from __future__ import annotations

from pathlib import Path

import pytest

import backup
from fixture_types import MakeItem, MakeWorkspace, SnapshotTree
from migration_helpers import init_git_repo, run_git
from versions import Version

# 移し替える先の版
TARGET_VERSION = Version(0, 3, 0)


@pytest.fixture
def git_workspace(tmp_path: Path, make_workspace: MakeWorkspace, make_item: MakeItem) -> Path:
    """git の作業ツリー（repo/）の中の ws/ にワークスペースを置く。外のファイルは other.txt と、add 済みの staged.txt。"""
    # ワークスペースを作ってから、その親を作業ツリーにする
    root = make_workspace(make_item("A-1"), name="repo/ws")
    repo = tmp_path / "repo"
    init_git_repo(repo)
    # ワークスペースの外のファイルは、どちらもコミットしない
    (repo / "other.txt").write_text("外のファイル\n", encoding="utf-8")
    (repo / "staged.txt").write_text("ステージしたファイル\n", encoding="utf-8")
    run_git(repo, "add", "staged.txt")
    return root


@pytest.fixture
def ignored_workspace(tmp_path: Path, make_workspace: MakeWorkspace, make_item: MakeItem) -> Path:
    """全てを ignore する tmp/.gitignore を持つ作業ツリーの、tmp/ws/ にワークスペースを置く。"""
    root = make_workspace(make_item("A-1"), name="repo/tmp/ws")
    repo = tmp_path / "repo"
    init_git_repo(repo)
    (repo / "tmp" / ".gitignore").write_text("*\n", encoding="utf-8")
    return root


def test_take_backup_when_not_git(
    make_workspace: MakeWorkspace, make_item: MakeItem, snapshot_tree: SnapshotTree
) -> None:
    """git の外ではフォルダを複製する（正常系）。"""
    # 準備
    root = make_workspace(make_item("A-1"))
    # 実行
    result = backup.take_backup(root, TARGET_VERSION)
    # 検証
    assert result.kind == "copy"
    assert Path(result.ref) == root.parent / "workspace.before-v0.3.0"
    assert snapshot_tree(Path(result.ref)) == snapshot_tree(root)


def test_take_backup_when_git(git_workspace: Path) -> None:
    """ワークスペースのパスだけをコミットする（正常系）。"""
    # 準備
    repo = git_workspace.parent
    # 実行
    result = backup.take_backup(git_workspace, TARGET_VERSION)
    # 検証
    assert result.kind == "git"
    committed = run_git(repo, "show", "--name-only", "--pretty=format:", result.ref).split()
    assert committed != []
    assert all(name.startswith("ws/") for name in committed)
    # ワークスペースの外のステージは、ステージされたまま残る
    assert run_git(repo, "diff", "--cached", "--name-only").split() == ["staged.txt"]


def test_take_backup_when_ignored(ignored_workspace: Path) -> None:
    """ignore されたファイルがあれば複製する（正常系）。"""
    # 準備
    repo = ignored_workspace.parents[1]
    # 実行
    result = backup.take_backup(ignored_workspace, TARGET_VERSION)
    # 検証
    assert result.kind == "copy"
    assert run_git(repo, "rev-list", "--all", "--count").strip() == "0"


def test_take_backup_when_copy_exists(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """同じ名前の写しがあれば日時を足す（正常系）。"""
    # 準備
    root = make_workspace(make_item("A-1"))
    existing = root.parent / "workspace.before-v0.3.0"
    existing.mkdir()
    # 実行
    result = backup.take_backup(root, TARGET_VERSION)
    # 検証
    assert Path(result.ref) != existing
    assert Path(result.ref).name.startswith("workspace.before-v0.3.0-")
    assert Path(result.ref).is_dir()


def test_restore_backup_when_copy(
    make_workspace: MakeWorkspace, make_item: MakeItem, snapshot_tree: SnapshotTree
) -> None:
    """複製から書き戻し、増えたファイルを消す（正常系）。"""
    # 準備
    root = make_workspace(make_item("A-1"))
    before = snapshot_tree(root)
    taken = backup.take_backup(root, TARGET_VERSION)
    (root / "docs.yaml").write_text("items: []\n", encoding="utf-8")
    (root / "new.yaml").write_text("items: []\n", encoding="utf-8")
    # 実行
    backup.restore_backup(root, taken)
    # 検証
    assert snapshot_tree(root) == before
    assert not (root / "new.yaml").exists()


def test_restore_backup_when_git(git_workspace: Path, snapshot_tree: SnapshotTree) -> None:
    """コミットの中身に戻し、増えたファイルを消す（正常系）。"""
    # 準備
    before = snapshot_tree(git_workspace)
    taken = backup.take_backup(git_workspace, TARGET_VERSION)
    (git_workspace / "docs.yaml").write_text("items: []\n", encoding="utf-8")
    (git_workspace / "new.yaml").write_text("items: []\n", encoding="utf-8")
    # 実行
    backup.restore_backup(git_workspace, taken)
    # 検証
    assert snapshot_tree(git_workspace) == before
    assert not (git_workspace / "new.yaml").exists()
