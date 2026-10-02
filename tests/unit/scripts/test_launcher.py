"""launcher.py（起動した Python の依存の判定と、仮想環境の Python での起動し直し）の単体テスト。"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from importlib.metadata import PackageNotFoundError
from pathlib import Path
from typing import Any

import pytest

import check_env
import launcher

# 依存が揃っているときの、配布名 → 入っている版
READY_VERSIONS = {"PyYAML": "6.0.3", "jsonschema": "4.26.0"}

# 起動し直す先として check が返す Python の場所
VENV_PYTHON = "/v/bin/python"

# 起動し直す mindmap.py
SCRIPT = Path("/s/mindmap.py")


def _make_find_version(versions: dict[str, str]) -> Callable[[str], str]:
    """versions にある配布は版を返し、無い配布は PackageNotFoundError を送る find_version の代わりを作る。"""

    def _find_version(name: str) -> str:
        """配布名から入っている版を引く。"""
        if name not in versions:
            raise PackageNotFoundError(name)
        return versions[name]

    return _find_version


def _make_ready(result: bool) -> tuple[Callable[[], bool], list[bool]]:
    """決めた結果を返し、呼ばれた回数を残す ready の代わりを作る。"""
    calls: list[bool] = []

    def _ready() -> bool:
        """起動した Python の依存の判定の代わり。"""
        calls.append(result)
        return result

    return _ready, calls


def _make_check(
    report: dict[str, Any],
) -> tuple[Callable[[Path], dict[str, Any]], list[Path]]:
    """決めた結果を返し、渡された仮想環境のフォルダを残す check の代わりを作る。"""
    calls: list[Path] = []

    def _check(venv_dir: Path) -> dict[str, Any]:
        """仮想環境の確認の代わり。"""
        calls.append(venv_dir)
        return report

    return _check, calls


def _make_failing_check(
    error: Exception,
) -> tuple[Callable[[Path], dict[str, Any]], list[Path]]:
    """決めた例外を送り、渡された仮想環境のフォルダを残す check の代わりを作る。"""
    calls: list[Path] = []

    def _check(venv_dir: Path) -> dict[str, Any]:
        """仮想環境の確認の代わり。"""
        calls.append(venv_dir)
        raise error

    return _check, calls


def _make_run(
    returncode: int,
) -> tuple[Callable[..., subprocess.CompletedProcess[Any]], list[list[str]]]:
    """決めた終了コードを返し、起動の引数を残す run の代わりを作る。"""
    calls: list[list[str]] = []

    def _run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[Any]:
        """子プロセスの起動の代わり。"""
        calls.append(list(args[0] if args else kwargs["args"]))
        return subprocess.CompletedProcess(args=args, returncode=returncode)

    return _run, calls


def _make_report(venv: str = "/v", **overrides: Any) -> dict[str, Any]:
    """依存の確認の結果（check-env の出力と同じ形）を作る。"""
    report: dict[str, Any] = {
        "base_python": "/usr/bin/python3",
        "base_python_version": "3.12.3",
        "base_python_ok": True,
        "venv": venv,
        "python_path": f"{venv}/bin/python",
        "venv_ok": True,
        "python": "3.12.3",
        "python_ok": True,
        "packages": [
            {"name": "PyYAML", "required": "5.1", "installed": "6.0.3", "ok": True},
            {
                "name": "jsonschema",
                "required": "4.18.0",
                "installed": "4.26.0",
                "ok": True,
            },
        ],
        "install": '"/v/bin/python" -m pip install "jsonschema>=4.18.0"',
    }
    report.update(overrides)
    return report


def test_current_python_ready() -> None:
    """版と依存が揃っていれば真（正常系）。"""
    # 準備
    find_version = _make_find_version(READY_VERSIONS)
    # 実行
    result = launcher.current_python_ready(version_info=(3, 12, 3), find_version=find_version)
    # 検証
    assert result is True


@pytest.mark.parametrize(
    ("version_info", "versions"),
    [
        pytest.param((3, 11, 9), READY_VERSIONS, id="old_python"),
        pytest.param((3, 12, 3), {"PyYAML": "6.0.3"}, id="missing_package"),
        pytest.param((3, 12, 3), {"PyYAML": "6.0.3", "jsonschema": "4.0.0"}, id="old_package"),
    ],
)
def test_current_python_ready_when_not_ready(
    version_info: tuple[int, ...], versions: dict[str, str]
) -> None:
    """古い Python・無い配布・古い配布は偽（正常系）。"""
    # 準備
    find_version = _make_find_version(versions)
    # 実行
    result = launcher.current_python_ready(version_info=version_info, find_version=find_version)
    # 検証
    assert result is False


@pytest.mark.parametrize(
    ("ready_result", "argv"),
    [
        pytest.param(True, ["attrs"], id="ready"),
        pytest.param(False, ["check-env"], id="check_env"),
        pytest.param(False, [], id="empty_argv"),
    ],
)
def test_relaunch_if_needed_when_ready(tmp_path: Path, ready_result: bool, argv: list[str]) -> None:
    """起動した Python で動ければ起動し直さない（正常系）。"""
    # 準備
    ready, _ = _make_ready(ready_result)
    check, check_calls = _make_check(_make_report())
    run, run_calls = _make_run(0)
    # 実行
    result = launcher.relaunch_if_needed(
        argv,
        script=SCRIPT,
        ready=ready,
        check=check,
        venv_dir=tmp_path / "venv",
        prefix=str(tmp_path / "sys"),
        run=run,
    )
    # 検証
    assert result is None
    assert check_calls == []
    assert run_calls == []


def test_relaunch_if_needed(tmp_path: Path) -> None:
    """仮想環境の Python で同じ引数を渡して起動し直す（正常系）。"""
    # 準備
    venv_dir = tmp_path / "venv"
    ready, _ = _make_ready(False)
    check, check_calls = _make_check(_make_report(python_path=VENV_PYTHON))
    run, run_calls = _make_run(3)
    # 実行
    result = launcher.relaunch_if_needed(
        ["status", "--workspace", "w"],
        script=SCRIPT,
        ready=ready,
        check=check,
        venv_dir=venv_dir,
        prefix=str(tmp_path / "sys"),
        run=run,
    )
    # 検証
    assert result == 3
    assert check_calls == [venv_dir]
    assert run_calls == [[VENV_PYTHON, str(SCRIPT), "status", "--workspace", "w"]]


@pytest.mark.skipif(sys.platform == "win32", reason="シンボリックリンクを作れない環境がある")
def test_relaunch_if_needed_when_same_interpreter(tmp_path: Path) -> None:
    """システムの Python と仮想環境の Python が同じ実体を指していても起動し直す（正常系）。"""
    # 準備
    system_python = tmp_path / "sys" / "bin" / "python3"
    system_python.parent.mkdir(parents=True)
    system_python.touch()
    venv_python = tmp_path / "venv" / "bin" / "python"
    venv_python.parent.mkdir(parents=True)
    venv_python.symlink_to(system_python)
    ready, _ = _make_ready(False)
    check, _ = _make_check(_make_report(python_path=str(venv_python)))
    run, run_calls = _make_run(0)
    # 実行
    result = launcher.relaunch_if_needed(
        ["attrs", "--workspace", "w"],
        script=SCRIPT,
        ready=ready,
        check=check,
        venv_dir=tmp_path / "venv",
        prefix=str(tmp_path / "sys"),
        run=run,
    )
    # 検証
    assert result == 0
    assert run_calls == [[str(venv_python), str(SCRIPT), "attrs", "--workspace", "w"]]


def test_relaunch_if_needed_when_venv_missing(tmp_path: Path) -> None:
    """仮想環境の確認の例外をそのまま伝える（異常系）。"""
    # 準備
    ready, _ = _make_ready(False)
    check, _ = _make_failing_check(check_env.VenvNotFoundError(_make_report(venv_ok=False)))
    run, run_calls = _make_run(0)
    # 実行・検証
    with pytest.raises(check_env.VenvNotFoundError):
        launcher.relaunch_if_needed(
            ["status", "--workspace", "w"],
            script=SCRIPT,
            ready=ready,
            check=check,
            venv_dir=tmp_path / "venv",
            prefix=str(tmp_path / "sys"),
            run=run,
        )
    assert run_calls == []


def test_relaunch_if_needed_when_already_venv(tmp_path: Path) -> None:
    """仮想環境の Python で起動されていれば繰り返さない（異常系）。"""
    # 準備
    venv_dir = tmp_path / "venv"
    venv_dir.mkdir()
    ready, _ = _make_ready(False)
    check, _ = _make_check(_make_report(python_path=VENV_PYTHON))
    run, run_calls = _make_run(0)
    # 実行・検証
    with pytest.raises(check_env.DependencyMissingError):
        launcher.relaunch_if_needed(
            ["status", "--workspace", "w"],
            script=SCRIPT,
            ready=ready,
            check=check,
            venv_dir=venv_dir,
            prefix=str(venv_dir),
            run=run,
        )
    assert run_calls == []


@pytest.mark.parametrize(
    ("error", "expected_fragment"),
    [
        pytest.param(
            check_env.VenvNotFoundError(_make_report(venv_ok=False, python=None)),
            "仮想環境がありません",
            id="venv_not_found",
        ),
        pytest.param(
            check_env.PythonVersionError(_make_report(python="3.11.9", python_ok=False)),
            "3.11.9",
            id="python_version",
        ),
        pytest.param(
            check_env.DependencyMissingError(
                _make_report(
                    packages=[
                        {
                            "name": "PyYAML",
                            "required": "5.1",
                            "installed": "6.0.3",
                            "ok": True,
                        },
                        {
                            "name": "jsonschema",
                            "required": "4.18.0",
                            "installed": None,
                            "ok": False,
                        },
                    ]
                )
            ),
            "jsonschema",
            id="dependency_missing",
        ),
    ],
)
def test_format_relaunch_error(
    error: check_env.VenvNotFoundError
    | check_env.PythonVersionError
    | check_env.DependencyMissingError,
    expected_fragment: str,
) -> None:
    """例外の種類ごとに足りないものと check-env を書く（正常系）。"""
    # 実行
    lines = launcher.format_relaunch_error(error)
    # 検証
    assert lines[0].startswith("エラー: ")
    assert "/v" in lines[0]
    assert expected_fragment in "\n".join(lines[1:])
    assert "check-env" in lines[-1]
