"""項目の詳細を読む（案・関係・本文・全画面・図の拡大・関係する項目への移動）の E2E テスト。"""

from __future__ import annotations

import re
from typing import Any

from playwright.sync_api import Page
from preview_helpers import BuildPreview, OpenPreview
from workspace_fixtures import MakeItem

# 本文に mermaid の図を 1 つ持つ Markdown
BODY_WITH_DIAGRAM = """# 要件

本文の段落

```mermaid
flowchart LR
  A --> B
```
"""

# 広い幅の画面（詳細パネルが本文を寄せる幅）
WIDE_SIZE = (1920, 1080)

# 図を描き終わるまで待つ上限ミリ秒
DIAGRAM_TIMEOUT_MS = 20_000

# 全画面の外側（後ろの幕）を押す位置
BACKDROP_POINT = (4, 4)

# 本文のスクリプトが実行されたときに残す印
SCRIPT_BODY = """<script>window.__bodyScriptRan = true</script>

<img src="missing.png" onerror="window.__bodyScriptRan = true">

本文の文字
"""


def _related(page: Page) -> dict[str, list[str]]:
    """詳細パネルの関係の節（見出し → 押せる項目の ID）を返す。"""
    return page.evaluate(
        """() => Object.fromEntries([...document.querySelectorAll('aside.panel .d-sec')]
            .filter(sec => sec.querySelector('.d-list'))
            .map(sec => [sec.querySelector('h3').textContent, [...sec.querySelectorAll('button.idlink')].map(b => b.textContent)]))"""
    )


def _decision_records(make_item: MakeItem) -> list[dict[str, Any]]:
    """案・前提・後続・進めるタスク・関連・参照元・図つきの本文を持つ検討事項 D-3 と、つながる項目を返す。"""
    return [
        make_item("D-1", status="決定済み", answer="種類ごとに分ける"),
        make_item(
            "D-3",
            status="要見直し",
            depends_on=["D-1"],
            related=["R-1"],
            body="D-3.md",
            options=[
                {"key": "A", "content": "表で見せる", "adopted": True, "reason": "並べやすい"},
                {"key": "B", "content": "カードで見せる", "adopted": False, "reason": "数が多いと長い"},
            ],
        ),
        make_item("D-5", status="未決定", depends_on=["D-3"]),
        make_item("T-2", status="進行中", **{"for": ["D-3"]}),
        make_item("R-1", question="何を調べたか"),
        make_item("N-1", content="メモの中身", related=["D-3"]),
    ]


