"""export（配る書き出し）の結合テスト。

正常系と、書き出す前に jsDelivr から取る異常系は、実際の jsDelivr へ HTTPS で届く環境で動かす。
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import yaml

from .fixture_types import MakeItem, MakeWorkspace, RunMindmap, SnapshotTree

# このファイルから見たリポジトリの直下（tests/integration/scripts の 3 つ上）
REPO_ROOT_PARENT_DEPTH = 3
TEMPLATE_PATH = (
    Path(__file__).resolve().parents[REPO_ROOT_PARENT_DEPTH]
    / "skills"
    / "mindmap"
    / "preview"
    / "template.html"
)

# 埋め込み先・ライセンスの表示の要素の開きタグ
DATA_ELEMENT_OPEN = '<script type="application/json" id="mindmap-data">'
LICENSES_ELEMENT_OPEN = '<script type="text/plain" id="mindmap-licenses">'

# 資料の本文（要素を閉じる文字列を含む）
BODY_WITH_SCRIPT_TAG = "本文に </script> を含む\n"

# jsDelivr に届かないようにする環境変数（届かない宛先のプロキシを通す）
UNREACHABLE_PROXY_ENV = {
    "HTTPS_PROXY": "http://127.0.0.1:9",
    "https_proxy": "http://127.0.0.1:9",
}

# 中に持つライブラリごとの、表示に出るライセンスの名前と著作権の表示（雛形の URL のパッケージ名 → 表示）
EXPECTED_LICENSES = {
    "marked": ("marked", "MIT", "Copyright (c) 2018+, MarkedJS"),
    "dompurify": ("DOMPurify", "Apache-2.0", "(c) Cure53 and other contributors"),
    "elkjs": ("elkjs", "EPL-2.0", "(c) Kiel University and others"),
    "mermaid": ("mermaid", "MIT", "Copyright (c) 2014 - 2022 Knut Sveidqvist"),
}

# elkjs のソースコードの入手先（リポジトリ）
ELKJS_REPOSITORY = "https://github.com/kieler/elkjs"


class _ExternalReferences(HTMLParser):
    """script・img の src と link の href を持つ要素を集める。"""

    def __init__(self) -> None:
        """集めた要素のタグ名と属性の並びを空で持つ。"""
        super().__init__()
        self.found: list[tuple[str, dict[str, str | None]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """外のファイルや URL を指す属性を持つ要素を控える。"""
        values = dict(attrs)
        if (tag in ("script", "img") and "src" in values) or (tag == "link" and "href" in values):
            self.found.append((tag, values))


def _read_element(html: str, open_tag: str) -> str:
    """HTML の指定した script 要素の中身を返す。"""
    return html.split(open_tag, 1)[1].split("</script>", 1)[0]


def _template_versions() -> dict[str, str]:
    """雛形の描画のライブラリの `<script src>` から、パッケージ名 → 版を読む。"""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    return dict(re.findall(r'src="https://cdn\.jsdelivr\.net/npm/([^@"]+)@([^/"]+)/', template))


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    run_mindmap: RunMindmap,
    snapshot_tree: SnapshotTree,
    tmp_path: Path,
    valid_settings: dict[str, Any],
) -> None:
    """記録・画面・描画のライブラリ・ライセンスの表示を中に持つ 1 枚の HTML を --out へ書き出す（正常系）。"""
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
    assert run_mindmap("build", "--workspace", str(root)).returncode == 0
    before = snapshot_tree(root)
    out = tmp_path / "配る.html"
    # 実行
    result = run_mindmap("export", "--workspace", str(root), "--out", str(out))
    # 検証
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"path": str(out)}
    html = out.read_text(encoding="utf-8")
    data = json.loads(_read_element(html, DATA_ELEMENT_OPEN))
    assert data["settings"] == valid_settings
    assert data["decisions"] == [make_item("D-1")]
    assert data["tasks"] == [make_item("T-1")]
    assert data["research"] == [make_item("R-1")]
    assert data["docs"] == [make_item("A-1")]
    assert data["terms"] == [make_item("G-1")]
    assert data["notes"] == [make_item("N-1")]
    assert data["logs"] == [make_item("L-1")]
    assert data["bodies"] == {"A-1.md": BODY_WITH_SCRIPT_TAG}
    # script・link・img が外のファイルや URL を指さない
    references = _ExternalReferences()
    references.feed(html)
    assert references.found == []
    # 本文の </script> で要素が閉じていない（雛形の閉じタグの数に、ライセンスの表示の要素の 1 つを足した数）
    template_closes = TEMPLATE_PATH.read_text(encoding="utf-8").count("</script>")
    assert html.count("</script>") == template_closes + 1
    # ライセンスの表示に、ライブラリごとの名前・版・著作権の表示・ライセンスの名前がある
    licenses = _read_element(html, LICENSES_ELEMENT_OPEN)
    versions = _template_versions()
    for package, (name, license_name, notice) in EXPECTED_LICENSES.items():
        assert f"{name} {versions[package]}" in licenses
        assert notice in licenses
        assert f"License: {license_name}" in licenses
    # elkjs は、ソースコードの入手先（リポジトリと版のタグの URL）を持つ
    assert f"{ELKJS_REPOSITORY}/tree/{versions['elkjs']}" in licenses
    # build の preview.html は書き換えない
    assert snapshot_tree(root) == before


def test_error_when_out_is_preview(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    run_mindmap: RunMindmap,
    snapshot_tree: SnapshotTree,
) -> None:
    """ワークスペースの preview.html を書き出す先にすると、何も書かずに終わる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    assert run_mindmap("build", "--workspace", str(root)).returncode == 0
    before = snapshot_tree(root)
    # 実行
    result = run_mindmap("export", "--workspace", str(root), "--out", str(root / "preview.html"))
    # 検証
    assert result.returncode == 2
    assert "--out" in result.stderr
    assert snapshot_tree(root) == before


