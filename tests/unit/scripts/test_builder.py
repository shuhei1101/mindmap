"""builder.py（プレビューのデータの収集・埋め込み・書き出し）の単体テスト。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import builder
import store
from errors import SchemaMismatchError, WriteFailedError
from fixture_types import FailingReplace, MakeItem, MakeWorkspace, SnapshotTree

# 埋め込み先の要素の開きタグ（DATA_ELEMENT から閉じタグを除いたもの）
DATA_ELEMENT_OPEN = builder.DATA_ELEMENT.removesuffix("</script>")

# 書き出した日時
BUILT_AT = "2026-10-02T08:00:00+00:00"


def _read_embedded(html: str) -> dict[str, Any]:
    """HTML の mindmap-data の要素の中身を JSON として読む。"""
    inner = html.split(DATA_ELEMENT_OPEN, 1)[1].split("</script>", 1)[0]
    return json.loads(inner)


def _write_preview_dir(preview_dir: Path, template: str) -> None:
    """雛形のフォルダに template.html と、STYLE_FILES・SCRIPT_FILES の名前のファイルを書く。"""
    preview_dir.mkdir(parents=True, exist_ok=True)
    (preview_dir / "template.html").write_text(template, encoding="utf-8")
    # 中身はファイル名のコメント（並びの順に差し込まれたかを見分けるため）
    for name in (*builder.STYLE_FILES, *builder.SCRIPT_FILES):
        path = preview_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"/* {name} */", encoding="utf-8")


@pytest.fixture
def preview_dir(tmp_path: Path) -> Path:
    """差し込み口と埋め込み先を持つ template.html と、空に近い CSS・JavaScript を置いた雛形のフォルダを返す。"""
    folder = tmp_path / "preview"
    _write_preview_dir(folder, f"{builder.STYLE_SLOT}{builder.DATA_ELEMENT}{builder.SCRIPT_SLOT}")
    return folder


def test_build_preview(
    make_workspace: MakeWorkspace, make_item: MakeItem, preview_dir: Path
) -> None:
    """データを埋め込んだ preview.html を書く（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"),
        make_item("A-1"),
        bodies={"A-1.md": "本文 </script>\n"},
    )
    workspace = store.load_workspace(root)
    # 実行
    path = builder.build_preview(workspace, built_at=BUILT_AT, preview_dir=preview_dir)
    # 検証
    assert path == root / "preview.html"
    data = _read_embedded(path.read_text(encoding="utf-8"))
    assert data["decisions"] == [make_item("D-1")]
    assert data["bodies"] == {"A-1.md": "本文 </script>\n"}
    assert data["built_at"] == BUILT_AT


def test_build_preview_when_schema_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
    preview_dir: Path,
) -> None:
    """問題があれば前の preview.html を残す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", status="完了"))
    (root / "preview.html").write_text("前の preview\n", encoding="utf-8")
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    # 実行・検証
    with pytest.raises(SchemaMismatchError):
        builder.build_preview(workspace, built_at=BUILT_AT, preview_dir=preview_dir)
    assert snapshot_tree(root) == before


def test_build_preview_when_replace_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
    failing_replace: FailingReplace,
    preview_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """置き換えに失敗したら前の preview.html を残す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    (root / "preview.html").write_text("前の preview\n", encoding="utf-8")
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    # builder モジュールの参照を、preview.html への置き換えが失敗するものに差し替える
    monkeypatch.setattr(builder.os, "replace", failing_replace("preview.html"))
    # 実行・検証
    with pytest.raises(WriteFailedError):
        builder.build_preview(workspace, built_at=BUILT_AT, preview_dir=preview_dir)
    assert snapshot_tree(root) == before
    assert list(root.rglob("*.tmp")) == []


