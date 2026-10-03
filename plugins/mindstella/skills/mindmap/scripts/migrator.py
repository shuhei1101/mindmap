"""ワークスペースの版とプラグインの版を比べ、版ごとの手順を並べる・写しを取って当てる・値を入れる・版を書き換える。"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

from backup import Backup, restore_backup, take_backup
from errors import (
    SchemaMismatchError,
    StepFailedError,
    StepsInvalidError,
    WorkspaceNewerError,
    WorkspaceNotFoundError,
)
from kinds import SETTINGS_FILE
from migration_ops import StepError, apply_step, list_needed_values
from store import (
    SCHEMA_DIR,
    build_mismatch_error,
    dump_yaml,
    load_workspace,
    validate_workspace,
    write_failed,
    write_temp,
)
from versions import (
    Version,
    compare_versions,
    parse_release_version,
    read_plugin_version,
    read_workspace_version,
    write_workspace_version,
)

# 版ごとの手順を置く場所（このファイルから見た `skills/mindmap/migrations/`）
MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations"

# 1 つの版の手順を持つファイルの名前
STEPS_FILE = "steps.yaml"

# `steps.yaml` の形のスキーマ
STEPS_SCHEMA = SCHEMA_DIR / "migration-steps.schema.json"

# 写しから戻せなかったときに、`StepFailedError` の `lines` へ足す 1 行
RESTORE_FAILED_LINE = "写しから戻せませんでした。写しは {ref} にあります"

# `--set` の `{ファイル}:{キーのパス}={値}` の区切り
FILE_SEPARATOR = ":"
VALUE_SEPARATOR = "="

# `--set` のキーのパスの区切り
KEY_PATH_SEPARATOR = "."


@dataclass(frozen=True, slots=True, kw_only=True)
class MigrationStep:
    """`steps.yaml` の 1 つの手順と、その版・番号。"""

    version: Version
    index: int
    op: Literal[
        "rename_file", "move_dir", "delete", "rename_key", "set_default", "map_values", "call"
    ]
    args: dict[str, Any]
    folder: Path


@dataclass(frozen=True, slots=True, kw_only=True)
class NeededValue:
    """`set_default` の `ask` で、値が無いキー。"""

    file: str
    key: str
    description: str


@dataclass(frozen=True, slots=True, kw_only=True)
class MigrationReport:
    """`migrate` の出力の中身。"""

    workspace_version: Version | None
    plugin_version: Version
    relation: Literal["older", "same", "newer"]
    steps: list[MigrationStep] = field(default_factory=list)
    needs_values: list[NeededValue] = field(default_factory=list)
    backup: Backup | None = None
    recorded: Version | None = None


def list_versions(*, migrations_dir: Path = MIGRATIONS_DIR) -> list[Version]:
    """手順の置き場所にある版のフォルダを、版の順に返す。版の形でないフォルダとファイルは含めない。"""
    found: list[Version] = []
    for path in migrations_dir.iterdir():
        # フォルダだけを見る
        if not path.is_dir():
            continue
        try:
            found.append(parse_release_version(path.name))
        except ValueError:
            # 版の形でない名前のフォルダは手順の置き場所ではない
            continue
    return sorted(found)


def load_steps(version: Version, *, migrations_dir: Path = MIGRATIONS_DIR) -> list[MigrationStep]:
    """1 つの版の `steps.yaml` を読み、スキーマと突き合わせて手順に並べる。"""
    folder = migrations_dir / str(version)
    try:
        data = yaml.safe_load((folder / STEPS_FILE).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise StepsInvalidError(
            f"{version} の {STEPS_FILE} を読めません", [f"{version}/{STEPS_FILE}: {error}"]
        ) from error
    problems = _validate_steps(data)
    if problems:
        raise StepsInvalidError(
            f"{version} の {STEPS_FILE} が手順の形に合いません",
            [f"{version}/{STEPS_FILE}: {problem}" for problem in problems],
        )
    return [
        MigrationStep(
            version=version,
            index=index,
            op=raw["op"],
            args={key: value for key, value in raw.items() if key != "op"},
            folder=folder,
        )
        for index, raw in enumerate(data["steps"], start=1)
    ]


def plan_migration(
    root: Path,
    *,
    from_version: Version | None = None,
    to_version: Version | None = None,
    migrations_dir: Path = MIGRATIONS_DIR,
) -> MigrationReport:
    """版を比べ、`from` より後で `to` 以下の版の手順と値が要るキーを返す。何も書かない。"""
    _require_workspace(root)
    workspace_version = read_workspace_version(root)
    plugin_version = read_plugin_version()
    relation = compare_versions(workspace_version, plugin_version)
    # 省いた版は、ワークスペースの版・プラグインの版で埋める
    lower = from_version if from_version is not None else workspace_version
    upper = to_version if to_version is not None else plugin_version
    steps: list[MigrationStep] = []
    for version in list_versions(migrations_dir=migrations_dir):
        # lower より後で upper 以下の版（lower が None なら全て）
        if (lower is None or version > lower) and version <= upper:
            steps.extend(load_steps(version, migrations_dir=migrations_dir))
    return MigrationReport(
        workspace_version=workspace_version,
        plugin_version=plugin_version,
        relation=relation,
        steps=steps,
        needs_values=_collect_needed_values(root, steps),
    )


def apply_migration(
    root: Path,
    *,
    from_version: Version | None = None,
    to_version: Version | None = None,
    migrations_dir: Path = MIGRATIONS_DIR,
) -> MigrationReport:
    """写しを取ってから手順を版の順に当てる。失敗したら写しから戻して送る。版のファイルは書かない。"""
    plan = plan_migration(
        root, from_version=from_version, to_version=to_version, migrations_dir=migrations_dir
    )
    # ワークスペースの版の方が新しい
    if plan.relation == "newer":
        raise WorkspaceNewerError(
            f"ワークスペースの版 {plan.workspace_version} はプラグインの版 "
            f"{plan.plugin_version} より新しいため移し替えられません。プラグインを更新してください"
        )
    # 当てる手順が無い: 写しを取らずに返す
    if not plan.steps:
        return plan
    target_version = to_version if to_version is not None else plan.plugin_version
    backup = take_backup(root, target_version)
    for step in plan.steps:
        try:
            apply_step(root, step)
        except StepError as error:
            raise _step_failed(root, step, backup, error) from error
    return MigrationReport(
        workspace_version=plan.workspace_version,
        plugin_version=plan.plugin_version,
        relation=plan.relation,
        steps=plan.steps,
        needs_values=_collect_needed_values(root, plan.steps),
        backup=backup,
    )


def parse_assignment(text: str) -> tuple[str, str, str]:
    """`--set` の `{ファイル}:{キーのパス}={値}` を、ファイル・キーのパス・値に分ける。"""
    file_name, found_file, rest = text.partition(FILE_SEPARATOR)
    key_path, found_value, value = rest.partition(VALUE_SEPARATOR)
    # 区切りが無いか、ファイル・キーのパスが空
    if not found_file or not found_value or not file_name or not key_path:
        raise ValueError(f"--set の形が違います: {text}（{{ファイル}}:{{キーのパス}}={{値}}）")
    return file_name, key_path, value


def set_values(root: Path, assignments: list[tuple[str, str, str]]) -> None:
    """値が要るキーに値を入れる。版のファイルは書かない。"""
    _require_workspace(root)
    # ファイルごとに、入れる値を渡した順にまとめる
    by_file: dict[str, list[tuple[str, str]]] = {}
    for file_name, key_path, value in assignments:
        by_file.setdefault(file_name, []).append((key_path, value))
    targets: dict[Path, str] = {}
    for file_name, pairs in by_file.items():
        path = _inside(root, file_name)
        data = _load_mapping(path, file_name)
        for key_path, value in pairs:
            _put(data, key_path, value, file_name)
        targets[path] = dump_yaml(data)
    _replace_all(targets)


def record_version(root: Path, *, to_version: Version | None = None) -> Version:
    """ワークスペースを点検し、スキーマに合えば版のファイルを書く。"""
    target = to_version if to_version is not None else read_plugin_version()
    current = read_workspace_version(root)
    # ワークスペースの版の方が新しい
    if current is not None and current > target:
        raise WorkspaceNewerError(
            f"ワークスペースの版 {current} は書く版 {target} より新しいため書き換えられません。"
            "プラグインを更新してください"
        )
    problems = validate_workspace(load_workspace(root))
    if problems:
        raise build_mismatch_error(problems)
    write_workspace_version(root, target)
    return target


def _validate_steps(data: Any) -> list[str]:
    """`steps.yaml` の中身を手順の形のスキーマと突き合わせ、合わない箇所の行を返す。"""
    schema = json.loads(STEPS_SCHEMA.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    lines: list[str] = []
    for error in validator.iter_errors(data):
        # oneOf で外れたときは、最も近い候補の理由を出す
        chosen = best_match(error.context) if error.context else error
        lines.append(f"{chosen.json_path}: {chosen.message}")
    return lines


def _collect_needed_values(root: Path, steps: list[MigrationStep]) -> list[NeededValue]:
    """各手順の値が要るキーを集める。同じファイル・キーは 1 つにする。"""
    needed: dict[tuple[str, str], NeededValue] = {}
    for step in steps:
        for value in list_needed_values(root, step):
            needed.setdefault((value.file, value.key), value)
    return list(needed.values())


def _step_failed(
    root: Path, step: MigrationStep, backup: Backup, error: StepError
) -> StepFailedError:
    """写しから戻し、失敗した版・番号・操作・理由を持つ例外を作る。戻せなければ写しの場所を添える。"""
    lines: list[str] = []
    try:
        restore_backup(root, backup)
    except OSError:
        # 戻せなかった: 利用者が戻せるよう、写しの場所を知らせる
        lines.append(RESTORE_FAILED_LINE.format(ref=backup.ref))
    return StepFailedError(f"{step.version} の手順 {step.index}（{step.op}）: {error}", lines)


def _require_workspace(root: Path) -> None:
    """`mindmap.yaml` が無ければ送る。"""
    if not (root / SETTINGS_FILE).exists():
        raise WorkspaceNotFoundError(f"ワークスペースがありません: {root}")


def _inside(root: Path, file_name: str) -> Path:
    """ワークスペースの中のファイルのパスを組む。外を指すなら送る。"""
    path = (root / file_name).resolve()
    # ワークスペースの外を指している
    if not path.is_relative_to(root.resolve()):
        raise SchemaMismatchError([f"{file_name}: (全体): ワークスペースの外は指せません"])
    return path


def _load_mapping(path: Path, file_name: str) -> dict[str, Any]:
    """YAML を読み、一番上が辞書であることを確かめる。"""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise SchemaMismatchError([f"{file_name}: (全体): 読めません"]) from error
    # 一番上が辞書でない
    if not isinstance(data, dict):
        raise SchemaMismatchError([f"{file_name}: (全体): 辞書ではありません"])
    return data


def _put(data: dict[str, Any], key_path: str, value: str, file_name: str) -> None:
    """キーのパスを辿って値を置く。途中の辞書が無ければ作る。"""
    *parents, last = key_path.split(KEY_PATH_SEPARATOR)
    current = data
    for part in parents:
        child = current.setdefault(part, {})
        # 途中が辞書でない
        if not isinstance(child, dict):
            raise SchemaMismatchError([f"{file_name}: {key_path}: {part} は辞書ではありません"])
        current = child
    current[last] = value


def _replace_all(targets: dict[Path, str]) -> None:
    """全てのファイルを一時ファイルに書いてから、置き換える。失敗したら残った一時ファイルを消す。"""
    temps: dict[Path, Path] = {}
    try:
        for path, text in targets.items():
            temps[path] = write_temp(path, text)
        for path, temp in temps.items():
            os.replace(temp, path)
    except OSError as error:
        # 置き換えられなかった一時ファイルは残さない
        for temp in temps.values():
            temp.unlink(missing_ok=True)
        raise write_failed(path, error) from error
