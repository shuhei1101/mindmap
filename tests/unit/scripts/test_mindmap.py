"""mindmap.py（入口：引数の解釈・振り分け・出力）の単体テスト。"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from typing import Any

import pytest
import yaml

import check_env
import mindmap
from fixture_types import MakeLegacyWorkspace, MakeWorkspace

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


def _fail_on_read(*args: Any, **kwargs: Any) -> str:
    """読まれたら失敗する標準入力の read の代わり。"""
    raise AssertionError("標準入力を読んではいけません")


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


def test_main_when_legacy_format(
    make_legacy_workspace: MakeLegacyWorkspace, capsys: pytest.CaptureFixture[str]
) -> None:
    """前の版の形式のスキーマ違反には /mindstella:upgrade を案内する（正常系）。"""
    # 準備
    root = make_legacy_workspace(legacy_docs={"A-1": True})
    # 実行
    exit_code = mindmap.main(["build", "--workspace", str(root)])
    # 検証
    captured = capsys.readouterr()
    assert exit_code == 1
    assert (
        captured.err.splitlines()[-1]
        == "ヒント: 前の版の形式の記録は /mindstella:upgrade で今の形式に移せます"
    )


def test_main_when_out_invalid(
    make_workspace: MakeWorkspace, capsys: pytest.CaptureFixture[str]
) -> None:
    """書き出す先の誤りは終了コード 2（正常系）。"""
    # 準備
    root = make_workspace()
    # 実行
    exit_code = mindmap.main(
        ["export", "--workspace", str(root), "--out", str(root / "preview.html")]
    )
    # 検証
    captured = capsys.readouterr()
    assert exit_code == 2
    assert "--out" in captured.err
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
    """繰り返しの --attr・--set と位置引数を解釈する（正常系）。"""
    # 準備
    # 版のモジュールを読めない間も、このファイルの他のテストの収集を止めないよう、使うときに読む
    from versions import Version

    parser = mindmap.build_parser()
    # 実行
    find_args = parser.parse_args(["find", "--workspace", "w", "--attr", "a=1", "--attr", "b"])
    adopt_args = parser.parse_args(["adopt", "D-1", "B", "--workspace", "w"])
    set_args = parser.parse_args(
        [
            "migrate",
            "--workspace",
            "w",
            "--set",
            "mindmap.yaml:summary=題名",
            "--set",
            "docs.yaml:x=1",
        ]
    )
    plan_args = parser.parse_args(
        ["migrate", "--workspace", "w", "--plan", "--from", "v0.2.0", "--to", "v0.3.0"]
    )
    # 検証
    assert find_args.attr == ["a=1", "b"]
    assert adopt_args.id == "D-1"
    assert adopt_args.key == "B"
    assert set_args.set == [("mindmap.yaml", "summary", "題名"), ("docs.yaml", "x", "1")]
    assert plan_args.plan is True
    assert vars(plan_args)["from"] == Version(0, 2, 0)
    assert plan_args.to == Version(0, 3, 0)


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(["next", "--workspace", "w", "--limit", "0"], id="limit_zero"),
        pytest.param(["migrate", "--workspace", "w", "--to", "0.3"], id="version_invalid"),
        pytest.param(["migrate", "--workspace", "w", "--set", "summary"], id="set_invalid"),
        pytest.param(["migrate", "--workspace", "w", "--plan", "--record"], id="plan_and_record"),
    ],
)
def test_build_parser_when_limit_invalid(argv: list[str]) -> None:
    """引数の誤りは終了コード 2 にする（異常系）。"""
    # 準備
    parser = mindmap.build_parser()
    # 実行・検証
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(argv)
    assert exc_info.value.code == 2


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        pytest.param(
            ["init", "--workspace", "w", "--json", '{"field": "システム開発"}'],
            '{"field": "システム開発"}',
            id="init",
        ),
        pytest.param(
            ["add", "note", "--workspace", "w", "--json", '{"title": "メモ"}'],
            '{"title": "メモ"}',
            id="add",
        ),
        pytest.param(
            ["update", "D-1", "--workspace", "w", "--json", '{"status": "保留"}'],
            '{"status": "保留"}',
            id="update",
        ),
        pytest.param(["add", "note", "--workspace", "w"], None, id="omitted"),
    ],
)
def test_build_parser_when_json(argv: list[str], expected: str | None) -> None:
    """init・add・update の --json を解釈する（正常系）。"""
    # 準備
    parser = mindmap.build_parser()
    # 実行
    args = parser.parse_args(argv)
    # 検証
    assert args.json == expected


def test_main_when_json_argument(
    make_workspace: MakeWorkspace,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--json を渡したら、標準入力を読まずにその中身で足す（正常系）。"""
    # 準備
    root = make_workspace()
    json_text = json.dumps({"title": "利用者's メモ", "content": "メモの中身"}, ensure_ascii=False)
    monkeypatch.setattr(sys, "stdin", types.SimpleNamespace(read=_fail_on_read))
    # 実行
    exit_code = mindmap.main(["add", "note", "--workspace", str(root), "--json", json_text])
    # 検証
    assert exit_code == 0
    assert json.loads(capsys.readouterr().out)["id"] == "N-1"
    notes = yaml.safe_load((root / "notes.yaml").read_text(encoding="utf-8"))
    assert notes["items"][0]["title"] == "利用者's メモ"