def test_collect_preview_data(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """種類ごとのキーと、指された本文だけを集める（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("A-1"),
        make_item("R-1", body="R-1.md"),
        bodies={"A-1.md": "資料の本文\n", "X-1.md": "どこからも指されない本文\n"},
    )
    workspace = store.load_workspace(root)
    # 実行
    data = builder.collect_preview_data(workspace, built_at=BUILT_AT)
    # 検証
    assert set(data) == {
        "settings",
        "decisions",
        "tasks",
        "research",
        "docs",
        "terms",
        "notes",
        "logs",
        "bodies",
        "derived",
        "built_at",
    }
    assert data["bodies"] == {"A-1.md": "資料の本文\n"}


def test_escape_for_script() -> None:
    """置き換えた文字列は </script> を含まず、JSON として読むと元に戻る（正常系）。"""
    # 準備
    original = {"a": "</script>&<b>"}
    json_text = json.dumps(original, ensure_ascii=False)
    # 実行
    escaped = builder.escape_for_script(json_text)
    # 検証
    assert "<" not in escaped
    assert ">" not in escaped
    assert "&" not in escaped
    assert json.loads(escaped) == original


def test_embed_data() -> None:
    """要素の中身に JSON を入れる（正常系）。"""
    # 準備
    template = "<p></p>" + builder.DATA_ELEMENT
    data = {"a": "</script>"}
    # 実行
    html = builder.embed_data(template, data)
    # 検証
    assert html.count("</script>") == 1
    assert _read_embedded(html) == data


@pytest.mark.parametrize(
    ("template", "count_text"),
    [
        pytest.param("<p></p>", "0 個", id="none"),
        pytest.param(builder.DATA_ELEMENT * 2, "2 個", id="two"),
    ],
)
def test_embed_data_when_element_count_wrong(template: str, count_text: str) -> None:
    """埋め込み先が 1 つでない雛形は受け付けない（異常系）。"""
    # 実行・検証
    with pytest.raises(ValueError, match=count_text):
        builder.embed_data(template, {"a": 1})


def test_assemble_template(preview_dir: Path) -> None:
    """CSS と JavaScript を並びの順に差し込む（正常系）。"""
    # 実行
    html = builder.assemble_template(preview_dir=preview_dir)
    # 検証
    style = html.split('<style id="mindmap-style">', 1)[1].split("</style>", 1)[0]
    script = html.split('<script id="mindmap-app">', 1)[1].split("</script>", 1)[0]
    assert style == "\n".join(f"/* {name} */" for name in builder.STYLE_FILES)
    assert script == "\n".join(f"/* {name} */" for name in builder.SCRIPT_FILES)
    # 埋め込み先は空のまま
    assert builder.DATA_ELEMENT in html


@pytest.mark.parametrize(
    ("kind", "closing_tag"),
    [
        pytest.param("style", "</STYLE>", id="style"),
        pytest.param("script", "</script>", id="script"),
    ],
)
def test_assemble_template_when_closing_tag(preview_dir: Path, kind: str, closing_tag: str) -> None:
    """閉じタグを含むファイルは差し込まない（異常系）。"""
    # 準備
    file_name = builder.STYLE_FILES[0] if kind == "style" else builder.SCRIPT_FILES[0]
    (preview_dir / file_name).write_text(f"x {closing_tag} y", encoding="utf-8")
    # 実行・検証
    with pytest.raises(ValueError, match=file_name):
        builder.assemble_template(preview_dir=preview_dir)


@pytest.mark.parametrize(
    ("slot_kind", "count_text"),
    [
        pytest.param("style_slot_none", "0 個", id="style_slot_none"),
        pytest.param("script_slot_two", "2 個", id="script_slot_two"),
    ],
)
def test_assemble_template_when_slot_count_wrong(
    tmp_path: Path, slot_kind: str, count_text: str
) -> None:
    """差し込み口が 1 つでない雛形は受け付けない（異常系）。"""
    # 準備
    if slot_kind == "style_slot_none":
        template = f"{builder.DATA_ELEMENT}{builder.SCRIPT_SLOT}"
    else:
        template = f"{builder.STYLE_SLOT}{builder.DATA_ELEMENT}{builder.SCRIPT_SLOT * 2}"
    folder = tmp_path / "preview"
    _write_preview_dir(folder, template)
    # 実行・検証
    with pytest.raises(ValueError, match=count_text):
        builder.assemble_template(preview_dir=folder)


def test_derive_preview_values(
    make_workspace: MakeWorkspace, make_item: MakeItem, valid_settings: dict[str, Any]
) -> None:
    """コマンドと同じ答えをまとめる（正常系）。"""
    # 準備
    settings = {
        **valid_settings,
        "phases": ["目的", "要件"],
        "categories": [
            {"name": "A", "target": "mindmap", "summary": "カテゴリー A"},
            {"name": "B", "target": "mindmap", "summary": "カテゴリー B"},
        ],
        "goal": {"phase": "要件", "summary": "要件が決まる", "deliverables": []},
    }
    root = make_workspace(
        make_item("D-1", category="A", phase="目的", status="決定済み"),
        make_item("D-2", category="A", phase="要件", status="未決定", depends_on=["D-1"]),
        make_item("D-3", category="B", phase="要件", status="対象外"),
        settings=settings,
    )
    workspace = store.load_workspace(root)
    # 実行
    derived = builder.derive_preview_values(workspace)
    # 検証
    assert [candidate["id"] for candidate in derived["next"]] == ["D-2"]
    assert derived["goal"]["phase_progress"] == [
        {"phase": "目的", "settled": 1, "total": 1},
        {"phase": "要件", "settled": 1, "total": 2},
    ]
    assert derived["progress"] == [
        {
            "category": "A",
            "cells": [
                {"phase": "目的", "settled": 1, "total": 1},
                {"phase": "要件", "settled": 0, "total": 1},
            ],
            "settled": 1,
            "total": 2,
        },
        {
            "category": "B",
            "cells": [
                {"phase": "目的", "settled": 0, "total": 0},
                {"phase": "要件", "settled": 1, "total": 1},
            ],
            "settled": 1,
            "total": 1,
        },
    ]
