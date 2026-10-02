"""check_env.py（依存の確認）の単体テスト。"""

from __future__ import annotations

import ast
import platform
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

import check_env

# 仮想環境の Python が返す、揃っているときの版の一覧
GOOD_PROBE_RESULT: dict[str, Any] = {
    "python": "3.12.3",
    "packages": {"PyYAML": "6.0.3", "jsonschema": "4.26.0"},
}

# 仮想環境の Python が古いときの版の一覧
OLD_PYTHON_PROBE_RESULT: dict[str, Any] = {
    "python": "3.9.6",
    "packages": {"PyYAML": "6.0.3", "jsonschema": "4.26.0"},
}


def _make_probe(
    result: dict[str, Any] | None,
) -> tuple[Callable[[Path], dict[str, Any] | None], list[Path]]:
    """決めた結果を返し、呼ばれた Python の場所を記録する probe の代わりを作る。"""
    calls: list[Path] = []

    def _probe(python_path: Path) -> dict[str, Any] | None:
        """呼ばれた Python の場所を記録して、決めた結果を返す。"""
        calls.append(python_path)
        return result

    return _probe, calls


def _packages_by_name(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """結果のライブラリの一覧を、名前から引ける辞書にする。"""
    return {package["name"]: package for package in report["packages"]}


def _run_raising_os_error(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    """子プロセスを起動できないときの subprocess.run の代わり。"""
    raise OSError("起動できません")


def _run_returning(returncode: int, stdout: str) -> Callable[..., subprocess.CompletedProcess[str]]:
    """決めた終了コードと標準出力を返す subprocess.run の代わりを作る。"""

    def _run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        """起動せずに、決めた結果を返す。"""
        return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout)

    return _run


@pytest.fixture
def fake_venv(tmp_path: Path) -> dict[str, Path]:
    """Python の場所だけを置いた仮想環境（present）と、まだ無い仮想環境（absent）を返す。"""
    present = tmp_path / "present"
    python_path = check_env.venv_python_path(present)
    python_path.parent.mkdir(parents=True)
    python_path.touch()
    return {"present": present, "absent": tmp_path / "absent"}


def test_run_check_env(fake_venv: dict[str, Path]) -> None:
    """そろっていれば結果を返す（正常系）。"""
    # 準備
    probe, calls = _make_probe(GOOD_PROBE_RESULT)
    python_path = check_env.venv_python_path(fake_venv["present"])
    # 実行
    report = check_env.run_check_env(fake_venv["present"], probe=probe)
    # 検証
    packages = _packages_by_name(report)
    assert report["venv_ok"] is True
    assert report["python_ok"] is True
    assert report["python"] == "3.12.3"
    assert packages["PyYAML"]["ok"] is True
    assert packages["jsonschema"]["ok"] is True
    assert str(report["python_path"]) == str(python_path)
    assert report["install"] is None
    assert calls == [python_path]


def test_run_check_env_when_venv_missing(fake_venv: dict[str, Path]) -> None:
    """仮想環境が無ければ VenvNotFoundError を送る（異常系）。"""
    # 準備
    probe, calls = _make_probe(GOOD_PROBE_RESULT)
    # 実行・検証
    with pytest.raises(check_env.VenvNotFoundError) as exc_info:
        check_env.run_check_env(fake_venv["absent"], probe=probe)
    report = exc_info.value.report
    packages = _packages_by_name(report)
    assert report["venv_ok"] is False
    assert report["python"] is None
    assert packages["PyYAML"]["installed"] is None
    assert packages["jsonschema"]["installed"] is None
    assert "-m venv" in report["install"]
    assert calls == []


@pytest.mark.parametrize(
    ("probe_result", "expected_python"),
    [
        pytest.param(OLD_PYTHON_PROBE_RESULT, "3.9.6", id="old_version"),
        pytest.param(None, None, id="unreadable"),
    ],
)
def test_run_check_env_when_python_old(
    fake_venv: dict[str, Path],
    probe_result: dict[str, Any] | None,
    expected_python: str | None,
) -> None:
    """仮想環境の Python が古いか版を引けなければ PythonVersionError を送る（異常系）。"""
    # 準備
    probe, _ = _make_probe(probe_result)
    # 実行・検証
    with pytest.raises(check_env.PythonVersionError) as exc_info:
        check_env.run_check_env(fake_venv["present"], probe=probe)
    report = exc_info.value.report
    assert report["python_ok"] is False
    assert report["python"] == expected_python
    assert "--clear" in report["install"]


def test_run_check_env_when_package_missing(fake_venv: dict[str, Path]) -> None:
    """無い・古いライブラリがあれば DependencyMissingError を送る（異常系）。"""
    # 準備
    probe, _ = _make_probe(
        {"python": "3.12.3", "packages": {"PyYAML": None, "jsonschema": "4.17.3"}}
    )
    # 実行・検証
    with pytest.raises(check_env.DependencyMissingError) as exc_info:
        check_env.run_check_env(fake_venv["present"], probe=probe)
    report = exc_info.value.report
    packages = _packages_by_name(report)
    assert packages["PyYAML"]["installed"] is None
    assert packages["PyYAML"]["ok"] is False
    assert packages["jsonschema"]["ok"] is False
    assert "PyYAML>=5.1" in report["install"]
    assert "jsonschema>=4.18.0" in report["install"]
    assert "-m venv" not in report["install"]


@pytest.mark.parametrize("file_name", ["mindmap.py", "check_env.py"])
def test_run_check_env_when_old_syntax(scripts_dir: Path, file_name: str) -> None:
    """入口と依存の確認のファイルが Python 3.8 の構文で読め、型注釈を実行時に評価しない（正常系）。"""
    # 準備
    source = (scripts_dir / file_name).read_text(encoding="utf-8")
    # 実行
    tree = ast.parse(source, feature_version=(3, 8))
    # 検証
    # 先頭は docstring で、その次の文が `from __future__ import annotations`
    statement = tree.body[1]
    assert isinstance(statement, ast.ImportFrom)
    assert statement.module == "__future__"
    assert len(statement.names) == 1
    assert statement.names[0].name == "annotations"


@pytest.mark.parametrize(
    ("venv_key", "probe_result", "error"),
    [
        pytest.param("absent", GOOD_PROBE_RESULT, check_env.VenvNotFoundError, id="venv_missing"),
        pytest.param(
            "present",
            OLD_PYTHON_PROBE_RESULT,
            check_env.PythonVersionError,
            id="python_old",
        ),
    ],
)
def test_run_check_env_when_base_python_old(
    fake_venv: dict[str, Path],
    venv_key: str,
    probe_result: dict[str, Any],
    error: type[Exception],
) -> None:
    """仮想環境を作る Python が古ければ、作る・作り直すコマンドを返さない（異常系）。"""
    # 準備
    probe, _ = _make_probe(probe_result)
    # 実行・検証
    with pytest.raises(error) as exc_info:
        check_env.run_check_env(fake_venv[venv_key], probe=probe, base_version=(3, 9, 6))
    report = exc_info.value.report
    assert report["base_python_ok"] is False
    assert report["base_python_version"] == "3.9.6"
    assert report["install"] is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("6.0.3", (6, 0, 3), id="release"),
        pytest.param("4.18.0rc1", (4, 18, 0), id="release_candidate"),
        pytest.param("5.1", (5, 1), id="two_parts"),
    ],
)
def test_parse_version(text: str, expected: tuple[int, ...]) -> None:
    """版の文字列を数字の組にする（正常系）。"""
    # 実行
    version = check_env.parse_version(text)
    # 検証
    assert version == expected


