"""単体・結合・E2E のテストが共有する、ワークスペースと mindmap.py の起動の fixture。

fixture は `tests/conftest.py` が読み込み、`tests/` の下の全てのテストが使える。
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
import yaml

# このファイルから見たリポジトリの直下（tests の 1 つ上）
REPO_ROOT_PARENT_DEPTH = 1
REPO_ROOT = Path(__file__).resolve().parents[REPO_ROOT_PARENT_DEPTH]

# 起動するスクリプトの入口
MINDMAP_SCRIPT = REPO_ROOT / "skills" / "mindmap" / "scripts" / "mindmap.py"

# 子プロセス 1 回を待つ上限秒数
COMMAND_TIMEOUT_SEC = 120

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
    "A": {"kind": "図", "deliverable": False, "status": "下書き"},
    "G": {"meaning": "用語の意味"},
    "N": {"content": "メモの中身"},
    "L": {"date": "2026-10-01"},
}

type RunMindmap = Callable[..., subprocess.CompletedProcess[str]]
type MakeItem = Callable[..., dict[str, Any]]
type MakeWorkspace = Callable[..., Path]
type MakeLegacyItem = Callable[[str, bool], dict[str, Any]]
type MakeLegacyWorkspace = Callable[..., Path]
type SnapshotTree = Callable[[Path], dict[str, bytes]]
type MakeVenv = Callable[..., Path]


@pytest.fixture
def run_mindmap() -> RunMindmap:
    """mindmap.py を子プロセスで起動し、結果を返す関数を返す。"""
    # 子プロセスの入出力を UTF-8 に揃える（既定の文字コードに左右されないため）
    env = {**os.environ, "PYTHONUTF8": "1"}

    def _run(
        *args: str, stdin: str | None = None, python: str = sys.executable
    ) -> subprocess.CompletedProcess[str]:
        """引数と標準入力を渡して実行し、終了コードが 0 以外でも例外にせず返す。"""
        return subprocess.run(
            [python, str(MINDMAP_SCRIPT), *args],
            input=stdin,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=COMMAND_TIMEOUT_SEC,
            check=False,
        )

    return _run


@pytest.fixture
def valid_settings() -> dict[str, Any]:
    """設定のスキーマに合う設定（mindmap.yaml の中身）を返す。"""
    return {
        "summary": "要件出しのスキル mindmap を設計する",
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
        (root / "release").mkdir()
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
def make_legacy_item(make_item: MakeItem) -> MakeLegacyItem:
    """前の版の形式（状態の代わりに done を持つ）の資料を作る関数を返す。"""

    def _make(item_id: str, done: bool) -> dict[str, Any]:
        """status の位置に done を置いた資料を返す（キーの並びは今の形式のまま）。"""
        item = make_item(item_id)
        return {
            ("done" if key == "status" else key): (done if key == "status" else value)
            for key, value in item.items()
        }

    return _make


@pytest.fixture
def make_legacy_workspace(
    tmp_path: Path, make_workspace: MakeWorkspace, make_legacy_item: MakeLegacyItem
) -> MakeLegacyWorkspace:
    """前の版の形式（資料の done・題名の無い設定）で書いたワークスペースを作る関数を返す。"""

    def _make(
        *items: dict[str, Any],
        legacy_docs: dict[str, bool] | None = None,
        without_summary: bool = False,
    ) -> Path:
        """items は今の形式の項目、legacy_docs は資料の ID → done。設定の題名は without_summary で外す。"""
        legacy_items = [
            make_legacy_item(doc_id, done) for doc_id, done in (legacy_docs or {}).items()
        ]
        root = make_workspace(
            *items, bodies={f"{item['id']}.md": "資料の本文\n" for item in legacy_items}
        )
        # 前の形式の資料を docs.yaml に直接書く（今の形式の資料の後ろに並べる）
        if legacy_items:
            docs_path = root / "docs.yaml"
            current = (
                yaml.safe_load(docs_path.read_text(encoding="utf-8"))["items"]
                if docs_path.exists()
                else []
            )
            write_yaml(docs_path, {"items": [*current, *legacy_items]})
        # 題名を持たない設定にする
        if without_summary:
            settings = yaml.safe_load((root / "mindmap.yaml").read_text(encoding="utf-8"))
            del settings["summary"]
            write_yaml(root / "mindmap.yaml", settings)
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
def make_venv(tmp_path: Path) -> MakeVenv:
    """一時フォルダに仮想環境を作る関数を返す。ライブラリはテストを動かす Python のものを見せる。"""

    def _make(name: str, *, python: str = sys.executable, with_libraries: bool = True) -> Path:
        """pip の無い仮想環境を作る。with_libraries なら PyYAML・jsonschema を見せる（通信しない）。"""
        venv_dir = tmp_path / name
        subprocess.run([python, "-m", "venv", "--without-pip", str(venv_dir)], check=True)
        # 仮想環境の Python の場所
        python_path = venv_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        if with_libraries:
            site_packages = subprocess.run(
                [
                    str(python_path),
                    "-c",
                    "import sysconfig; print(sysconfig.get_paths()['purelib'])",
                ],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            # テストを動かす Python のライブラリの置き場所を、`.pth` で仮想環境に足す
            library_dirs = [
                entry for entry in sys.path if entry.endswith(("site-packages", "dist-packages"))
            ]
            (Path(site_packages) / "mindmap_test.pth").write_text(
                "\n".join(library_dirs) + "\n", encoding="utf-8"
            )
        return venv_dir

    return _make


def write_yaml(path: Path, data: Any) -> None:
    """日本語をそのままにして、キーの並びを保って YAML を書く。"""
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