def test_normal(
    build_preview: BuildPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """案・関係・本文と図を読み、全画面と図の拡大で読み、関係する項目へ移って戻る（正常系）。"""
    # 準備
    path = build_preview(
        *_decision_records(make_item),
        settings=valid_settings,
        bodies={"D-3.md": BODY_WITH_DIAGRAM},
    )
    page = open_preview(path, "#tab=decisions&view=table", width=WIDE_SIZE[0], height=WIDE_SIZE[1])
    box_script = "(() => { const r = document.querySelector('main#main').getBoundingClientRect(); return [r.left, r.right]; })()"
    left_before = page.evaluate(box_script)[0]
    # 実行
    page.click('table.grid button.row-open[data-id="D-3"]')
    page.wait_for_selector("aside.panel.open .mermaid svg", timeout=DIAGRAM_TIMEOUT_MS)
    # 検証（案）: 案 A（採用）と案 B（不採用と理由）のカードが縦に並ぶ
    options = page.eval_on_selector_all(
        "aside.panel .opt",
        "opts => opts.map(o => [o.querySelector('.key').textContent, o.querySelector('.res').textContent, o.getBoundingClientRect().top, o.textContent.includes('数が多いと長い')])",
    )
    assert [row[:2] for row in options] == [["A", "採用"], ["B", "不採用"]]
    assert options[0][2] < options[1][2]
    assert options[1][3] is True
    # 検証（関係）
    related = _related(page)
    assert related["前提"] == ["D-1"]
    assert related["後続の項目"] == ["D-5"]
    assert related["関連タスク"] == ["T-2"]
    assert related["関連"] == ["R-1"]
    assert related["この項目を参照している項目"] == ["N-1"]
    # 検証（本文と図）
    assert page.inner_text('aside.panel .md [data-md-level="1"]') == "要件"
    for action in ("diagram-zoom", "diagram-raw", "diagram-copy"):
        assert page.locator(f'aside.panel button[data-act="{action}"]').count() == 1
    # 幅 1920px では、パネルを開いている間、本文がパネルの分だけ左へ寄り、パネルに重ならない
    left_after, right_after = page.evaluate(box_script)
    panel_left = page.evaluate("document.querySelector('aside.panel').getBoundingClientRect().left")
    assert left_after < left_before
    assert right_after <= panel_left
    # 全画面に切り替え、図の拡大は中身の切り替えで、モーダルが 2 枚重ならない
    page.click('aside.panel button[data-act="full"]')
    page.wait_for_selector("dialog.full[open] .mermaid svg", timeout=DIAGRAM_TIMEOUT_MS)
    page.click('dialog.full button[data-act="diagram-zoom"]')
    page.wait_for_selector("dialog.full .full-viewer .v-stage svg")
    assert page.locator("dialog[open]").count() == 1
    page.click('dialog.full button[data-act="diagram-close"]')
    page.wait_for_selector("dialog.full .panel-body", state="visible")
    # 全画面に全てを閉じるボタンが無く、外側を押すと D-3 の詳細パネルに戻る
    assert page.locator('dialog.full button[data-act="close"]').count() == 0
    page.mouse.click(*BACKDROP_POINT)
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "D-3の題"
    # D-1 を押すと詳細パネルに D-1 が開き、URL のハッシュが D-1 を指す
    page.click("aside.panel .d-sec:has(h3:text-is('前提')) button.idlink")
    page.wait_for_function("document.querySelector('aside.panel .d-title')?.textContent === 'D-1の題'")
    assert "id=D-1" in page.evaluate("location.hash")
    # 戻る操作で D-3 の詳細パネルに戻り、URL のハッシュが D-3 を指す
    page.go_back()
    page.wait_for_function("document.querySelector('aside.panel .d-title')?.textContent === 'D-3の題'")
    assert "id=D-3" in page.evaluate("location.hash")


def test_error_when_body_has_script(
    build_preview: BuildPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """本文の script と onerror 属性は実行せず、詳細パネルの中にも残さない（異常系）。"""
    # 準備
    path = build_preview(
        make_item("A-1"), settings=valid_settings, bodies={"A-1.md": SCRIPT_BODY}
    )
    # 実行
    page = open_preview(path, "#tab=docs&id=A-1")
    page.wait_for_selector("aside.panel.open .md")
    page.wait_for_timeout(1_000)
    # 検証
    assert page.evaluate("window.__bodyScriptRan") is None
    assert page.locator("aside.panel script").count() == 0
    assert page.locator("aside.panel [onerror]").count() == 0
    assert "本文の文字" in page.inner_text("aside.panel .md")


def test_error_when_render_library_unavailable(
    build_preview: BuildPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    page: Page,
) -> None:
    """本文の描画のライブラリ（marked・mermaid）が読めないと、名前を出し、本文を文字のまま読める（異常系）。"""
    # 準備
    path = build_preview(
        make_item("A-1"), settings=valid_settings, bodies={"A-1.md": BODY_WITH_DIAGRAM}
    )
    page.route(re.compile(r"/npm/(marked|mermaid)@"), lambda route: route.abort())
    # 実行
    open_preview(path, "#tab=docs&id=A-1")
    page.wait_for_selector("aside.panel.open .md .lib-error[role=alert]")
    # 検証
    notice = page.inner_text("aside.panel .md .lib-error[role=alert]")
    assert "marked" in notice
    assert "mermaid" in notice
    raw = page.inner_text("aside.panel .md .md-raw")
    assert "# 要件" in raw
    assert "flowchart LR" in raw
