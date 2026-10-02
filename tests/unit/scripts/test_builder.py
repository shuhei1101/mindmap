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


@pytest.fixture
def template_path(tmp_path: Path) -> Path:
    """埋め込み先の要素だけを持つ雛形のファイルを作ってそのパスを返す。"""
    path = tmp_path / "template.html"
    path.write_text(builder.DATA_ELEMENT, encoding="utf-8")
    return path


def test_build_preview(
    make_workspace: MakeWorkspace, make_item: MakeItem, template_path: Path
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
    path = builder.build_preview(workspace, built_at=BUILT_AT, template_path=template_path)
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
    template_path: Path,
) -> None:
    """問題があれば前の preview.html を残す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", status="完了"))
    (root / "preview.html").write_text("前の preview\n", encoding="utf-8")
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    # 実行・検証
    with pytest.raises(SchemaMismatchError):
        builder.build_preview(workspace, built_at=BUILT_AT, template_path=template_path)
    assert snapshot_tree(root) == before


def test_build_preview_when_replace_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
    failing_replace: FailingReplace,
    template_path: Path,
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
        builder.build_preview(workspace, built_at=BUILT_AT, template_path=template_path)
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
