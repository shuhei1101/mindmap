"""移し替えの単体テストが共有する、手順・git・更新日時の補助。"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from migrator import MigrationStep
from versions import Version

# 手順に付ける版（v0.3.0 の手順を試すので揃える）
STEP_VERSION = Version(0, 3, 0)

# 手順の置き場所（migrations/）のうち、1 つの版のフォルダにある手順の名前
STEPS_FILE = "steps.yaml"


def make_step(op: Any, args: dict[str, Any], *, folder: Path | None = None) -> MigrationStep:
    """操作名と引数から、v0.3.0 の 1 番目の手順を作る（op は Literal の操作名を str で受けるため Any）。"""
    return MigrationStep(
        version=STEP_VERSION,
        index=1,
        op=op,
        args=args,
        folder=folder if folder is not None else Path("."),
    )


def snapshot_mtimes(root: Path) -> dict[str, int]:
    """フォルダの下の全てのファイルの更新日時（ナノ秒）を、相対パス → 更新日時で返す。"""
    return {
        path.relative_to(root).as_posix(): path.stat().st_mtime_ns
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def run_git(cwd: Path, *args: str) -> str:
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


def init_git_repo(path: Path) -> None:
    """フォルダを作って git init し、コミットに要る作者を、そのリポジトリの設定に置く。"""
    path.mkdir(parents=True, exist_ok=True)
    run_git(path, "init", "-q")
    run_git(path, "config", "user.name", "テスト")
    run_git(path, "config", "user.email", "test@example.com")
    run_git(path, "config", "commit.gpgsign", "false")
