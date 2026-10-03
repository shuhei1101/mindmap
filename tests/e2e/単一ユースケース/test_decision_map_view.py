"""検討事項をマップで辿る（マップ・状態で絞る・枝と依存を辿る・ボードと表への切り替え）の E2E テスト。"""

from __future__ import annotations

import re
from typing import Any

from playwright.sync_api import Page
from preview_helpers import BuildPreview, OpenPreview, row_ids
from workspace_fixtures import MakeItem

# マップを広い幅で出す画面の幅（px）
WIDE_WIDTH = 1280

# マップの代わりに字下げの一覧を出す画面の幅（px）
NARROW_WIDTH = 390

# 薄くした項目の不透明度の上限（強調していない項目は 1 より薄い）
FADED_OPACITY_LIMIT = 1.0

# 選んだ項目から根までの枝の本数（根 → カテゴリー → フェーズ → 項目）
TREE_EDGES_TO_ROOT = 3

# 依存の線の本数（D-1 → D-3 と D-3 → D-5）
DEPENDENCY_EDGES = 2

# まとめて切り替える箱（状態の印の並びの右端）と、状態の印のチェックボックス（箱を除く）
TOGGLE_ALL_BOX = ".legend .legend-all-check input"
STATUS_INPUTS = ".legend label:not(.legend-all-check) input"

# 全ての状態を隠したときに出す文
NO_SHOWN_STATUS_TEXT = "表示する検討事項はありません。"

# マップに検討事項が 1 件も描かれていない
NO_MAP_ITEM_SCRIPT = "!document.querySelector('#decision-map button.n-item')"


def _settings(valid_settings: dict[str, Any]) -> dict[str, Any]:
    """カテゴリーを 2 つ持つ設定を返す。"""
    return {
        **valid_settings,
        "categories": [
            {"name": "データ構造", "target": "mindmap", "summary": "YAML の種類とキー"},
            {"name": "画面", "target": "mindmap", "summary": "プレビューの画面"},
        ],
    }


def _decisions(make_item: MakeItem) -> list[dict[str, Any]]:
    """対象 1・カテゴリー 2・フェーズ 2 にまたがる検討事項（D-1 → D-3 → D-5 と依存でつながる）を返す。"""
    return [
        make_item(
            "D-1",
            status="決定済み",
            target="mindmap",
            category="データ構造",
            phase="目的",
            answer="種類ごとに分ける",
        ),
        make_item(
            "D-3",
            status="要見直し",
            target="mindmap",
            category="画面",
            phase="要件",
            depends_on=["D-1"],
        ),
        make_item(
            "D-5",
            status="未決定",
            target="mindmap",
            category="画面",
            phase="構成",
            depends_on=["D-3"],
        ),
    ]


def _map_item_ids(page: Page) -> list[str]:
    """マップに描かれている検討事項の ID を並べ替えて返す。"""
    ids = page.eval_on_selector_all(
        "#decision-map button.n-item", "nodes => nodes.map(n => n.dataset.node)"
    )
    return sorted(ids)


def _segment_boxes(page: Page) -> list[list[float]]:
    """表示形式の切り替えのボタンの位置と幅を返す。"""
    return page.evaluate(
        "[...document.querySelectorAll('.segment button')].map(b => { const r = b.getBoundingClientRect(); return [r.left, r.top, r.width]; })"
    )


def _opacity(page: Page, selector: str) -> float:
    """要素の見た目の不透明度を返す。"""
    return float(
        page.evaluate(
            "(selector) => getComputedStyle(document.querySelector(selector)).opacity", selector
        )
    )


