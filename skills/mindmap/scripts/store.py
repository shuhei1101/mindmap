"""ワークスペースの YAML と本文の読み込み・検証・採番・書き込み。"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry
from referencing.jsonschema import DRAFT202012

from errors import (
    ItemNotFoundError,
    SchemaMismatchError,
    WorkspaceExistsError,
    WorkspaceNotFoundError,
    WriteFailedError,
)
from kinds import (
    BODY_DIR,
    HANDOFF_DIR,
    KINDS,
    SETTINGS_FILE,
    Kind,
    kind_of_id,
)

# このファイルから見た `skills/mindmap/schemas/`
SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"

# Registry に登録し、各種類のスキーマが `$ref` で指す共通のスキーマの名前
COMMON_SCHEMA = "common.schema.json"

# `mindmap.yaml` を検証するスキーマ
SETTINGS_SCHEMA = "settings.schema.json"

# 置き換える前に書く一時ファイルの拡張子（置き換えるファイルと同じフォルダに作る）
TEMP_SUFFIX = ".tmp"

# 置き換え先が無いときの一時ファイルの権限（umask で削る前の値）
DEFAULT_FILE_MODE = 0o666

# 一番上など、キーのパスが空のときの表記
WHOLE_PATH = "(全体)"

# 前の版の形式でスキーマに合わないときに、エラーの最後に続ける 1 行
LEGACY_HINT = "ヒント: 前の版の形式の記録は migrate で今の形式に移せます"


@dataclass(frozen=True, slots=True, kw_only=True)
class Problem:
    """スキーマ違反・参照切れなど 1 件の問題。"""

    kind: Literal["schema", "duplicate_id", "broken_ref", "missing_body", "orphan_body"]
    # ワークスペースからの相対パス
    file: str
    # 問題のある項目の ID
    id: str | None
    # `items[0].status` の形のキーのパス
    key: str | None
    # 中身（参照先の ID・スキーマの理由など）
    detail: str


@dataclass(frozen=True, slots=True, kw_only=True)
class Workspace:
    """読み込んだ設定・種類ごとの項目・読めなかったファイル。"""

    # ワークスペースのフォルダ（絶対パス）
    root: Path
    # ファイル名 → 読んだ値そのまま。YAML として読めないファイルは含めない
    raw: dict[str, Any]
    # `mindmap.yaml` の値。辞書でない・読めないときは空
    settings: dict[str, Any]
    # 種類ごとの `items`（ファイルの並びのまま）。形が合わないときは空
    items: dict[Kind, list[dict[str, Any]]]
    # YAML として読めなかったファイル
    load_problems: list[Problem]


@dataclass(frozen=True, slots=True, kw_only=True)
class ItemRef:
    """ID で引いた項目と、その種類・並びの位置。"""

    kind: Kind
    # `items` の中の位置
    index: int
    item: dict[str, Any]


@dataclass(frozen=True, slots=True, kw_only=True)
class BodyWrite:
    """`docs/` に書く 1 つの本文。"""

    # `docs/` の中のファイル名（`{ID}.md`）
    name: str
    # 本文の Markdown
    text: str


@dataclass(frozen=True, slots=True, kw_only=True)
class Change:
    """1 つの種類の項目の並びを丸ごと置き換える変更と、一緒に書く本文。"""

    kind: Kind
    # 書き換えた後の `items` の並び全体
    items: list[dict[str, Any]]
    body: BodyWrite | None = None


def load_workspace(root: Path) -> Workspace:
    """設定と 7 種類の YAML を読む。読めないファイルは問題に記録して空として扱う。"""
    root = root.resolve()
    # mindmap.yaml が無いフォルダはワークスペースではない
    if not (root / SETTINGS_FILE).is_file():
        raise WorkspaceNotFoundError(f"ワークスペースがありません: {root}")

    raw: dict[str, Any] = {}
    load_problems: list[Problem] = []
    for file_name in [SETTINGS_FILE, *(spec.file for spec in KINDS.values())]:
        path = root / file_name
        # 種類のファイルが無い: 項目が 0 件のものとして扱う
        if not path.is_file():
            raw[file_name] = {"items": []}
            continue
        try:
            raw[file_name] = _read_yaml(path)
        except yaml.YAMLError as error:
            # YAML として読めない: 問題に記録し、raw には入れない
            load_problems.append(
                Problem(
                    kind="schema",
                    file=file_name,
                    id=None,
                    key=WHOLE_PATH,
                    detail=f"YAML として読めません: {' '.join(str(error).split())}",
                )
            )

    settings = raw.get(SETTINGS_FILE)
    return Workspace(
        root=root,
        raw=raw,
        settings=settings if isinstance(settings, dict) else {},
        items={kind: _extract_items(raw.get(spec.file)) for kind, spec in KINDS.items()},
        load_problems=load_problems,
    )


def validate_workspace(workspace: Workspace) -> list[Problem]:
    """設定と 7 種類をスキーマと突き合わせ、合わない箇所を問題の並びにする。"""
    validators = load_validators()
    # ファイル名の順・同じファイルの中はキーのパスの順に並べるための (ファイル名, パスの順, 問題)
    entries: list[tuple[str, tuple[tuple[int, Any], ...], Problem]] = [
        (problem.file, (), problem) for problem in workspace.load_problems
    ]
    schema_by_file = {SETTINGS_FILE: SETTINGS_SCHEMA}
    schema_by_file.update({spec.file: spec.schema for spec in KINDS.values()})
    for file_name, schema_name in schema_by_file.items():
        # 読めなかったファイルは load_problems が持っているので突き合わせない
        if file_name not in workspace.raw:
            continue
        value = workspace.raw[file_name]
        for error in validators[schema_name].iter_errors(value):
            path = list(error.absolute_path)
            problem = Problem(
                kind="schema",
                file=file_name,
                id=_item_id_at(value, path),
                key=_format_path(path),
                detail=error.message,
            )
            entries.append((file_name, _path_order(path), problem))
    entries.sort(key=lambda entry: (entry[0], entry[1]))
    return [problem for _, _, problem in entries]


def load_validators() -> dict[str, Draft202012Validator]:
    """共通のスキーマを Registry に登録し、設定と 7 種類の検証器を作る。"""
    common = json.loads((SCHEMA_DIR / COMMON_SCHEMA).read_text(encoding="utf-8"))
    # 各種類のスキーマが `common.schema.json#/$defs/...` で指せるように登録する
    registry = Registry().with_resources([(COMMON_SCHEMA, DRAFT202012.create_resource(common))])
    schema_names = [SETTINGS_SCHEMA, *(spec.schema for spec in KINDS.values())]
    validators: dict[str, Draft202012Validator] = {}
    for schema_name in schema_names:
        schema = json.loads((SCHEMA_DIR / schema_name).read_text(encoding="utf-8"))
        validators[schema_name] = Draft202012Validator(schema, registry=registry)
    return validators


def find_item(workspace: Workspace, item_id: str) -> ItemRef:
    """ID で項目を引く。"""
    kind = kind_of_id(item_id)
    # 形が合わないか、頭の文字がどの種類にも当たらない
    if kind is None:
        raise ItemNotFoundError(f"項目がありません: {item_id}")
    for index, item in enumerate(workspace.items[kind]):
        if item.get("id") == item_id:
            return ItemRef(kind=kind, index=index, item=item)
    # その種類に ID の項目が無い
    raise ItemNotFoundError(f"項目がありません: {item_id}")


def next_id(workspace: Workspace, kind: Kind) -> str:
    """その種類の連番の最大 + 1 の ID を返す。"""
    numbers = [
        int(item_id.split("-", 1)[1])
        for item_id in (item.get("id") for item in workspace.items[kind])
        if isinstance(item_id, str) and kind_of_id(item_id) == kind
    ]
    return f"{KINDS[kind].prefix}-{max(numbers, default=0) + 1}"


def now_utc() -> str:
    """今の日時を UTC のタイムゾーン付き ISO 8601（秒まで）で返す。"""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def build_mismatch_error(
    problems: list[Problem], workspace: Workspace | None = None
) -> SchemaMismatchError:
    """問題ごとの `{ファイル名}: {キーのパス}: {理由}` の行を持つ例外を作る。workspace を渡すと前の版の形式の問題かも決める。"""
    lines = [
        f"{problem.file}: {problem.key or WHOLE_PATH}: {problem.detail}" for problem in problems
    ]
    legacy = workspace is not None and any(is_legacy_problem(p, workspace) for p in problems)
    return SchemaMismatchError(lines, legacy=legacy)


def is_legacy_problem(problem: Problem, workspace: Workspace) -> bool:
    """問題が、前の版の形式（資料の `done`・題名の無い設定）から来ているかを返す。"""
    # スキーマ違反以外（参照切れなど）は前の版の形式のせいではない
    if problem.kind != "schema":
        return False
    # 設定: 題名（summary）が無い
    if problem.file == SETTINGS_FILE:
        raw_settings = workspace.raw.get(SETTINGS_FILE)
        return isinstance(raw_settings, dict) and "summary" not in raw_settings
    # 資料: done を持ち、status を持たない
    if problem.file == KINDS["doc"].file and problem.id is not None:
        docs = _extract_items(workspace.raw.get(problem.file))
        return any(
            item.get("id") == problem.id and "done" in item and "status" not in item
            for item in docs
        )
    return False


def save_change(workspace: Workspace, change: Change) -> None:
    """1 種類の項目の並びと本文を、検証してから両方とも書き換えるか、どちらも書き換えない。"""
    spec = KINDS[change.kind]
    # 書き戻すと中身を失う形のファイルには書かない（変更を当てる前の、そのファイルの問題を返す）
    if _loses_content_on_rewrite(workspace, change.kind):
        current = [p for p in validate_workspace(workspace) if p.file == spec.file]
        raise build_mismatch_error(current, workspace)
    # 変更を当てた後のワークスペース全体を検証する
    changed_raw = {**workspace.raw, spec.file: {"items": change.items}}
    changed = replace(workspace, raw=changed_raw)
    problems = validate_workspace(changed)
    if problems:
        raise build_mismatch_error(problems, changed)

    yaml_path = workspace.root / spec.file
    body_path = workspace.root / BODY_DIR / change.body.name if change.body else None
    # 本文があるときは置き換える前の中身を控える（無ければ None）
    previous_body = body_path.read_bytes() if body_path and body_path.is_file() else None

    # 一時ファイルを先に全て書く
    temps: list[Path] = []
    body_temp: Path | None = None
    try:
        yaml_temp = write_temp(yaml_path, dump_yaml({"items": change.items}))
        temps.append(yaml_temp)
        if change.body and body_path:
            body_path.parent.mkdir(exist_ok=True)
            body_temp = write_temp(body_path, change.body.text)
            temps.append(body_temp)
    except OSError as error:
        _remove_files(temps)
        raise write_failed(yaml_path, error) from error

    # 本文 → YAML の順に置き換える
    try:
        if body_temp and body_path:
            os.replace(body_temp, body_path)
    except OSError as error:
        _remove_files(temps)
        raise write_failed(body_path or yaml_path, error) from error
    try:
        os.replace(yaml_temp, yaml_path)
    except OSError as error:
        # YAML を置き換えられなかった: 置き換えた本文を元に戻す
        if body_path and body_temp:
            _restore_body(body_path, previous_body)
        _remove_files(temps)
        raise write_failed(yaml_path, error) from error


def create_workspace(root: Path, settings: dict[str, Any]) -> list[str]:
    """設定を検証してから、設定・空の 7 種類の YAML・`docs/`・`handoff/` を作る。"""
    root = root.resolve()
    if (root / SETTINGS_FILE).exists():
        raise WorkspaceExistsError(f"既にワークスペースがあります: {root}")

    # 設定と空の 7 種類で検証する（問題があればフォルダも作らない）
    raw: dict[str, Any] = {SETTINGS_FILE: settings}
    raw.update({spec.file: {"items": []} for spec in KINDS.values()})
    candidate = Workspace(
        root=root,
        raw=raw,
        settings=settings,
        items={kind: [] for kind in KINDS},
        load_problems=[],
    )
    problems = validate_workspace(candidate)
    if problems:
        raise build_mismatch_error(problems)

    # この関数が作ったファイルとフォルダ（途中で失敗したときに消す）
    created: list[Path] = []
    files: list[str] = []
    try:
        top_missing = _first_missing_ancestor(root)
        root.mkdir(parents=True, exist_ok=True)
        if top_missing is not None:
            created.append(top_missing)
        for dir_name in (BODY_DIR, HANDOFF_DIR):
            _make_dir(root / dir_name, created)
            files.append(f"{dir_name}/")
        for spec in KINDS.values():
            (root / spec.file).write_text(dump_yaml({"items": []}), encoding="utf-8")
            created.append(root / spec.file)
            files.append(spec.file)
        # mindmap.yaml は最後に書く（途中で止まってもワークスペースとして扱われない）
        (root / SETTINGS_FILE).write_text(dump_yaml(settings), encoding="utf-8")
        files.append(SETTINGS_FILE)
    except OSError as error:
        _remove_created(created)
        raise write_failed(root, error) from error
    return files


def read_body(workspace: Workspace, name: str) -> str | None:
    """`docs/` の本文を読む。ファイルが無いか、名前が `docs/` の外を指すときは None を返す。"""
    body_dir = (workspace.root / BODY_DIR).resolve()
    path = (body_dir / name).resolve()
    # docs/ の外を指す名前は読まない
    if not path.is_relative_to(body_dir):
        return None
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def as_ids(value: Any) -> list[str]:
    """参照のキーの値（`parent` は文字列、ほかは配列）を ID の並びにする。"""
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [element for element in value if isinstance(element, str)]
    return []


def dump_yaml(data: Any) -> str:
    """日本語をそのままにし、キーの並びを保って YAML の文字列にする。"""
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)


def _read_yaml(path: Path) -> Any:
    """1 ファイルを `yaml.safe_load` で読む（空のファイルは None）。"""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _extract_items(value: Any) -> list[dict[str, Any]]:
    """一番上が辞書で `items` が配列のときだけ、その要素のうち辞書のものを取り出す。"""
    if not isinstance(value, dict) or not isinstance(value.get("items"), list):
        return []
    return [item for item in value["items"] if isinstance(item, dict)]


def _item_id_at(value: Any, path: list[str | int]) -> str | None:
    """キーのパスが `items[n]` の下を指すとき、その項目の ID を返す。"""
    if len(path) <= 1 or path[0] != "items" or not isinstance(path[1], int):
        return None
    items = value.get("items") if isinstance(value, dict) else None
    if not isinstance(items, list) or path[1] >= len(items):
        return None
    item = items[path[1]]
    item_id = item.get("id") if isinstance(item, dict) else None
    return item_id if isinstance(item_id, str) else None


def _path_order(path: list[str | int]) -> tuple[tuple[int, Any], ...]:
    """キーのパスを、添字は数の順・キーは名前の順で比べられる形にする。"""
    return tuple((0, part) if isinstance(part, int) else (1, part) for part in path)


def _format_path(path: Iterable[str | int]) -> str:
    """`absolute_path` を `items[0].status` の形の文字列にする。"""
    text = ""
    for part in path:
        # 添字は直前に `[n]` をつなぐ
        if isinstance(part, int):
            text += f"[{part}]"
        # キーは `.` でつなぐ（先頭は付けない）
        else:
            text += f".{part}" if text else part
    return text or WHOLE_PATH


def write_temp(target: Path, text: str) -> Path:
    """置き換え先と同じフォルダに一時ファイルを書き、そのパスを返す（置き換えは呼ぶ側が行う）。"""
    return _write_temp(target, text)


def _write_temp(target: Path, text: str) -> Path:
    """置き換え先と同じフォルダに一時ファイルを書き、置き換え先の権限に揃えてそのパスを返す。"""
    fd, name = tempfile.mkstemp(dir=target.parent, suffix=TEMP_SUFFIX)
    temp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        # mkstemp は 0600 で作るので、置き換えた後に権限が変わらないよう揃える
        if target.exists():
            # 置き換え先がある: その権限を写す
            shutil.copymode(target, temp)
        else:
            # 置き換え先が無い: 通常のファイルと同じ権限（0o666 から umask を引いたもの）にする
            temp.chmod(DEFAULT_FILE_MODE & ~_current_umask())
    except OSError:
        # 書けなかった一時ファイルは残さない
        _remove_files([temp])
        raise
    return temp


def _loses_content_on_rewrite(workspace: Workspace, kind: Kind) -> bool:
    """その種類のファイルが、項目の並びで書き戻すと中身を失う形か。

    読めない・一番上が辞書でない・`items` の横にキーがある・辞書でない要素がある、など
    `items` に取り出せない中身があるときに真になる。項目の中の値だけが合わない形は、変更で直せるので偽。
    """
    file_name = KINDS[kind].file
    # YAML として読めないファイル
    if any(problem.file == file_name for problem in workspace.load_problems):
        return True
    # 読んだ値が、取り出した項目の並びだけの形と違う
    return workspace.raw.get(file_name) != {"items": workspace.items[kind]}


def _current_umask() -> int:
    """今の umask を返す（読むには一度設定するしかないので、設定し直して戻す）。"""
    mask = os.umask(0)
    os.umask(mask)
    return mask


def _remove_files(paths: list[Path]) -> None:
    """後始末として一時ファイルを消す（元の失敗を優先するので消せなくても続ける）。"""
    for path in paths:
        with contextlib.suppress(OSError):
            path.unlink(missing_ok=True)


def _restore_body(body_path: Path, previous_body: bytes | None) -> None:
    """置き換えた本文を、置き換える前の中身に戻す（前に本文が無ければ消す）。"""
    # 前に本文が無かった: 新しく書いた本文を消す
    if previous_body is None:
        body_path.unlink(missing_ok=True)
        return
    body_path.write_bytes(previous_body)


def write_failed(path: Path, error: OSError) -> WriteFailedError:
    """置き換え先のパスと OSError の理由を持つ例外を作る。"""
    return WriteFailedError(f"書き込めませんでした: {path}（{error.strerror or error}）")


def _first_missing_ancestor(path: Path) -> Path | None:
    """まだ無いパスのうち、一番上のものを返す（全て在るときは None）。"""
    missing: Path | None = None
    current = path
    while not current.exists():
        missing = current
        current = current.parent
    return missing


def _make_dir(path: Path, created: list[Path]) -> None:
    """フォルダが無ければ作り、作ったものを記録する。"""
    if not path.exists():
        path.mkdir()
        created.append(path)


def _remove_created(created: list[Path]) -> None:
    """作ったファイルとフォルダを、作った順の逆に消す（元の失敗を優先するので消せなくても続ける）。"""
    for path in reversed(created):
        with contextlib.suppress(OSError):
            # フォルダは中身ごと、ファイルはそのものを消す
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink(missing_ok=True)
