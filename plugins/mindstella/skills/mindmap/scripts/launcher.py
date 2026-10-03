"""起動した Python に依存が揃っていなければ、スキル専用の仮想環境の Python で mindmap.py を起動し直す。

依存を読み込めない Python でも読まれるので、Python 3.8 で読める構文だけで書く。
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from check_env import (
    MIN_PYTHON,
    REQUIREMENTS,
    DependencyMissingError,
    PythonVersionError,
    VenvNotFoundError,
    default_venv_dir,
    parse_version,
    run_check_env,
)


def current_python_ready(
    *,
    version_info: tuple[int, ...] = tuple(sys.version_info),
    find_version: Callable[[str], str] = version,
) -> bool:
    """起動した Python が依存の確認と同じ判定で揃っているかを返す。"""
    # Python の版が下限より古い
    if tuple(version_info) < MIN_PYTHON:
        return False
    for name, required in REQUIREMENTS.items():
        try:
            installed = find_version(name)
        except PackageNotFoundError:
            # 配布が入っていない
            return False
        # 入っている版が下限より古い
        if parse_version(installed) < parse_version(required):
            return False
    return True


def relaunch_if_needed(
    argv: list[str],
    *,
    script: Path,
    ready: Callable[[], bool] = current_python_ready,
    check: Callable[[Path], dict[str, Any]] = run_check_env,
    venv_dir: Path = default_venv_dir(),
    prefix: str = sys.prefix,
    run: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
) -> int | None:
    """起動した Python で動ければ None、動けなければ仮想環境の Python で起動し直して終了コードを返す。"""
    # 引数が空・check-env・起動した Python で動ける: 起動し直さない
    if not argv or argv[0] == "check-env" or ready():
        return None
    # 仮想環境が使えるか確かめる（使えなければ例外がそのまま伝わる）
    report = check(venv_dir)
    # 仮想環境の Python で起動されているのに依存が揃っていない: 起動し直しを繰り返さない
    if Path(prefix).resolve() == venv_dir.resolve():
        raise DependencyMissingError(report)
    # 配列のまま渡して、シェルを通さずに同じ引数で起動し直す
    completed = run([report["python_path"], str(script), *argv], check=False)
    return completed.returncode


def format_relaunch_error(
    error: VenvNotFoundError | PythonVersionError | DependencyMissingError,
) -> list[str]:
    """仮想環境の確認の例外から、標準エラーに出す行を作る。"""
    report = error.report
    lines = [f"エラー: スキル専用の仮想環境が使えません: {report['venv']}"]
    # 例外の種類ごとに足りないものを書く
    if isinstance(error, VenvNotFoundError):
        lines.append("仮想環境がありません")
    elif isinstance(error, PythonVersionError):
        lines.append(
            f"仮想環境の Python の版が下限より古いか、版を引けません（版: {report['python']}）"
        )
    else:
        missing = [row["name"] for row in report["packages"] if not row["ok"]]
        lines.append(f"足りないライブラリ: {', '.join(missing)}")
    lines.append("`check-env` を実行し、出力の `install` のコマンドで揃えてください")
    return lines