def test_normal(
    build_preview: BuildPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """マップで状態を絞り、項目を押して枝と依存を辿り、ボード・表に切り替える（正常系）。"""
    # 準備
    path = build_preview(*_decisions(make_item), settings=_settings(valid_settings))
    # 実行・検証（マップ）
    page = open_preview(path, "#tab=decisions&view=map", width=WIDE_WIDTH)
    page.wait_for_selector("#decision-map button.n-item")
    assert _map_item_ids(page) == ["D-3", "D-5"]
    page.click('.legend label:has(input[value="決定済み"])')
    page.wait_for_selector('#decision-map button[data-node="D-1"]')
    assert _map_item_ids(page) == ["D-1", "D-3", "D-5"]
    # D-3 を押すと、根までの枝と D-1・D-5 への依存の線を強調し、それ以外を薄くする
    page.click('#decision-map button[data-node="D-3"]')
    page.wait_for_selector("#decision-map.focusing")
    related = page.eval_on_selector_all(
        "#decision-map button.n-item.rel", "nodes => nodes.map(n => n.dataset.node)"
    )
    assert sorted(related) == ["D-1", "D-3", "D-5"]
    assert page.locator("#decision-map .edge-tree.rel").count() == TREE_EDGES_TO_ROOT
    assert page.locator("#decision-map .edge-dep.rel").count() == DEPENDENCY_EDGES
    faded_selector = '#decision-map [data-node="category:mindmap/データ構造"]'
    assert _opacity(page, faded_selector) < FADED_OPACITY_LIMIT
    # 詳細パネルに D-3 が開き、URL のハッシュが検討事項のタブと D-3 を指す
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "D-3の題"
    hash_text = page.evaluate("location.hash")
    assert "tab=decisions" in hash_text
    assert "id=D-3" in hash_text
    # 切り替えのボタンの位置と幅が、マップ・ボード・表で変わらない
    boxes = {"map": _segment_boxes(page)}
    # 実行・検証（ボード）
    page.click('.segment button[data-view="board"]')
    page.wait_for_selector(".board")
    columns = page.eval_on_selector_all(
        ".board section.board-col",
        "cols => Object.fromEntries(cols.map(c => [c.getAttribute('aria-label'), [...c.querySelectorAll('.card')].map(k => k.dataset.id)]))",
    )
    assert columns["要見直し"] == ["D-3"]
    assert columns["未決定"] == ["D-5"]
    assert columns["決定済み"] == ["D-1"]
    boxes["board"] = _segment_boxes(page)
    # 実行・検証（表）
    page.click('.segment button[data-view="table"]')
    page.wait_for_selector("table.grid")
    boxes["table"] = _segment_boxes(page)
    assert boxes["map"] == boxes["board"] == boxes["table"]
    ready = page.evaluate(
        """() => {
            const header = [...document.querySelectorAll('table.grid thead th')]
                .find(th => th.querySelector('.th-sort').textContent === '着手可否');
            const column = header.dataset.col;
            return document.querySelector(`table.grid tr[data-id="D-5"] td[data-col="${column}"]`).textContent;
        }"""
    )
    assert ready == "前提待ち"


def test_normal_when_keyword(
    build_preview: BuildPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """キーワードをタイトルに含む項目を強調し、状態の印に一致した件数のバッジを付ける（正常系）。"""
    # 準備
    common: dict[str, Any] = {"target": "mindmap", "category": "データ構造", "phase": "要件"}
    path = build_preview(
        make_item("D-2", status="未決定", title="保存形式を決める", **common),
        make_item("D-3", status="要見直し", title="保存先を決める", **common),
        make_item("D-5", status="未決定", title="一覧の並びを決める", **common),
        settings=valid_settings,
    )
    page = open_preview(path, "#tab=decisions&view=map", width=WIDE_WIDTH)
    page.wait_for_selector("#decision-map button.n-item")
    # 実行
    page.fill("input.map-q", "保存")
    page.wait_for_selector("#decision-map .map-node.hit")
    # 検証
    hits = page.eval_on_selector_all(
        "#decision-map .map-node.hit", "nodes => nodes.map(n => n.dataset.node)"
    )
    assert sorted(hits) == ["D-2", "D-3"]
    undecided_badge = page.inner_text('.legend label:has(input[value="未決定"]) .hit-n')
    review_badge = page.inner_text('.legend label:has(input[value="要見直し"]) .hit-n')
    assert (undecided_badge, review_badge) == ("1", "1")


def test_normal_when_narrow(
    build_preview: BuildPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """狭い幅では、マップの代わりに字下げした縦の一覧を出し、横スクロールが出ない（正常系）。"""
    # 準備
    path = build_preview(*_decisions(make_item), settings=_settings(valid_settings))
    # 実行
    page = open_preview(path, "#tab=decisions&view=map", width=NARROW_WIDTH, height=844)
    page.wait_for_selector("nav.map-outline", state="visible")
    # 検証
    assert not page.is_visible("#decision-map")
    outline = page.inner_text("nav.map-outline")
    # 対象 → カテゴリー → フェーズ → 検討事項の順に字下げして並ぶ
    positions = [outline.index(word) for word in ("mindmap", "画面", "要件", "D-3の題", "構成", "D-5の題")]
    assert positions == sorted(positions)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")


def test_error_when_layout_library_unavailable(
    build_preview: BuildPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
    page: Page,
) -> None:
    """配置のライブラリ（elkjs）が読めないと、マップの場所に名前を出し、表では項目を読める（異常系）。"""
    # 準備
    path = build_preview(
        make_item("D-5", status="未決定", target="mindmap", category="データ構造", phase="構成"),
        settings=valid_settings,
    )
    page.route(re.compile(r"/npm/elkjs@"), lambda route: route.abort())
    # 実行
    open_preview(path, "#tab=decisions&view=map", width=WIDE_WIDTH)
    page.wait_for_selector("main .lib-error[role=alert]")
    # 検証
    assert "elkjs" in page.inner_text("main .lib-error[role=alert]")
    page.click('.segment button[data-view="table"]')
    page.wait_for_selector("table.grid")
    assert row_ids(page) == ["D-5"]


def _toggle_all_box(page: Page) -> dict[str, bool]:
    """まとめて切り替える箱の、チェック・横棒・状態の印の並びの右端かを返す。"""
    return page.eval_on_selector(
        TOGGLE_ALL_BOX,
        """box => ({
            checked: box.checked,
            indeterminate: box.indeterminate,
            last: box.closest('.legend').lastElementChild === box.closest('label'),
        })""",
    )


def _status_checks(page: Page) -> list[bool]:
    """状態の印のチェックを、並びの順に返す。"""
    return page.eval_on_selector_all(STATUS_INPUTS, "inputs => inputs.map(i => i.checked)")


def test_normal_when_toggle_all_statuses(
    build_preview: BuildPreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    valid_settings: dict[str, Any],
) -> None:
    """まとめて切り替える箱で全ての状態を出し・隠し、箱と状態の印をそろえ、空の旨の文を出す（正常系）。"""
    # 準備
    path = build_preview(*_decisions(make_item), settings=_settings(valid_settings))
    # 実行・検証（開く: 決定済みを隠した木と、横棒の箱）
    page = open_preview(path, "#tab=decisions&view=map", width=WIDE_WIDTH)
    page.wait_for_selector("#decision-map button.n-item")
    assert _map_item_ids(page) == ["D-3", "D-5"]
    assert _toggle_all_box(page) == {"checked": False, "indeterminate": True, "last": True}
    # 実行・検証（1 回目: 全ての状態を出す）
    page.click(TOGGLE_ALL_BOX)
    page.wait_for_selector('#decision-map button[data-node="D-1"]')
    assert _map_item_ids(page) == ["D-1", "D-3", "D-5"]
    assert _toggle_all_box(page) == {"checked": True, "indeterminate": False, "last": True}
    assert _status_checks(page) == [True, True, True]
    assert not page.is_visible("p.map-empty")
    # 実行・検証（2 回目: 全ての状態を隠す）
    page.click(TOGGLE_ALL_BOX)
    page.wait_for_function(NO_MAP_ITEM_SCRIPT)
    assert _map_item_ids(page) == []
    assert _toggle_all_box(page) == {"checked": False, "indeterminate": False, "last": True}
    assert _status_checks(page) == [False, False, False]
    assert page.inner_text("p.map-empty") == NO_SHOWN_STATUS_TEXT