@pytest.mark.parametrize(
    ("mode", "missing", "expected"),
    [
        pytest.param(
            "create",
            ["PyYAML", "jsonschema"],
            '"/usr/bin/python3" -m venv "/v" && "/v/bin/python" -m pip install '
            '"PyYAML>=5.1" "jsonschema>=4.18.0"',
            id="create",
        ),
        pytest.param(
            "recreate",
            ["PyYAML", "jsonschema"],
            '"/usr/bin/python3" -m venv --clear "/v" && "/v/bin/python" -m pip install '
            '"PyYAML>=5.1" "jsonschema>=4.18.0"',
            id="recreate",
        ),
        pytest.param(
            "install",
            ["jsonschema"],
            '"/v/bin/python" -m pip install "jsonschema>=4.18.0"',
            id="install_only",
        ),
    ],
)
def test_build_install_command(mode: str, missing: list[str], expected: str) -> None:
    """作る・作り直す・入れるだけを分ける（正常系）。"""
    # 実行
    command = check_env.build_install_command(
        mode,
        missing,
        venv_dir=Path("/v"),
        base_python="/usr/bin/python3",
        os_name="posix",
    )
    # 検証
    assert command == expected


def test_build_install_command_when_none_missing() -> None:
    """入れるものが無ければ None を返す（正常系）。"""
    # 実行
    command = check_env.build_install_command(
        "install",
        [],
        venv_dir=Path("/v"),
        base_python="/usr/bin/python3",
        os_name="posix",
    )
    # 検証
    assert command is None


def test_default_venv_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """ホームの下の .mindmap/venv を返す（正常系）。"""
    # 準備
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    # 実行
    venv_dir = check_env.default_venv_dir()
    # 検証
    assert venv_dir == tmp_path / ".mindmap" / "venv"


@pytest.mark.parametrize(
    ("os_name", "expected"),
    [
        pytest.param("posix", Path("/v/bin/python"), id="posix"),
        pytest.param("nt", Path("/v/Scripts/python.exe"), id="windows"),
    ],
)
def test_venv_python_path(os_name: str, expected: Path) -> None:
    """OS で Python の場所を分ける（正常系）。"""
    # 実行
    python_path = check_env.venv_python_path(Path("/v"), os_name=os_name)
    # 検証
    assert python_path == expected


def test_probe_venv() -> None:
    """テストを動かす Python に尋ねる（正常系）。"""
    # 実行
    result = check_env.probe_venv(Path(sys.executable))
    # 検証
    assert result is not None
    assert result["python"] == platform.python_version()
    assert "PyYAML" in result["packages"]
    assert "jsonschema" in result["packages"]


@pytest.mark.parametrize(
    "run",
    [
        pytest.param(_run_raising_os_error, id="os_error"),
        pytest.param(_run_returning(1, ""), id="exit_code_1"),
        pytest.param(_run_returning(0, "x"), id="not_json"),
    ],
)
def test_probe_venv_when_failed(
    run: Callable[..., subprocess.CompletedProcess[str]],
) -> None:
    """起動できないか出力が読めなければ None を返す（異常系）。"""
    # 実行
    result = check_env.probe_venv(Path("/v/bin/python"), run=run)
    # 検証
    assert result is None
