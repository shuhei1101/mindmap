"""プレビューの書き出し（スキルが記録を 1 枚の HTML に書き出す）の E2E テスト。"""

from __future__ import annotations

import json
import re
from typing import Any

import yaml
from workspace_fixtures import MakeItem, MakeWorkspace, RunMindmap

# 埋め込み先の要素の開きタグ
DATA_ELEMENT_OPEN = '<script type="application/json" id="mindmap-data">'

# 資料の本文の Markdown
DOC_BODY = "## 資料\n\n本文に </script> を含む。\n"


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
        bodies={"A-1.md": DOC_BODY},
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
    assert data["bodies"] == {"A-1.md": DOC_BODY}
    # 読み込むスクリプトとスタイルが、ローカルの他のファイルを指さない
    references = re.findall(r'(?:src|href)="([^"]*)"', html)
    assert [ref for ref in references if not ref.startswith("https://")] == []


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace, make_item: MakeItem, run_mindmap: RunMindmap
) -> None:
    """手で崩した YAML があると、前に書き出した preview.html を残して終わる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    run_mindmap("build", "--workspace", str(root))
    before = (root / "preview.html").read_bytes()
    (root / "decisions.yaml").write_text(
        yaml.safe_dump({"items": [make_item("D-1", status="完了")]}, allow_unicode=True),
        encoding="utf-8",
    )
    # 実行
    result = run_mindmap("build", "--workspace", str(root))
    # 検証
    assert result.returncode != 0
    assert "decisions.yaml" in result.stderr
    assert "status" in result.stderr
    assert (root / "preview.html").read_bytes() == before
