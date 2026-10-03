"""プレビューを配る（記録を見るだけの 1 枚の HTML に書き出し、通信を止めたブラウザで開いて読む）の E2E テスト。

正常シナリオは、実際の jsDelivr から描画のライブラリとライセンスの本文を取って書き出す。
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import yaml
from playwright.sync_api import Page
from preview_helpers import OpenPreview, click_item_ball
from workspace_fixtures import MakeItem, MakeWorkspace, RunMindmap, SnapshotTree

# このファイルから見たリポジトリの直下（tests/e2e/単一ユースケース の 3 つ上）
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

# 資料 A-1 の本文（表と mermaid の図を 1 つずつ持つ）
DOC_BODY = """## 仕様

| 列 | 値 |
| --- | --- |
| 数 | 3 |

```mermaid
flowchart LR
  A --> B
```
"""

# 画面に出ない書き込みの操作（ボタンの名前に含まれる語）
WRITE_ACTION_PATTERN = re.compile("追加|編集|削除|送信|保存")

# 中に持つライブラリごとの、表示に出る名前・ライセンスの名前・著作権の表示（雛形の URL のパッケージ名 → 表示）
EXPECTED_LICENSES = {
    "marked": ("marked", "MIT", "Copyright (c) 2018+, MarkedJS"),
    "dompurify": ("DOMPurify", "Apache-2.0", "(c) Cure53 and other contributors"),
    "elkjs": ("elkjs", "EPL-2.0", "(c) Kiel University and others"),
    "mermaid": ("mermaid", "MIT", "Copyright (c) 2014 - 2022 Knut Sveidqvist"),
}

# elkjs のソースコードの入手先（リポジトリ）
ELKJS_REPOSITORY = "https://github.com/kieler/elkjs"

# 画面に出ているボタンの名前（文字と aria-label）を読む
BUTTON_LABELS_SCRIPT = """() => [...document.querySelectorAll('button, [role="button"]')].map(
    b => `${b.textContent ?? ''} ${b.getAttribute('aria-label') ?? ''}`
)"""

# 読めなかったライブラリの知らせ（role="alert"）を数える
ALERT_SELECTOR = '[role="alert"]'

# 描画のライブラリを描いた後の図（SVG）が出るまで待つ上限ミリ秒
DIAGRAM_TIMEOUT_MS = 20_000


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


def _is_not_file_url(url: str) -> bool:
    """`file:` で始まらない URL（外への要求）かを返す。"""
    return not url.startswith("file:")


def _read_element(html: str, open_tag: str) -> str:
    """HTML の指定した script 要素の中身を返す。"""
    return html.split(open_tag, 1)[1].split("</script>", 1)[0]


def _template_versions() -> dict[str, str]:
    """雛形の描画のライブラリの `<script src>` から、パッケージ名 → 版を読む。"""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    return dict(re.findall(r'src="https://cdn\.jsdelivr\.net/npm/([^@"]+)@([^/"]+)/', template))


def _records(make_item: MakeItem, valid_settings: dict[str, Any]) -> list[dict[str, Any]]:
    """検討事項 D-1 と、D-1 を前提に持つ D-2、本文を持つ資料 A-1。"""
    placement: dict[str, Any] = {
        "target": valid_settings["targets"][0]["name"],
        "category": valid_settings["categories"][0]["name"],
        "phase": valid_settings["phases"][0],
    }
    return [
        make_item("D-1", status="未決定", **placement),
        make_item("D-2", status="未決定", depends_on=["D-1"], **placement),
        make_item("A-1", status="完成"),
    ]


def test_normal(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    run_mindmap: RunMindmap,
    open_preview: OpenPreview,
    snapshot_tree: SnapshotTree,
    page: Page,
    tmp_path: Path,
    valid_settings: dict[str, Any],
) -> None:
    """記録を人に渡すために書き出し、通信を止めたブラウザで開いて本文・図・マップ・つながりを読む（正常系）。"""
    # 準備
    root = make_workspace(*_records(make_item, valid_settings), bodies={"A-1.md": DOC_BODY})
    assert run_mindmap("build", "--workspace", str(root)).returncode == 0
    before = snapshot_tree(root)
    out = tmp_path / "配る.html"
    # 実行（書き出す）
    result = run_mindmap("export", "--workspace", str(root), "--out", str(out))
    # 検証（書き出し）
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"path": str(out)}
    html = out.read_text(encoding="utf-8")
    references = _ExternalReferences()
    references.feed(html)
    assert references.found == []
    licenses = _read_element(html, LICENSES_ELEMENT_OPEN)
    versions = _template_versions()
    for package, (name, license_name, notice) in EXPECTED_LICENSES.items():
        assert f"{name} {versions[package]}" in licenses
        assert notice in licenses
        assert f"License: {license_name}" in licenses
    assert f"{ELKJS_REPOSITORY}/tree/{versions['elkjs']}" in licenses
    assert snapshot_tree(root) == before
    # 実行（外への通信を全て止めたブラウザで開く）
    blocked: list[str] = []

    def _block(route: Any) -> None:
        """外への要求を数えて失敗させる。"""
        blocked.append(route.request.url)
        route.abort()

    page.route(_is_not_file_url, _block)
    button_labels: list[str] = []
    open_preview(out)
    button_labels += page.evaluate(BUTTON_LABELS_SCRIPT)
    assert page.locator(ALERT_SELECTOR).count() == 0
    # 検討事項のマップに D-1 と D-2 が描かれる
    page.click('nav.tabbar a[data-tab="decisions"]')
    page.wait_for_selector('#decision-map button[data-node="D-1"]')
    map_ids = page.eval_on_selector_all(
        "#decision-map .map-node.n-item", "nodes => nodes.map(n => n.dataset.node).sort()"
    )
    assert map_ids == ["D-1", "D-2"]
    button_labels += page.evaluate(BUTTON_LABELS_SCRIPT)
    assert page.locator(ALERT_SELECTOR).count() == 0
    # A-1 の詳細パネルの本文に、表が table 要素で、mermaid の図が SVG で描かれる
    page.click('nav.tabbar a[data-tab="docs"]')
    page.click('.doc-card[data-id="A-1"]')
    page.wait_for_selector("aside.panel.open .mermaid svg", timeout=DIAGRAM_TIMEOUT_MS)
    assert page.locator("aside.panel .md table").count() == 1
    assert page.locator("aside.panel .mermaid svg").count() == 1
    button_labels += page.evaluate(BUTTON_LABELS_SCRIPT)
    assert page.locator(ALERT_SELECTOR).count() == 0
    # つながりに玉が描かれる（D-1 の玉を押すと、詳細パネルに D-1 が開く）
    page.click('nav.tabbar a[data-tab="graph"]')
    page.wait_for_selector("#graph-canvas")
    click_item_ball(page, "D-1")
    assert page.inner_text("aside.panel .d-title") == "D-1の題"
    button_labels += page.evaluate(BUTTON_LABELS_SCRIPT)
    assert page.locator(ALERT_SELECTOR).count() == 0
    # 検証（ブラウザ）
    assert blocked == []
    # ボタンを 1 つも読めていないと、書き込む操作が無いことを確かめたことにならない
    assert button_labels
    assert [label for label in button_labels if WRITE_ACTION_PATTERN.search(label)] == []
    assert snapshot_tree(root) == before


def test_error_when_schema_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    run_mindmap: RunMindmap,
    snapshot_tree: SnapshotTree,
    tmp_path: Path,
) -> None:
    """手で崩した YAML があると、書き出す先のファイルを書き換えずに終わる（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    assert run_mindmap("build", "--workspace", str(root)).returncode == 0
    out = tmp_path / "配る.html"
    assert run_mindmap("export", "--workspace", str(root), "--out", str(out)).returncode == 0
    (root / "decisions.yaml").write_text(
        yaml.safe_dump({"items": [make_item("D-1", status="完了")]}, allow_unicode=True),
        encoding="utf-8",
    )
    out_before = out.read_bytes()
    workspace_before = snapshot_tree(root)
    # 実行
    result = run_mindmap("export", "--workspace", str(root), "--out", str(out))
    # 検証
    assert result.returncode != 0
    assert "decisions.yaml" in result.stderr
    assert "status" in result.stderr
    assert out.read_bytes() == out_before
    assert snapshot_tree(root) == workspace_before
