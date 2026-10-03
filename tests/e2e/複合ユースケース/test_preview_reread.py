"""プレビューで記録を読み返す（概要から項目の詳細を開き、つながりで関係を読み、URL に残す）の E2E テスト。"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import Page
from preview_helpers import BuildPreview, OpenPreview, click_item_ball
from workspace_fixtures import MakeItem, SnapshotTree

# 本文に mermaid の図を持つ Markdown
BODY_WITH_DIAGRAM = """# 納品物の本文

```mermaid
flowchart LR
  A --> B
```
"""

# 新しいタブで開き直した画面が描き終わるまで待つ上限ミリ秒
RENDER_TIMEOUT_MS = 20_000


def _settings(valid_settings: dict[str, Any]) -> dict[str, Any]:
    """カテゴリー 2 つ・フェーズ 3 つ・納品物 1 つを持つ設定を返す。"""
    return {
        **valid_settings,
        "categories": [
            {"name": "データ構造", "target": "mindmap", "summary": "YAML の種類とキー"},
            {"name": "画面", "target": "mindmap", "summary": "プレビューの画面"},
        ],
        "goal": {
            "phase": "要件",
            "summary": "要件が決まる",
            "deliverables": [{"title": "仕様書", "doc": "A-1"}],
        },
    }


def _records(make_item: MakeItem) -> list[dict[str, Any]]:
    """未決定・決定済み・要見直し・保留を含み、依存でつながる検討事項と、そのほかの種類の項目を返す。"""
    placed: dict[str, Any] = {"target": "mindmap"}
    return [
        make_item("D-1", status="決定済み", category="データ構造", phase="目的", **placed),
        make_item(
            "D-3", status="要見直し", category="画面", phase="要件", depends_on=["D-1"], **placed
        ),
        make_item(
            "D-5", status="未決定", category="画面", phase="構成", depends_on=["D-3"], **placed
        ),
        make_item("D-6", status="保留", category="データ構造", phase="構成", **placed),
        make_item("T-2", status="進行中", **{"for": ["D-3"]}),
        make_item("R-1", question="何を調べたか"),
        make_item("A-1", deliverable=True, status="完成", kind="仕様書"),
        make_item("G-1"),
        make_item("N-1"),
        make_item("L-1"),
    ]


def test_normal(
    build_preview: BuildPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    snapshot_tree: SnapshotTree,
    page: Page,
) -> None:
    """概要の要見直しから D-3 の詳細を開き、つながりで D-3 を押して、終えた URL を開き直す（正常系）。"""
    # 準備
    path = build_preview(
        *_records(make_item),
        settings=_settings(valid_settings),
        bodies={"A-1.md": BODY_WITH_DIAGRAM},
    )
    root = path.parent
    before = snapshot_tree(root)
    # 実行（概要の要見直しのタイルで D-3 を押す）
    open_preview(path)
    page.click('#tile-review button[data-id="D-3"]')
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "D-3の題"
    # 実行（つながりを開く。開いている詳細パネルは閉じない）
    page.click('nav.tabbar a[data-tab="graph"]')
    page.wait_for_selector("#graph-canvas")
    assert page.inner_text("aside.panel .d-title") == "D-3の題"
    # 実行（D-3 の玉を押す）
    click_item_ball(page, "D-3")
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "D-3の題"
    final_url = page.url
    # 検証（終えたときの URL を新しいタブで開くと、つながりの画面と D-3 の詳細パネルが開く）
    reopened = page.context.new_page()
    reopened.goto(final_url)
    reopened.wait_for_selector("main#main > *", state="attached", timeout=RENDER_TIMEOUT_MS)
    reopened.wait_for_selector("aside.panel.open")
    assert reopened.get_attribute('nav.tabbar a[data-tab="graph"]', "aria-current") == "page"
    assert reopened.inner_text("aside.panel .d-title") == "D-3の題"
    assert reopened.locator("#graph-canvas").count() == 1
    # 検証（ワークスペースの YAML と preview.html の中身が、開く前と同じ）
    assert snapshot_tree(root) == before
