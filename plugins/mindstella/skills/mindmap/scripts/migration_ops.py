"""移し替えの手順の操作ごとの当て方と、手順の 1 行の説明。"""

from __future__ import annotations

import copy
import importlib.util
import json
import os
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from store import dump_yaml, write_temp

if TYPE_CHECKING:
    # migrator がこのモジュールを読むので、型の注釈のためだけに読む
    from migrator import MigrationStep, NeededValue

# 利用者に当ててよいかを確かめる操作
DESTRUCTIVE_OPS = frozenset({"rename_file", "move_dir", "delete"})

# 項目ごとに当てる操作が、各項目の位置を示すときの接頭辞
ITEMS_PREFIX = "items[]."

# `call` が呼ぶ変換の関数の名前
CALL_FUNCTION = "migrate"


class StepError(Exception):
    """1 つの手順が失敗した理由。`apply_migration` が写しから戻して版と番号を添えた `StepFailedError` にする。"""


def apply_step(root: Path, step: MigrationStep) -> list[str]:
    """操作ごとに手順を当て、変えたファイル・フォルダ（ワークスペースからの相対パス）を返す。何も変えなければ空。"""
    args = step.args
    if step.op in ("rename_file", "move_dir"):
        return _move(root, args["from"], args["to"])
    if step.op == "delete":
        return _delete(root, args["path"])
    if step.op == "call":
        return _call(root, step)
    return _apply_yaml_step(root, step)


def describe_step(step: MigrationStep) -> str:
    """出力の `steps[].summary` にする、手順の中身の 1 行を作る。"""
    args = step.args
    prefix = ITEMS_PREFIX if args.get("each_item") else ""
    if step.op == "rename_file":
        return f"{args['from']} を {args['to']} に名前を変える"
    if step.op == "move_dir":
        return f"{args['from']} を {args['to']} へ移す"
    if step.op == "delete":
        return f"{args['path']} を消す"
    if step.op == "call":
        return f"{args['script']} の変換を当てる"
    if step.op == "rename_key":
        return f"{args['file']} の {prefix}{args['from']} を {args['to']} に名前を変える"
    if step.op == "map_values":
        pairs = "、".join(f"{_show(old)} → {_show(new)}" for old, new in args["map"].items())
        return f"{args['file']} の {prefix}{args['key']} の値を置き換える（{pairs}）"
    # set_default: 値が要るときは利用者に聞く
    if "ask" in args:
        return f"{args['file']} の {prefix}{args['key']} を利用者に聞く（{args['ask']}）"
    value = json.dumps(args["value"], ensure_ascii=False)
    return f"{args['file']} の {prefix}{args['key']} が無ければ {value} を足す"


def list_needed_values(root: Path, step: MigrationStep) -> list[NeededValue]:
    """`set_default` の `ask` で、今のワークスペースにキーが無いものを返す。"""
    # 移し替えのモジュールがこのモジュールを読むので、使うときに読む
    from migrator import NeededValue

    args = step.args
    # 値が要る手順だけを見る
    if step.op != "set_default" or "ask" not in args:
        return []
    try:
        data = _read_yaml(root, args["file"])
    except StepError:
        # 読めないことは、手順を当てるときに失敗として扱う
        return []
    targets = _targets(data, bool(args["each_item"]))
    if any(args["key"] not in target for target in targets):
        return [NeededValue(file=args["file"], key=args["key"], description=args["ask"])]
    return []


def _move(root: Path, source: str, destination: str) -> list[str]:
    """ファイル・フォルダを動かす。動かす元が無ければ飛ばし、動かす先があれば送る。"""
    source_path = _resolve(root, source)
    destination_path = _resolve(root, destination)
    # 動かす元が無い: 既に動かした後として飛ばす
    if not source_path.exists():
        return []
    # 動かす先が既にある
    if destination_path.exists():
        raise StepError(f"動かす先が既にあります: {destination}")
    try:
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.rename(destination_path)
    except OSError as error:
        raise StepError(
            f"{source} を {destination} に動かせません: {error.strerror or error}"
        ) from error
    return [source, destination]


def _delete(root: Path, path: str) -> list[str]:
    """ファイル・フォルダを消す。対象が無ければ飛ばす。"""
    target = _resolve(root, path)
    if not target.exists():
        return []
    try:
        # フォルダは中身ごと、ファイルはそのものを消す
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    except OSError as error:
        raise StepError(f"{path} を消せません: {error.strerror or error}") from error
    return [path]