def test_error_when_workspace_not_found(tmp_path: Path, run_mindmap: RunMindmap) -> None:
    """mindmap.yaml が無いフォルダを指すと何も書かずに終わる（異常系）。"""
    # 準備
    root = tmp_path / "empty"
    root.mkdir()
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    out = out_dir / "配る.html"
    # 実行
    result = run_mindmap("export", "--workspace", str(root), "--out", str(out))
    # 検証
    assert result.returncode == 1
    assert str(root) in result.stderr
    assert not out.exists()


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    run_mindmap: RunMindmap,
    tmp_path: Path,
) -> None:
    """手で崩した YAML があると、前に書き出した --out のファイルを残して終わる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    out = tmp_path / "配る.html"
    assert run_mindmap("export", "--workspace", str(root), "--out", str(out)).returncode == 0
    before = out.read_bytes()
    (root / "decisions.yaml").write_text(
        yaml.safe_dump({"items": [make_item("D-1", status="完了")]}, allow_unicode=True),
        encoding="utf-8",
    )
    # 実行
    result = run_mindmap("export", "--workspace", str(root), "--out", str(out))
    # 検証
    assert result.returncode == 1
    assert "decisions.yaml: items[0].status:" in result.stderr
    assert out.read_bytes() == before


def test_error_when_out_dir_missing(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    run_mindmap: RunMindmap,
    tmp_path: Path,
) -> None:
    """--out の親のフォルダが無いと、フォルダを作らずに終わる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    out = tmp_path / "無い" / "配る.html"
    # 実行
    result = run_mindmap("export", "--workspace", str(root), "--out", str(out))
    # 検証
    assert result.returncode == 1
    assert result.stderr.startswith("エラー: ")
    assert str(out) in result.stderr
    assert "Traceback" not in result.stderr
    assert not (tmp_path / "無い").exists()


def test_error_when_download_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    run_mindmap: RunMindmap,
    tmp_path: Path,
) -> None:
    """jsDelivr に届かないと、何も書かずに終わる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    out = tmp_path / "配る.html"
    assert run_mindmap("export", "--workspace", str(root), "--out", str(out)).returncode == 0
    before = out.read_bytes()
    # 実行
    result = run_mindmap(
        "export",
        "--workspace",
        str(root),
        "--out",
        str(out),
        extra_env=UNREACHABLE_PROXY_ENV,
    )
    # 検証
    assert result.returncode == 1
    assert result.stderr.startswith("エラー: ")
    assert "https://cdn.jsdelivr.net/" in result.stderr
    assert "Traceback" not in result.stderr
    assert out.read_bytes() == before
