"""コマンドの起動（依存が無いときの仮想環境の Python での起動し直し）の結合テスト。"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from workspace_fixtures import COMMAND_TIMEOUT_SEC, MINDMAP_SCRIPT

from .fixture_types import MakeVenv, MakeWorkspace, SnapshotTree

# ホームの下の、スキル専用の仮想環境の場所（check-env の既定）
VENV_RELATIVE_PATH = "home/.mindmap/venv"

# 古い版を名乗る仮の配布の版（下限 4.18.0 より古い）
OLD_JSONSCHEMA_VERSION = "4.0.0"


def _python_of(venv_dir: Path) -> str:
    """仮想環境の Python の場所を返す。"""
    return str(venv_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python"))


def _run_launch(python: str, home: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """ホームを差し替えて、指定した Python で mindmap.py を起動する。"""
    env = {**os.environ, "PYTHONUTF8": "1", "HOME": str(home), "USERPROFILE": str(home)}
    return subprocess.run(
        [python, str(MINDMAP_SCRIPT), *args],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=COMMAND_TIMEOUT_SEC,
        check=False,
    )


def _site_packages_of(python: str) -> Path:
    """仮想環境の Python の site-packages の場所を返す。"""
    found = subprocess.run(
        [python, "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return Path(found)


def test_normal_when_python_ready(tmp_path: Path, make_workspace: MakeWorkspace) -> None:
    """起動した Python に依存があれば、起動し直さずにコマンドを実行する（正常系）。"""
    # 準備
    home = tmp_path / "home"
    home.mkdir()
    root = make_workspace()
    # 実行
    result = _run_launch(sys.executable, home, "attrs", "--workspace", str(root))
    # 検証
    # 仮想環境が無くても通る（起動し直していない）
    assert result.returncode == 0
    assert json.loads(result.stdout) == {"attrs": []}


def test_normal_when_relaunch(
    make_venv: MakeVenv, make_workspace: MakeWorkspace, tmp_path: Path
) -> None:
    """起動した Python に依存が無ければ、仮想環境の Python で起動し直し、出力と終了コードをそのまま返す（正常系）。"""
    # 準備
    bare_python = _python_of(make_venv("bare", with_libraries=False))
    venv_dir = make_venv(VENV_RELATIVE_PATH)
    root = make_workspace()
    home = tmp_path / "home"
    # 実行
    result = _run_launch(bare_python, home, "attrs", "--workspace", str(root))
    # 検証
    direct = _run_launch(_python_of(venv_dir), home, "attrs", "--workspace", str(root))
    assert result.returncode == 0
    assert result.stdout == direct.stdout
    assert json.loads(result.stdout) == {"attrs": []}


def test_normal_when_relaunched_command_fails(make_venv: MakeVenv, tmp_path: Path) -> None:
    """起動し直したコマンドがエラーで終われば、その標準エラーと終了コードをそのまま返す（正常系）。"""
    # 準備
    bare_python = _python_of(make_venv("bare", with_libraries=False))
    make_venv(VENV_RELATIVE_PATH)
    home = tmp_path / "home"
    empty = tmp_path / "empty"
    empty.mkdir()
    # 実行
    result = _run_launch(bare_python, home, "status", "--workspace", str(empty))
    # 検証
    assert result.returncode == 1
    assert str(empty) in result.stderr
    assert result.stdout == ""


def test_normal_when_dependency_old(
    make_venv: MakeVenv, make_workspace: MakeWorkspace, tmp_path: Path
) -> None:
    """起動した Python の依存が下限より古ければ、読み込めても仮想環境の Python で起動し直す（正常系）。"""
    # 準備
    old_python = _python_of(make_venv("old"))
    venv_dir = make_venv(VENV_RELATIVE_PATH)
    root = make_workspace()
    home = tmp_path / "home"
    # 起動する Python の site-packages に、古い版を名乗る仮の配布を置く（版は importlib.metadata が読む）
    site_packages = _site_packages_of(old_python)
    dist_info = site_packages / f"jsonschema-{OLD_JSONSCHEMA_VERSION}.dist-info"
    dist_info.mkdir()
    (dist_info / "METADATA").write_text(
        f"Metadata-Version: 2.1\nName: jsonschema\nVersion: {OLD_JSONSCHEMA_VERSION}\n",
        encoding="utf-8",
    )
    (site_packages / "jsonschema").mkdir()
    (site_packages / "jsonschema" / "__init__.py").write_text("", encoding="utf-8")
    # 実行
    result = _run_launch(old_python, home, "attrs", "--workspace", str(root))
    # 検証
    direct = _run_launch(_python_of(venv_dir), home, "attrs", "--workspace", str(root))
    assert result.returncode == 0
    assert result.stdout == direct.stdout


def test_error_when_venv_missing(
    make_venv: MakeVenv,
    make_workspace: MakeWorkspace,
    snapshot_tree: SnapshotTree,
    tmp_path: Path,
) -> None:
    """依存が無く仮想環境も無ければ、check-env を促してエラーで終わる（異常系）。"""
    # 準備
    bare_python = _python_of(make_venv("bare", with_libraries=False))
    root = make_workspace()
    home = tmp_path / "home"
    home.mkdir()
    before = snapshot_tree(root)
    # 実行
    result = _run_launch(bare_python, home, "attrs", "--workspace", str(root))
    # 検証
    assert result.returncode == 1
    assert str(home / ".mindmap" / "venv") in result.stderr
    assert "check-env" in result.stderr
    assert result.stdout == ""
    assert snapshot_tree(root) == before


def test_error_when_dependency_missing(
    make_venv: MakeVenv, make_workspace: MakeWorkspace, tmp_path: Path
) -> None:
    """仮想環境にも依存が無ければ、もう一度は起動し直さずエラーで終わる（異常系）。"""
    # 準備
    bare_python = _python_of(make_venv("bare", with_libraries=False))
    make_venv(VENV_RELATIVE_PATH, with_libraries=False)
    root = make_workspace()
    home = tmp_path / "home"
    # 実行
    result = _run_launch(bare_python, home, "attrs", "--workspace", str(root))
    # 検証
    # 起動し直しが繰り返されれば終わらずに待ち時間を超えるので、終わったこと自体が 1 回で止まった証になる
    assert result.returncode == 1
    assert "PyYAML" in result.stderr
    assert "jsonschema" in result.stderr
    assert "check-env" in result.stderr
    assert result.stdout == ""
