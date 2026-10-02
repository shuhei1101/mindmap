"""mindmap.py（入口：引数の解釈・振り分け・出力）の単体テスト。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

import check_env
import mindmap
from fixture_types import MakeWorkspace

# check-env の結果として返す、揃っているときの結果
GOOD_REPORT: dict[str, Any] = {"python": "3.12.3", "python_ok": True, "install": None}

# check-env の結果として返す、足りないものがあるときの結果
MISSING_REPORT: dict[str, Any] = {
    "python": "3.12.3",
    "python_ok": True,
    "install": '"/v/bin/python" -m pip install "PyYAML>=5.1"',
}


def _raise_dependency_missing(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """足りないライブラリがあるときの例外を送る run_check_env の代わり。"""
    raise check_env.DependencyMissingError(MISSING_REPORT)


def _patch_run_check_env(monkeypatch: pytest.MonkeyPatch, fake: Any) -> None:
    """依存の確認の関数を、入口がどちらの形で読んでいても差し替える。"""
    # 依存の確認のモジュールの関数と、入口が名前で取り込んだ関数の両方を差し替える
    monkeypatch.setattr(check_env, "run_check_env", fake)
    monkeypatch.setattr(mindmap, "run_check_env", fake, raising=False)


def test_main_when_check_env(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """check-env は commands を読まずに結果を出す（正常系）。"""
    # 準備
    _patch_run_check_env(monkeypatch, lambda *args, **kwargs: GOOD_REPORT)
    monkeypatch.delitem(sys.modules, "commands", raising=False)
    # 実行
    exit_code = mindmap.main(["check-env"])
    # 検証
    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == GOOD_REPORT
    assert "commands" not in sys.modules


def test_main_when_dependency_missing(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """依存が足りなければ結果を出して 1 を返す（正常系）。"""
    # 準備
    _patch_run_check_env(monkeypatch, _raise_dependency_missing)
    # 実行
    exit_code = mindmap.main(["check-env"])
    # 検証
    assert exit_code == 1
    assert json.loads(capsys.readouterr().out) == MISSING_REPORT


def test_main_when_mindmap_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """コマンドのエラーは標準エラーと終了コード 1 にする（正常系）。"""
    # 実行
    exit_code = mindmap.main(["status", "--workspace", str(tmp_path)])
    # 検証
    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.err.startswith("エラー: ")
    assert str(tmp_path) in captured.err
    assert captured.out == ""


def test_main(make_workspace: MakeWorkspace, capsys: pytest.CaptureFixture[str]) -> None:
    """コマンドの結果を JSON で出す（正常系）。"""
    # 準備
    root = make_workspace()
    # 実行
    exit_code = mindmap.main(["attrs", "--workspace", str(root)])
    # 検証
    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {"attrs": []}


def test_build_parser() -> None:
    """繰り返しの --attr と位置引数を解釈する（正常系）。"""
    # 準備
    parser = mindmap.build_parser()
    # 実行
    find_args = parser.parse_args(["find", "--workspace", "w", "--attr", "a=1", "--attr", "b"])
    adopt_args = parser.parse_args(["adopt", "D-1", "B", "--workspace", "w"])
    # 検証
    assert find_args.attr == ["a=1", "b"]
    assert adopt_args.id == "D-1"
    assert adopt_args.key == "B"


def test_build_parser_when_limit_invalid() -> None:
    """1 より小さい --limit は引数の誤りにする（異常系）。"""
    # 準備
    parser = mindmap.build_parser()
    # 実行・検証
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["next", "--workspace", "w", "--limit", "0"])
    assert exc_info.value.code == 2
