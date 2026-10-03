"""build（プレビューの書き出し）の結合テスト。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from .fixture_types import LockDirs, MakeItem, MakeWorkspace, RunMindmap, SnapshotTree

# このファイルから見たリポジトリの直下（tests/integration/scripts の 3 つ上）
REPO_ROOT_PARENT_DEPTH = 3
TEMPLATE_PATH = (
    Path(__file__).resolve().parents[REPO_ROOT_PARENT_DEPTH]
    / "plugins"
    / "mindstella"
    / "skills"
    / "mindmap"
    / "preview"
    / "template.html"
)

# 埋め込み先の要素の開きタグ
DATA_ELEMENT_OPEN = '<script type="application/json" id="mindmap-data">'

# 資料の本文（要素を閉じる文字列を含む）
BODY_WITH_SCRIPT_TAG = "本文に </script> を含む\n"


def _read_embedded(html: str) -> dict[str, Any]:
    """HTML の mindmap-data の要素の中身を JSON として読む。"""
    inner = html.split(DATA_ELEMENT_OPEN, 1)[1].split("</script>", 1)[0]
    return json.loads(inner)


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    run_mindmap: RunMindmap,
    valid_settings: dict[str, Any],
) -> None:
    """全ての種類と本文を埋め込んだ preview.html を書き出す（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"),
        make_item("T-1"),
        make_item("R-1"),
        make_item("A-1"),
        make_item("G-1"),
        make_item("N-1"),
        make_item("L-1"),
        bodies={"A-1.md": BODY_WITH_SCRIPT_TAG},
    )
    # 実行
    result = run_mindmap("build", "--workspace", str(root))
    # 検証
    assert result.returncode == 0
    assert json.loads(result.stdout) == {"path": str(root / "preview.html")}
    html = (root / "preview.html").read_text(encoding="utf-8")
    data = _read_embedded(html)
    assert data["settings"] == valid_settings
    assert data["decisions"] == [make_item("D-1")]
    assert data["tasks"] == [make_item("T-1")]
    assert data["research"] == [make_item("R-1")]
    assert data["docs"] == [make_item("A-1")]
    assert data["terms"] == [make_item("G-1")]
    assert data["notes"] == [make_item("N-1")]
    assert data["logs"] == [make_item("L-1")]
    assert data["bodies"] == {"A-1.md": BODY_WITH_SCRIPT_TAG}
    # 画面に出す値は、next・goal のコマンドと同じ中身
    assert data["settings"]["summary"] == valid_settings["summary"]
    candidates = json.loads(run_mindmap("next", "--workspace", str(root)).stdout)["candidates"]
    assert data["derived"]["next"] == candidates
    goal = json.loads(run_mindmap("goal", "--workspace", str(root)).stdout)
    for key, value in goal.items():
        assert data["derived"]["goal"][key] == value
    # 本文の </script> で要素が閉じていない（雛形の閉じタグの数と同じ）
    assert html.count("</script>") == TEMPLATE_PATH.read_text(encoding="utf-8").count("</script>")
    # 読み込む src・href にローカルのパスが無い
    references = re.findall(r'(?:src|href)="([^"]*)"', html)
    assert [ref for ref in references if not ref.startswith("https://")] == []


def test_error_when_workspace_not_found(tmp_path: Path, run_mindmap: RunMindmap) -> None:
    """mindmap.yaml が無いフォルダを指すと何も書かずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    # 実行
    result = run_mindmap("build", "--workspace", str(root))
    # 検証
    assert result.returncode == 1
    assert str(root) in result.stderr
    assert not (root / "preview.html").exists()


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    run_mindmap: RunMindmap,
    snapshot_tree: SnapshotTree,
) -> None:
    """手で崩した YAML があると、前に書き出した preview.html を残して終わる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    run_mindmap("build", "--workspace", str(root))
    (root / "decisions.yaml").write_text(
        yaml.safe_dump({"items": [make_item("D-1", status="完了")]}, allow_unicode=True),
        encoding="utf-8",
    )
    before = snapshot_tree(root)
    # 実行
    result = run_mindmap("build", "--workspace", str(root))
    # 検証
    assert result.returncode == 1
    assert "decisions.yaml: items[0].status:" in result.stderr
    assert snapshot_tree(root) == before


def test_error_when_write_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    run_mindmap: RunMindmap,
    snapshot_tree: SnapshotTree,
    lock_dirs: LockDirs,
) -> None:
    """書き込めないワークスペースでは前の preview.html を残して終わる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    run_mindmap("build", "--workspace", str(root))
    before = snapshot_tree(root)
    lock_dirs(root)
    # 実行
    result = run_mindmap("build", "--workspace", str(root))
    # 検証
    assert result.returncode == 1
    assert result.stderr.startswith("エラー: ")
    assert "Traceback" not in result.stderr
    assert snapshot_tree(root) == before
