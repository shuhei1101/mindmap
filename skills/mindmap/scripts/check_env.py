"""スキル専用の仮想環境の Python の版と、PyYAML・jsonschema の版を確かめる。

PyYAML・jsonschema を読まずに動かすため、Python 3.8 で読める構文だけで書く。
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

# Python の版の下限
MIN_PYTHON = (3, 12)

# 配布名 → 版の下限
REQUIREMENTS = {"PyYAML": "5.1", "jsonschema": "4.18.0"}

# 仮想環境の Python に版を尋ねるときに待つ秒数の上限
PROBE_TIMEOUT_SEC = 30

# 仮想環境の Python に `-c` で渡すコード。版と配布名ごとの版（無ければ null）を JSON で出す
PROBE_SCRIPT = "\n".join(
    [
        "import json, platform",
        "try:",
        "    from importlib.metadata import PackageNotFoundError, version",
        "except ImportError:",
        "    version = None",
        "found = {}",
        "for name in " + json.dumps(list(REQUIREMENTS)) + ":",
        "    if version is None:",
        "        found[name] = None",
        "        continue",
        "    try:",
        "        found[name] = version(name)",
        "    except PackageNotFoundError:",
        "        found[name] = None",
        'print(json.dumps({"python": platform.python_version(), "packages": found}))',
    ]
)


class _CheckEnvError(Exception):
    """依存の確認の結果を持つ例外の親。入口がその結果を標準出力に出して終了コード 1 にする。"""

    def __init__(self, report: dict[str, Any]) -> None:
        """メッセージと、依存の確認の結果を持つ。"""
        super().__init__("依存が足りません")
        self.report = report


class PythonVersionError(_CheckEnvError):
    """仮想環境の Python の版が下限より古いか、版を引けない。"""


class DependencyMissingError(_CheckEnvError):
    """ライブラリが無いか下限より古い。"""


class VenvNotFoundError(_CheckEnvError):
    """仮想環境の Python が無い。"""


def default_venv_dir() -> Path:
    """スキル専用の仮想環境のフォルダ（`~/.mindmap/venv`）を返す。"""
    return Path.home() / ".mindmap" / "venv"


def venv_python_path(venv_dir: Path, os_name: str = os.name) -> Path:
    """仮想環境のフォルダから、その Python の場所を返す。"""
    # Windows は Scripts/python.exe、それ以外は bin/python
    if os_name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def parse_version(text: str) -> tuple[int, ...]:
    """版の文字列を、各部分の先頭の数字を並べた比べられる整数の組にする。"""
    numbers: list[int] = []
    for part in text.split("."):
        matched = re.match(r"[0-9]+", part)
        # 先頭が数字でない部分が出たらそこで打ち切る
        if matched is None:
            break
        numbers.append(int(matched.group(0)))
    return tuple(numbers)


def build_install_command(
    mode: str,
    missing: list[str],
    *,
    venv_dir: Path,
    base_python: str,
    os_name: str = os.name,
) -> str | None:
    """仮想環境とライブラリをそろえる 1 行のコマンドを作る。入れるものが無ければ None を返す。"""
    # ライブラリだけ入れるときに入れるものが無ければ、コマンドは要らない
    if mode == "install" and not missing:
        return None
    steps = []
    # 作る・作り直すときは、仮想環境を作るコマンドを先頭に置く
    if mode == "create":
        steps.append(f'"{base_python}" -m venv "{venv_dir}"')
    elif mode == "recreate":
        steps.append(f'"{base_python}" -m venv --clear "{venv_dir}"')
    requirements = " ".join(f'"{name}>={REQUIREMENTS[name]}"' for name in missing)
    steps.append(f'"{venv_python_path(venv_dir, os_name)}" -m pip install {requirements}')
    return " && ".join(steps)


def probe_venv(
    python_path: Path,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any] | None:
    """仮想環境の Python を子プロセスで起動し、版とライブラリの版を受け取る。"""
    try:
        # 配列のまま渡して、シェルを通さない
        completed = run(
            [str(python_path), "-c", PROBE_SCRIPT],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=PROBE_TIMEOUT_SEC,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        # 起動できない・時間内に終わらない: 版を引けない
        return None
    if completed.returncode != 0:
        return None
    try:
        probed = json.loads(completed.stdout)
    except ValueError:
        # 出力を JSON として読めない
        return None
    return probed if isinstance(probed, dict) else None


def run_check_env(
    venv_dir: Path,
    probe: Callable[[Path], dict[str, Any] | None] = probe_venv,
    *,
    base_python: str = sys.executable,
    base_version: tuple[Any, ...] = tuple(sys.version_info),
) -> dict[str, Any]:
    """仮想環境の Python の版とライブラリの版を確かめ、足りなければ結果を持った例外を送る。"""
    base_numbers = tuple(base_version)[:3]
    # 仮想環境を作る Python が下限以上か（古ければ作る・作り直すコマンドを返せない）
    base_python_ok = base_numbers >= MIN_PYTHON
    python_path = venv_python_path(venv_dir)
    report: dict[str, Any] = {
        "base_python": base_python,
        "base_python_version": ".".join(str(number) for number in base_numbers),
        "base_python_ok": base_python_ok,
        "venv_dir": str(venv_dir),
        "python_path": str(python_path),
    }

    def _command(mode: str, missing: list[str]) -> str | None:
        """仮想環境を作る Python が下限以上のときだけ、そろえるコマンドを作る。"""
        if not base_python_ok:
            return None
        return build_install_command(mode, missing, venv_dir=venv_dir, base_python=base_python)

    # 仮想環境の Python が無い: 作って入れるコマンドを返す
    if not python_path.exists():
        report.update(
            venv_ok=False,
            python=None,
            python_ok=False,
            packages=_package_rows({}),
            install=_command("create", list(REQUIREMENTS)),
        )
        raise VenvNotFoundError(report)

    report["venv_ok"] = True
    probed = probe(python_path)
    python = probed.get("python") if probed else None
    versions = probed.get("packages") if probed else None
    packages = _package_rows(versions if isinstance(versions, dict) else {})
    python_ok = python is not None and parse_version(python) >= MIN_PYTHON
    report.update(python=python, python_ok=python_ok, packages=packages)

    # 仮想環境の Python が古い・版を引けない: 作り直して入れるコマンドを返す
    if not python_ok:
        report["install"] = _command("recreate", list(REQUIREMENTS))
        raise PythonVersionError(report)
    # ライブラリが無い・古い: 足りないものを入れるコマンドを返す
    missing = [row["name"] for row in packages if not row["ok"]]
    if missing:
        report["install"] = _command("install", missing)
        raise DependencyMissingError(report)
    report["install"] = None
    return report


def _package_rows(installed: dict[str, Any]) -> list[dict[str, Any]]:
    """配布名ごとに、下限・入っている版・下限以上かを並べる。"""
    rows = []
    for name, required in REQUIREMENTS.items():
        version = installed.get(name)
        rows.append(
            {
                "name": name,
                "required": required,
                "installed": version,
                "ok": version is not None and parse_version(version) >= parse_version(required),
            }
        )
    return rows
