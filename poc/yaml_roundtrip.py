"""PyYAML の書き戻しと jsonschema のファイルをまたぐ参照を確かめる PoC。"""

from __future__ import annotations

import os
import sys
import tempfile
from importlib.metadata import version
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry
from referencing.jsonschema import DRAFT202012

# 手で書いた検討事項の YAML（日本語・行のコメント・行末のコメント・独自のキーの並び）
HAND_WRITTEN = """\
# 手で書いた行のコメント
items:
  - title: 何のためのスキルか  # 行末のコメント
    id: D-1
    status: 決定済み
    weight: 大
"""

# 共通のスキーマ（状態の値を 1 か所で決める）
COMMON_SCHEMA: dict[str, Any] = {
    "$defs": {"status": {"enum": ["未決定", "決定済み", "要見直し"]}},
}

# 検討事項のスキーマ（状態は共通側を $ref で指す）
DECISIONS_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"status": {"$ref": "common.json#/$defs/status"}},
            },
        },
    },
}


def build_validator() -> Draft202012Validator:
    """共通のスキーマを Registry に登録した検証器を作る。"""
    registry: Registry[Any] = Registry().with_resources(
        [("common.json", DRAFT202012.create_resource(COMMON_SCHEMA))]
    )
    return Draft202012Validator(DECISIONS_SCHEMA, registry=registry)


def write_atomically(path: Path, text: str, *, fail_before_replace: bool = False) -> None:
    """一時ファイルに書いてから os.replace で置き換える。"""
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)
    # 置き換える前に失敗した場合を再現する
    if fail_before_replace:
        os.remove(tmp)
        raise RuntimeError("置き換える前に失敗した")
    os.replace(tmp, path)


def main() -> int:
    """成功条件を 1 つずつ確かめて結果を出す。"""
    print(f"Python {sys.version.split()[0]} / PyYAML {yaml.__version__} / "
          f"jsonschema {version('jsonschema')} / referencing {version('referencing')}")
    validator = build_validator()
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "decisions.yaml"
        path.write_text(HAND_WRITTEN, encoding="utf-8")

        # 読んで検証し、1 項目を書き換えて書き戻す
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        errors = list(validator.iter_errors(data))
        print(f"[検証（正しい値）] エラー {len(errors)} 件")
        data["items"][0]["status"] = "要見直し"
        dumped = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
        write_atomically(path, dumped)
        written = path.read_text(encoding="utf-8")
        print("[書き戻した YAML]")
        print(written)
        print(f"[日本語] エスケープされずに残る: {'何のためのスキルか' in written}")
        keys = list(yaml.safe_load(written)["items"][0].keys())
        print(f"[キーの並び] {keys} 読んだときと同じ: {keys == ['title', 'id', 'status', 'weight']}")
        print(f"[コメント] 行のコメントが残る: {'手で書いた行のコメント' in written} / "
              f"行末のコメントが残る: {'行末のコメント' in written}")

        # 共通側で決めた値に反する状態を入れて検証する
        bad = yaml.safe_load(written)
        bad["items"][0]["status"] = "完了"
        for error in validator.iter_errors(bad):
            print(f"[ファイルをまたぐ参照・検証エラーの場所] {path.name}: "
                  f"{list(error.absolute_path)} {error.message}")

        # 置き換える前に失敗しても元のファイルが変わらないか
        before = path.read_text(encoding="utf-8")
        try:
            write_atomically(path, "壊れた中身", fail_before_replace=True)
        except RuntimeError:
            pass
        leftovers = [p.name for p in Path(d).iterdir() if p.suffix == ".tmp"]
        print(f"[書き込みの原子性] 元のファイルが変わらない: {path.read_text(encoding='utf-8') == before}"
              f" / 一時ファイルの残り: {leftovers}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
