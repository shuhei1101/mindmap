"""check-env（依存の確認）の結合テスト。"""

from __future__ import annotations

import json
import shlex
import socket
import subprocess
from pathlib import Path
from typing import Any

import pytest

from .fixture_types import FindOldPython, MakeVenv, MakeWorkspace, RunMindmap

# 通信できるかを確かめる先と待つ秒数
PYPI_HOST = "pypi.org"
PYPI_PORT = 443
NETWORK_TIMEOUT_SEC = 5

# 仮想環境を作ってライブラリを入れる（通信する）コマンド 1 本を待つ上限秒数
INSTALL_TIMEOUT_SEC = 600


def _skip_without_network() -> None:
    """PyPI へ通信できなければ、その場でテストを skip する。"""
    try:
        socket.create_connection((PYPI_HOST, PYPI_PORT), timeout=NETWORK_TIMEOUT_SEC).close()
    except OSError:
        pytest.skip("PyPI へ通信できない")


def _run_install_command(command: str) -> None:
    """`&&` でつないだそろえるコマンドを、シェルを通さずに 1 本ずつ流す。"""
    for step in command.split(" && "):
        subprocess.run(shlex.split(step), check=True, timeout=INSTALL_TIMEOUT_SEC)


def _packages_by_name(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """出力のライブラリの一覧を、名前から引ける辞書にする。"""
    return {package["name"]: package for package in payload["packages"]}


def test_normal(
    make_workspace: MakeWorkspace,
    make_venv: MakeVenv,
    run_mindmap: RunMindmap,
) -> None:
    """仮想環境に依存がそろっていて、起動する Python を返す（正常系）。"""
    # 準備
    venv_dir = make_venv("venv")
    root = make_workspace()
    # 実行
    result = run_mindmap("check-env", "--venv", str(venv_dir))
    # 検証
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    packages = _packages_by_name(payload)
    assert payload["venv"] == str(venv_dir.resolve())
    assert payload["venv_ok"] is True
    assert payload["python_ok"] is True
    assert packages["PyYAML"]["ok"] is True
    assert packages["jsonschema"]["ok"] is True
    assert payload["install"] is None
    # 返された python_path で、ほかのコマンドを起動できる
    started = run_mindmap("attrs", "--workspace", str(root), python=payload["python_path"])
    assert started.returncode == 0
    assert json.loads(started.stdout) == {"attrs": []}


def test_error_when_venv_missing(tmp_path: Path, run_mindmap: RunMindmap) -> None:
    """仮想環境が無ければ、作って入れる 1 行のコマンドを返す（異常系）。"""
    # 準備
    venv_dir = tmp_path / "new-venv"
    # 実行
    result = run_mindmap("check-env", "--venv", str(venv_dir))
    # 検証
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    packages = _packages_by_name(payload)
    assert payload["venv_ok"] is False
    assert payload["python"] is None
    assert packages["PyYAML"]["installed"] is None
    assert packages["jsonschema"]["installed"] is None
    assert "-m venv" in payload["install"]
    assert str(venv_dir) in payload["install"]
    assert "PyYAML>=5.1" in payload["install"]
    assert "jsonschema>=4.18.0" in payload["install"]
    # そろえるコマンドをそのまま流すと仮想環境ができ、もう一度確かめると全てそろっている
    _skip_without_network()
    _run_install_command(payload["install"])
    again = run_mindmap("check-env", "--venv", str(venv_dir))
    assert again.returncode == 0


def test_error_when_python_too_old(
    make_venv: MakeVenv, find_old_python: FindOldPython, run_mindmap: RunMindmap
) -> None:
    """仮想環境の Python が下限より古ければ、構文エラーで落ちずに python_ok: false を返す（異常系）。"""
    # 準備
    old_python = find_old_python()
    venv_dir = make_venv("old-venv", python=old_python, with_libraries=False)
    # 実行
    result = run_mindmap("check-env", "--venv", str(venv_dir))
    # 検証
    assert result.returncode == 1
    assert "SyntaxError" not in result.stderr
    payload = json.loads(result.stdout)
    assert payload["python_ok"] is False
    assert payload["python"].startswith("3.")
    assert "--clear" in payload["install"]


def test_error_when_dependency_missing(make_venv: MakeVenv, run_mindmap: RunMindmap) -> None:
    """ライブラリを入れていない仮想環境で、足りないものと入れるコマンドを返す（異常系）。"""
    # 準備
    venv_dir = make_venv("bare-venv", with_libraries=False)
    # 実行
    result = run_mindmap("check-env", "--venv", str(venv_dir))
    # 検証
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    packages = _packages_by_name(payload)
    assert packages["PyYAML"]["installed"] is None
    assert packages["PyYAML"]["ok"] is False
    assert packages["jsonschema"]["installed"] is None
    assert packages["jsonschema"]["ok"] is False
    assert f'"{payload["python_path"]}" -m pip install' in payload["install"]
    assert "PyYAML>=5.1" in payload["install"]
    assert "jsonschema>=4.18.0" in payload["install"]
    assert "-m venv" not in payload["install"]


def test_error_when_base_python_too_old(
    tmp_path: Path, find_old_python: FindOldPython, run_mindmap: RunMindmap
) -> None:
    """仮想環境が無く、check-env を動かす Python も下限より古ければ、流しても直らないコマンドを返さない（異常系）。"""
    # 準備
    old_python = find_old_python()
    venv_dir = tmp_path / "new-venv"
    old_version = subprocess.run(
        [old_python, "-c", "import platform; print(platform.python_version())"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    # 実行
    result = run_mindmap("check-env", "--venv", str(venv_dir), python=old_python)
    # 検証
    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["venv_ok"] is False
    assert payload["base_python_ok"] is False
    assert payload["base_python_version"] == old_version
    assert payload["install"] is None