def _call(root: Path, step: MigrationStep) -> list[str]:
    """手順の版のフォルダの `scripts/{script}.py` を読み込み、`migrate(root)` が返した変えたパスを返す。"""
    script = step.args["script"]
    path = _resolve(step.folder / "scripts", f"{script}.py")
    spec = importlib.util.spec_from_file_location(f"migration_{step.version}_{script}", path)
    if spec is None or spec.loader is None or not path.exists():
        raise StepError(f"変換のスクリプトを読み込めません: {path}")
    module = importlib.util.module_from_spec(spec)
    # 変換のスクリプトが送るどの例外も、手順の失敗として扱う
    try:
        spec.loader.exec_module(module)
        changed = getattr(module, CALL_FUNCTION)(root)
    except Exception as error:
        raise StepError(f"{script} の変換が失敗しました: {error}") from error
    return [str(name) for name in changed]


def _apply_yaml_step(root: Path, step: MigrationStep) -> list[str]:
    """YAML のキーを操作する手順を当てる。中身が変わったときだけ書く。"""
    args = step.args
    file_name = args["file"]
    data = _read_yaml(root, file_name)
    changed = False
    for position, target in enumerate(_targets(data, bool(args["each_item"]))):
        if step.op == "rename_key":
            changed |= _rename_key(target, args["from"], args["to"], _label(target, position))
        elif step.op == "map_values":
            changed |= _map_value(target, args["key"], args["map"])
        else:
            changed |= _set_default(target, args)
    # 何も変えなかったファイルは書かない
    if not changed:
        return []
    _write_yaml(root, file_name, data)
    return [file_name]


def _rename_key(target: dict[str, Any], old: str, new: str, label: str) -> bool:
    """キーの位置を保ったまま名前を変える。`old` が無ければ飛ばし、`new` も持つときは送る。"""
    if old not in target:
        return False
    # 名前を変える先のキーを既に持つ
    if new in target:
        raise StepError(f"{label}: {old} と {new} の両方を持つため、{new} に変えられません")
    renamed = {(new if key == old else key): value for key, value in target.items()}
    target.clear()
    target.update(renamed)
    return True


def _map_value(target: dict[str, Any], key: str, mapping: dict[Any, Any]) -> bool:
    """`key` の値が `mapping` にあれば置き換える。"""
    if key not in target:
        return False
    current = target[key]
    for old, new in mapping.items():
        # 真偽値と整数は == で等しくなるので、型も合わせる
        if type(old) is type(current) and old == current:
            target[key] = new
            return True
    return False


def _set_default(target: dict[str, Any], args: dict[str, Any]) -> bool:
    """キーが無い項目に既定の値を足す。値が要る（`ask`）ときは何も書かない。"""
    if args["key"] in target or "ask" in args:
        return False
    target[args["key"]] = copy.deepcopy(args["value"])
    return True


def _targets(data: Any, each_item: bool) -> list[dict[str, Any]]:
    """手順を当てる辞書を返す。`each_item` なら `items[]` の各項目、そうでなければ最上位の辞書。"""
    if not isinstance(data, dict):
        return []
    if not each_item:
        return [data]
    items = data.get("items")
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def _label(target: dict[str, Any], position: int) -> str:
    """エラーの文に添える項目の呼び名（ID があれば ID、無ければ `items[n]`）。"""
    item_id = target.get("id")
    return item_id if isinstance(item_id, str) else f"items[{position}]"


def _read_yaml(root: Path, file_name: str) -> Any:
    """ワークスペースの YAML を読む。読めなければ送る。"""
    path = _resolve(root, file_name)
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise StepError(f"{file_name} を読めません: {_reason(error)}") from error


def _write_yaml(root: Path, file_name: str, data: Any) -> None:
    """YAML を一時ファイルに書いてから置き換える。"""
    path = _resolve(root, file_name)
    try:
        temp = write_temp(path, dump_yaml(data))
    except OSError as error:
        raise StepError(f"{file_name} を書けません: {error.strerror or error}") from error
    try:
        os.replace(temp, path)
    except OSError as error:
        # 置き換えられなかった一時ファイルは残さない
        temp.unlink(missing_ok=True)
        raise StepError(f"{file_name} を書けません: {error.strerror or error}") from error


def _resolve(base: Path, relative: str) -> Path:
    """基準のフォルダからの相対パスを組み、基準の配下にあることを確かめる。"""
    path = (base / relative).resolve()
    # 基準のフォルダの外を指している
    if not path.is_relative_to(base.resolve()):
        raise StepError(f"ワークスペースの外は指せません: {relative}")
    return path


def _reason(error: Exception) -> str:
    """OSError は理由の文字列を、それ以外は例外の文を 1 行で返す。"""
    if isinstance(error, OSError):
        return error.strerror or str(error)
    return " ".join(str(error).split())


def _show(value: Any) -> str:
    """説明に出す値を文字にする（真偽値は true・false）。"""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
