"""mindmap のスクリプトの入口。引数を解釈してコマンドを実行し、結果を JSON で標準出力に出す。

使い方（`{スキルのフォルダ}` はスキル mindmap のフォルダ）:
python3 {スキルのフォルダ}/scripts/mindmap.py {コマンド} [引数]

`check-env` が PyYAML・jsonschema を読まずに答えられるよう、Python 3.8 で読める構文だけで書く。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from check_env import (
    DependencyMissingError,
    PythonVersionError,
    VenvNotFoundError,
    default_venv_dir,
    run_check_env,
)
from launcher import format_relaunch_error, relaunch_if_needed

# `add` の種類（kinds.py の `KINDS` のキー。kinds.py は 3.12 の構文なので、ここでは読まずに写す）
KIND_NAMES = ("decision", "task", "research", "doc", "term", "note", "log")


def main(argv: list[str] | None = None) -> int:
    """引数を解釈してコマンドを実行し、出力と終了コードを決める。"""
    arguments = sys.argv[1:] if argv is None else argv
    # 引数を解釈する前に、起動した Python で動けるかを確かめる
    try:
        relaunched = relaunch_if_needed(arguments, script=Path(__file__).resolve())
    except (VenvNotFoundError, PythonVersionError, DependencyMissingError) as error:
        # 起動し直せない: 標準エラーに出して終了コード 1（標準出力には何も出さない）
        for line in format_relaunch_error(error):
            print(line, file=sys.stderr)
        return 1
    # 仮想環境の Python で起動し直した: 子プロセスの終了コードをそのまま返す
    if relaunched is not None:
        return relaunched

    args = build_parser().parse_args(arguments)
    # check-env: ライブラリを読み込まずに、仮想環境の状態を答える
    if args.command == "check-env":
        return _run_check_env_command(args.venv)

    # それ以外: 依存の確認を通った環境で動くので、3.12 の書き方のモジュールをここで読む
    import commands
    from errors import MindmapError, SchemaMismatchError, SummaryRequiredError
    from store import LEGACY_HINT

    try:
        payload, exit_code = _run_command(commands, args)
    except SummaryRequiredError as error:
        # 題名が要る（引数の誤り）: 標準エラーに出して終了コード 2
        print(f"エラー: {error}", file=sys.stderr)
        return 2
    except MindmapError as error:
        # コマンドのエラー: 標準エラーに出して終了コード 1（標準出力には何も出さない）
        print(f"エラー: {error}", file=sys.stderr)
        for line in error.lines:
            print(line, file=sys.stderr)
        # 前の版の形式のスキーマ違反: 最後に migrate を案内する
        if isinstance(error, SchemaMismatchError) and error.legacy:
            print(LEGACY_HINT, file=sys.stderr)
        return 1
    print(json.dumps(payload, ensure_ascii=False))
    return exit_code


def build_parser() -> argparse.ArgumentParser:
    """15 のコマンドと引数を持つ ArgumentParser を作る。"""
    parser = argparse.ArgumentParser(
        prog="mindmap.py", description="ワークスペースの YAML を読み書き・検索・点検する"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_env_parser = subparsers.add_parser("check-env", help="依存を確かめる")
    check_env_parser.add_argument(
        "--venv", type=Path, default=default_venv_dir(), help="確かめる仮想環境のフォルダ"
    )

    def add_command(name: str, help_text: str) -> argparse.ArgumentParser:
        """`--workspace` を必須で持つサブコマンドを足す。"""
        subparser = subparsers.add_parser(name, help=help_text)
        subparser.add_argument(
            "--workspace", type=Path, required=True, help="ワークスペースのフォルダ"
        )
        return subparser

    init_parser = add_command("init", "設定を受け取って空のワークスペースを作る")
    _add_json_argument(init_parser, "設定の JSON")
    add_parser = add_command("add", "1 項目を足す")
    add_parser.add_argument("kind", choices=KIND_NAMES, help="足す項目の種類")
    _add_json_argument(add_parser, "項目の中身の JSON")
    update_parser = add_command("update", "1 項目のキーを置き換える")
    update_parser.add_argument("id", help="直す項目の ID")
    _add_json_argument(update_parser, "置き換えるキーの JSON")
    adopt_parser = add_command("adopt", "検討事項の採用する案を切り替える")
    adopt_parser.add_argument("id", help="検討事項の ID")
    adopt_parser.add_argument("key", help="採用する案の記号")
    add_command("status", "再開時の状況を返す")
    next_parser = add_command("next", "前提が揃った未決定を順に返す")
    next_parser.add_argument("--limit", type=_positive_int, help="返す候補の件数の上限")
    impact_parser = add_command("impact", "影響を受ける項目を返す")
    impact_parser.add_argument("id", help="起点の項目の ID")
    find_parser = add_command("find", "条件に合う項目を返す")
    find_parser.add_argument("--text", help="文字の欄に含まれる文字")
    find_parser.add_argument("--kind", choices=KIND_NAMES, help="種類")
    find_parser.add_argument("--status", help="状態")
    find_parser.add_argument("--tag", help="タグ")
    find_parser.add_argument("--target", help="対象")
    find_parser.add_argument("--category", help="カテゴリー")
    find_parser.add_argument("--phase", help="フェーズ")
    find_parser.add_argument(
        "--attr", action="append", help="`名前=値` か `名前`（繰り返し渡せる）"
    )
    show_parser = add_command("show", "1 項目の中身・本文・参照元を返す")
    show_parser.add_argument("id", help="表示する項目の ID")
    add_command("attrs", "使っている属性名と件数を返す")
    add_command("check", "スキーマ違反・参照切れ・本文のずれを洗い出す")
    add_command("build", "記録を埋め込んだ preview.html を書き出す")
    add_command("goal", "ゴールに届いたかと残りを返す")
    migrate_parser = add_command("migrate", "前の版の形式を今の形式に移す")
    migrate_parser.add_argument(
        "--summary", default=None, help="設定に足す題名（設定が題名を持たないときに渡す）"
    )
    return parser


def _add_json_argument(parser: argparse.ArgumentParser, what: str) -> None:
    """中身の JSON を標準入力の代わりに引数で渡す `--json` を足す。"""
    parser.add_argument("--json", help=f"{what}（渡したときは標準入力を読まない）")


def _read_json_input(args: argparse.Namespace) -> str:
    """`--json` があればその値を、無ければ標準入力を読んで返す。"""
    return args.json if args.json is not None else sys.stdin.read()


def _positive_int(text: str) -> int:
    """1 以上の整数として読む（それ以外は引数の誤りにする）。"""
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"整数ではありません: {text}") from None
    # 1 より小さい値は件数として使えない
    if value < 1:
        raise argparse.ArgumentTypeError(f"1 以上の整数を渡してください: {text}")
    return value


def _run_check_env_command(venv_dir: Path) -> int:
    """依存の確認の結果を標準出力に出し、足りないときは終了コード 1 にする。"""
    try:
        report = run_check_env(venv_dir)
    except (VenvNotFoundError, PythonVersionError, DependencyMissingError) as error:
        # 足りない: 結果（足りないものと入れるコマンド）を同じ形で出して 1
        print(json.dumps(error.report, ensure_ascii=False))
        return 1
    print(json.dumps(report, ensure_ascii=False))
    return 0


def _run_command(commands: Any, args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    """コマンド名に合う処理を呼び、出力の辞書と終了コードを返す。"""
    from query import SearchFilter, parse_attr

    root = args.workspace
    handlers = {
        "init": lambda: commands.run_init(root, _read_json_input(args)),
        "add": lambda: commands.run_add(root, args.kind, _read_json_input(args)),
        "update": lambda: commands.run_update(root, args.id, _read_json_input(args)),
        "adopt": lambda: commands.run_adopt(root, args.id, args.key),
        "status": lambda: commands.run_status(root),
        "next": lambda: commands.run_next(root, args.limit),
        "impact": lambda: commands.run_impact(root, args.id),
        "find": lambda: commands.run_find(
            root,
            SearchFilter(
                text=args.text,
                kind=args.kind,
                status=args.status,
                tag=args.tag,
                target=args.target,
                category=args.category,
                phase=args.phase,
                attrs=[parse_attr(text) for text in args.attr or []],
            ),
        ),
        "show": lambda: commands.run_show(root, args.id),
        "attrs": lambda: commands.run_attrs(root),
        "check": lambda: commands.run_check(root),
        "build": lambda: commands.run_build(root),
        "goal": lambda: commands.run_goal(root),
        "migrate": lambda: commands.run_migrate(root, summary=args.summary),
    }
    return handlers[args.command]()


if __name__ == "__main__":
    sys.exit(main())
