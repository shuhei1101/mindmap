"""移し替える前の写しの取り方と戻し方（git のコミットか、フォルダの複製）。"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from store import write_failed
from versions import Version

# git の写しのコミットのメッセージ（`{version}` は移し替える先の版）
BACKUP_COMMIT_MESSAGE = "mindstella: {version} へ移し替える前の写し"

# 同じ名前の写しがあるときに、複製のフォルダ名の末尾へ足す日時の形
COPY_SUFFIX_FORMAT = "%Y%m%d%H%M%S"


@dataclass(frozen=True, slots=True, kw_only=True)
class Backup:
    """取った写し。`kind` は git のコミットか、フォルダの複製か。`ref` はコミットの ID か、複製したフォルダの絶対パス。"""

    kind: Literal["git", "copy"]
    ref: str


def take_backup(root: Path, version: Version) -> Backup:
    """git の作業ツリーの中で ignore されたファイルが無ければワークスペースのパスだけをコミットし、そうでなければ隣のフォルダへ複製する。"""
    committed = _commit_workspace(root, version)
    if committed is not None:
        return Backup(kind="git", ref=committed)
    return _copy_workspace(root, version)


def restore_backup(root: Path, backup: Backup) -> None:
    """ワークスペースを写しの中身に戻す。戻せなければ OSError を送る。"""
    if backup.kind == "git":
        # コミットの中身に戻し、コミットに無いファイルを消す
        _run_git(root, "checkout", backup.ref, "--", ".")
        _run_git(root, "clean", "-fdq", "--", ".")
        return
    # 中身を全て消してから、複製の中身を書き戻す
    for child in root.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
    shutil.copytree(backup.ref, root, dirs_exist_ok=True)


def _commit_workspace(root: Path, version: Version) -> str | None:
    """ワークスペースのパスだけをコミットし、そのコミットの ID を返す。コミットできない条件のときは None。"""
    # git の作業ツリーの外（git が無い場合も含む）
    inside = _git(root, "rev-parse", "--is-inside-work-tree")
    if inside is None or inside.returncode != 0:
        return None
    # ignore されたファイルがあると、コミットでは写せない
    ignored = _git(root, "ls-files", "--others", "--ignored", "--exclude-standard", "--", ".")
    if ignored is None or ignored.returncode != 0 or ignored.stdout.strip():
        return None
    staged = _git(root, "add", "-A", "--", ".")
    if staged is None or staged.returncode != 0:
        return None
    # 変更が無ければ、コミットを増やさず今の HEAD を写しにする
    unchanged = _git(root, "diff", "--cached", "--quiet", "--", ".")
    if unchanged is not None and unchanged.returncode == 0:
        head = _git(root, "rev-parse", "--verify", "HEAD")
        return head.stdout.strip() if head is not None and head.returncode == 0 else None
    message = BACKUP_COMMIT_MESSAGE.format(version=version)
    commit = _git(root, "commit", "-q", "-m", message, "--", ".")
    # コミットできなかった（作者の名前が無い等）: ステージを戻して複製に回す
    if commit is None or commit.returncode != 0:
        _git(root, "reset", "-q", "--", ".")
        return None
    return _run_git(root, "rev-parse", "HEAD").strip()


def _copy_workspace(root: Path, version: Version) -> Backup:
    """ワークスペースの隣のフォルダへ複製する。同じ名前があれば末尾に日時を足す。"""
    destination = root.parent / f"{root.name}.before-{version}"
    # 同じ名前の写しがある
    if destination.exists():
        stamp = datetime.now(UTC).strftime(COPY_SUFFIX_FORMAT)
        destination = root.parent / f"{root.name}.before-{version}-{stamp}"
    try:
        shutil.copytree(root, destination)
    except OSError as error:
        # 作りかけの複製は残さない
        shutil.rmtree(destination, ignore_errors=True)
        raise write_failed(destination, error) from error
    return Backup(kind="copy", ref=str(destination.absolute()))


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str] | None:
    """root で git を呼び、終了コードが 0 以外でも結果を返す。git が無ければ None。"""
    try:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except OSError:
        return None


def _run_git(root: Path, *args: str) -> str:
    """root で git を呼び、標準出力を返す。失敗したら OSError を送る。"""
    result = _git(root, *args)
    if result is None:
        raise OSError("git を起動できません")
    # 終了コードが 0 以外
    if result.returncode != 0:
        raise OSError(f"git {args[0]} が失敗しました: {result.stderr.strip()}")
    return result.stdout
