"""scripts の単体テストの共通 fixture。"""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

from fixture_types import (
    FailingReplace,
    FailingWriteText,
    MakeItem,
    MakeWorkspace,
    SnapshotTree,
)

# このファイルから見たリポジトリの直下（tests/unit/scripts の 3 つ上）
REPO_ROOT_PARENT_DEPTH = 3
SCRIPTS_DIR = (
    Path(__file__).resolve().parents[REPO_ROOT_PARENT_DEPTH] / "skills" / "mindmap" / "scripts"
)

# スクリプトはパッケージとして入れず、同じフォルダの名前（import store など）で読む
sys.path.insert(0, str(SCRIPTS_DIR))

# 項目に入れる既定の日時（UTC のタイムゾーン付き ISO 8601）
DEFAULT_TIMESTAMP = "2026-10-01T00:00:00+00:00"

# ID の頭の文字 → 書き込む YAML のファイル名（並びは D・T・R・A・G・N・L）
KIND_FILES = {
    "D": "decisions.yaml",
    "T": "tasks.yaml",
    "R": "research.yaml",
    "A": "docs.yaml",
    "G": "terms.yaml",
    "N": "notes.yaml",
    "L": "logs.yaml",
}

# ID の頭の文字 → スキーマが必須にしているキーの既定値
KIND_DEFAULTS: dict[str, dict[str, Any]] = {
    "D": {"status": "未決定"},
    "T": {"kind": "作業", "status": "未着手"},
    "R": {"question": "何を調べたか"},
    "A": {"kind": "図", "deliverable": False, "done": False},
    "G": {"meaning": "用語の意味"},
    "N": {"content": "メモの中身"},
    "L": {"date": "2026-10-01"},
}


@pytest.fixture
def scripts_dir() -> Path:
    """スクリプトのフォルダ（skills/mindmap/scripts）を返す。"""
    return SCRIPTS_DIR


@pytest.fixture
def valid_settings() -> dict[str, Any]:
    """設定のスキーマに合う設定（mindmap.yaml の中身）を返す。"""
    return {
        "field": "システム開発",
        "target_label": "システム",
        "phases": ["目的", "要件", "構成"],
        "targets": [{"name": "mindmap", "summary": "話し合いを記録するスキル"}],
        "categories": [{"name": "データ構造", "target": "mindmap", "summary": "YAML の種類とキー"}],
        "goal": {
            "phase": "構成",
            "summary": "作り始められる",
            "deliverables": [{"title": "YAML のスキーマ"}],
        },
        "links": [],
    }


@pytest.fixture
def make_item() -> MakeItem:
    """ID の頭の文字に合う必須のキーを持つ項目を作る関数を返す。"""

    def _make(item_id: str, **overrides: Any) -> dict[str, Any]:
        """ID・題・種類ごとの必須のキーに、渡したキーを重ねて日時を足した項目を返す。"""
        item: dict[str, Any] = {"id": item_id, "title": f"{item_id}の題"}
        item.update(KIND_DEFAULTS[item_id[0]])
        # 資料は本文が必須なので、ID に揃えたファイル名を既定にする
        if item_id[0] == "A":
            item["body"] = f"{item_id}.md"
        item.update(overrides)
        item.setdefault("created", DEFAULT_TIMESTAMP)
        item.setdefault("updated", DEFAULT_TIMESTAMP)
        return item

    return _make


@pytest.fixture
def make_workspace(tmp_path: Path, valid_settings: dict[str, Any]) -> MakeWorkspace:
    """一時フォルダにワークスペースを書く関数を返す。項目は ID の頭の文字で YAML に振り分ける。"""

    def _make(
        *items: dict[str, Any],
        settings: dict[str, Any] | None = None,
        raw_files: dict[str, str] | None = None,
        bodies: dict[str, str] | None = None,
        name: str = "workspace",
    ) -> Path:
        """項目のある種類の YAML だけを置いたワークスペースを作り、そのフォルダを返す。"""
        root = tmp_path / name
        (root / "docs").mkdir(parents=True)
        (root / "handoff").mkdir()
        write_yaml(root / "mindmap.yaml", valid_settings if settings is None else settings)
        # 項目のある種類だけ、渡した並びのまま 1 つの YAML にまとめる
        for prefix, file_name in KIND_FILES.items():
            kind_items = [item for item in items if item["id"][0] == prefix]
            if kind_items:
                write_yaml(root / file_name, {"items": kind_items})
        # 壊れた YAML や一番上が配列のファイルなど、そのまま書きたいファイルは上書きする
        for file_name, text in (raw_files or {}).items():
            (root / file_name).write_text(text, encoding="utf-8")
        for body_name, text in (bodies or {}).items():
            (root / "docs" / body_name).write_text(text, encoding="utf-8")
        return root

    return _make


@pytest.fixture
def snapshot_tree() -> SnapshotTree:
    """フォルダの下の全てのファイルを、相対パス → 中身にして返す関数を返す。"""

    def _snapshot(root: Path) -> dict[str, bytes]:
        """書き込みの前後で何も変わっていないことを比べるための写しを作る。"""
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }

    return _snapshot


@pytest.fixture
def failing_replace() -> FailingReplace:
    """指定したファイル名への置き換えだけを OSError にする os.replace の代わりを作る関数を返す。"""
    # monkeypatch で差し替える前の本物を控える
    real_replace = os.replace

    def _build(target_name: str) -> Callable[[Any, Any], None]:
        """置き換え先が target_name のときだけ失敗する関数を返す。"""

        def _replace(src: Any, dst: Any) -> None:
            """置き換え先の名前を見て、失敗させるか本物に任せるかを決める。"""
            # 失敗させる対象のファイルへの置き換え
            if Path(dst).name == target_name:
                raise OSError("置き換えできません")
            # それ以外は本物で置き換える
            real_replace(src, dst)

        return _replace

    return _build


@pytest.fixture
def failing_write_text(monkeypatch: pytest.MonkeyPatch) -> FailingWriteText:
    """指定したファイル名への Path.write_text だけを OSError にする関数を返す。"""
    # monkeypatch で差し替える前の本物を控える
    real_write_text = Path.write_text

    def _install(target_name: str) -> None:
        """Path.write_text を、target_name のときだけ失敗するものに差し替える。"""

        def _write_text(self: Path, data: str, *args: Any, **kwargs: Any) -> int:
            """書く先の名前を見て、失敗させるか本物に任せるかを決める。"""
            # 失敗させる対象のファイルへの書き込み
            if self.name == target_name:
                raise OSError("書き込めません")
            # それ以外は本物で書く
            return real_write_text(self, data, *args, **kwargs)

        monkeypatch.setattr(Path, "write_text", _write_text)

    return _install


def write_yaml(path: Path, data: Any) -> None:
    """日本語をそのままにして、キーの並びを保って YAML を書く。"""
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
