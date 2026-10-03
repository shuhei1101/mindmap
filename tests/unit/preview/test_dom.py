"""core/dom.ts（要素の組み立て・アイコン・状態の印・選択中）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# 空の断片（DocumentFragment）の nodeType
FRAGMENT_NODE_TYPE = 11

# 空の断片を `describe` が返す形（子が無い）
EMPTY_FRAGMENT = {"nodeType": FRAGMENT_NODE_TYPE, "childCount": 0}

# スクロールする要素の背景（ボタンの外）と、ボタンの上の押す位置
BACKGROUND_POINT = (150, 150)
BUTTON_POINT = (60, 60)

# ドラッグで動かした量（左へ・上へ）
DRAG_LEFT = 50
DRAG_UP = 30

# ドラッグを始める前のスクロール位置
START_SCROLL = 100

# スクロールする要素を置き、中にボタンを持たせる（ボタンは枠の左上から 50px の所に見える）
SCROLLER_SCRIPT = """() => {
    const scroller = document.createElement("div");
    scroller.id = "scroller";
    scroller.style.cssText = "position:fixed;left:0;top:0;width:200px;height:200px;overflow:auto";
    const content = document.createElement("div");
    content.style.cssText = "position:relative;width:1000px;height:1000px";
    const button = document.createElement("button");
    button.style.cssText = "position:absolute;left:150px;top:150px;width:40px;height:24px";
    content.append(button);
    scroller.append(content);
    document.body.append(scroller);
    scroller.scrollLeft = 100;
    scroller.scrollTop = 100;
    MindmapPreview.enableDragScroll(scroller);
}"""


def test_h(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """属性・リスナー・子を付けた要素を作る（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """() => {
            let clicks = 0;
            const child = document.createElement("i");
            const element = MindmapPreview.h({
                tag: "button",
                attrs: {
                    class: "b",
                    disabled: true,
                    title: null,
                    hidden: false,
                    onclick: () => { clicks += 1; },
                },
                children: ["a", 1, null, false, child],
            });
            element.dispatchEvent(new Event("click"));
            return {
                className: element.className,
                disabled: element.getAttribute("disabled"),
                hasTitle: element.hasAttribute("title"),
                hasHidden: element.hasAttribute("hidden"),
                children: Array.from(element.childNodes).map(
                    (node) => node.nodeType === Node.TEXT_NODE ? node.textContent : node.tagName,
                ),
                clicks,
            };
        }"""
    )
    # 検証
    assert result == {
        "className": "b",
        "disabled": "",
        "hasTitle": False,
        "hasHidden": False,
        "children": ["a", "1", "I"],
        "clicks": 1,
    }


def test_append(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """偽の値を除いて子を足す（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    children = preview_page.evaluate(
        """() => {
            const parent = document.createElement("div");
            parent.append(document.createElement("b"));
            MindmapPreview.append({parent, children: ["x", 0, undefined, false]});
            return Array.from(parent.childNodes).map(
                (node) => node.nodeType === Node.TEXT_NODE ? node.textContent : node.tagName,
            );
        }"""
    )
    # 検証
    assert children == ["B", "x", "0"]


def test_icon(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """装飾として隠した線のアイコンを返す（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """() => {
            const svg = MindmapPreview.icon("search");
            return {
                tag: svg.tagName,
                className: svg.getAttribute("class"),
                ariaHidden: svg.getAttribute("aria-hidden"),
                shapes: svg.children.length,
            };
        }"""
    )
    # 検証
    assert result["tag"] == "svg"
    assert result["className"] == "icon"
    assert result["ariaHidden"] == "true"
    assert result["shapes"] >= 1


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        pytest.param("決定済み", "svg.mark", id="decided"),
        pytest.param("要見直し", "svg.mark", id="needs_review"),
        pytest.param("完成", "svg.mark", id="completed"),
        pytest.param("知らない", None, id="unknown"),
        pytest.param(None, None, id="undefined"),
    ],
)
def test_status_mark(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    status: str | None,
    expected: str | None,
) -> None:
    """状態の印を返す。知らない状態と未指定は印なし（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """(status) => {
            const mark = MindmapPreview.statusMark(status ?? undefined);
            return mark === null ? null : `${mark.tagName}.${mark.getAttribute("class")}`;
        }""",
        status,
    )
    # 検証
    assert result == expected


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        pytest.param(
            "未決定",
            {"tag": "SPAN", "className": "st", "dataSt": "未決定", "text": "未決定", "marks": 1},
            id="open",
        ),
        pytest.param(None, EMPTY_FRAGMENT, id="undefined"),
    ],
)
def test_status_badge(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    status: str | None,
    expected: dict[str, Any],
) -> None:
    """印と状態の名前を並べる。状態を持たない項目は空の断片（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """(status) => {
            const node = MindmapPreview.statusBadge(status ?? undefined);
            if (node.nodeType === Node.DOCUMENT_FRAGMENT_NODE) {
                return {nodeType: node.nodeType, childCount: node.childNodes.length};
            }
            return {
                tag: node.tagName,
                className: node.className,
                dataSt: node.getAttribute("data-st"),
                text: node.textContent,
                marks: node.querySelectorAll("svg.mark").length,
            };
        }""",
        status,
    )
    # 検証
    assert result == expected


@pytest.mark.parametrize(
    ("weight", "expected"),
    [
        pytest.param("大", {"on": 3}, id="large"),
        pytest.param("中", {"on": 2}, id="medium"),
        pytest.param("小", {"on": 1}, id="small"),
        pytest.param("知らない", EMPTY_FRAGMENT, id="unknown"),
        pytest.param(None, EMPTY_FRAGMENT, id="undefined"),
    ],
)
def test_impact_badge(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    weight: str | None,
    expected: dict[str, Any],
) -> None:
    """影響度を目盛りで表す。大・中・小のどれでもない値と未指定は空の断片（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """(weight) => {
            const node = MindmapPreview.impactBadge(weight ?? undefined);
            if (node.nodeType === Node.DOCUMENT_FRAGMENT_NODE) {
                return {nodeType: node.nodeType, childCount: node.childNodes.length};
            }
            return {on: node.querySelectorAll("i.on").length};
        }""",
        weight,
    )
    # 検証
    assert result == expected


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        pytest.param(["UI", "性能"], {"tags": 2}, id="two_tags"),
        pytest.param(None, EMPTY_FRAGMENT, id="undefined"),
    ],
)
def test_tag_list(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    values: list[str] | None,
    expected: dict[str, Any],
) -> None:
    """タグを span.tag で並べる。未指定は空の断片（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """(values) => {
            const node = MindmapPreview.tagList(values ?? undefined);
            if (node.childNodes.length === 0) {
                return {nodeType: node.nodeType, childCount: 0};
            }
            return {tags: node.querySelectorAll("span.tag").length};
        }""",
        values,
    )
    # 検証
    assert result == expected


def test_deliverable_badge(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """箱のアイコンと「成果物」を持つ印を返す（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """() => {
            const badge = MindmapPreview.deliverableBadge();
            return {
                tag: badge.tagName,
                className: badge.className,
                icons: badge.querySelectorAll("svg.icon").length,
                text: badge.textContent,
            };
        }"""
    )
    # 検証
    assert result == {"tag": "SPAN", "className": "deliv-badge", "icons": 1, "text": "成果物"}


def test_empty_note(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """空のときの 1 行を p.empty で返す（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """() => {
            const note = MindmapPreview.emptyNote("該当なし");
            return {tag: note.tagName, className: note.className, text: note.textContent};
        }"""
    )
    # 検証
    assert result == {"tag": "P", "className": "empty", "text": "該当なし"}


@pytest.mark.parametrize(
    ("start", "expected_scroll"),
    [
        pytest.param(
            BACKGROUND_POINT,
            {"left": START_SCROLL + DRAG_LEFT, "top": START_SCROLL + DRAG_UP},
            id="background",
        ),
        pytest.param(BUTTON_POINT, {"left": START_SCROLL, "top": START_SCROLL}, id="button"),
    ],
)
def test_enable_drag_scroll(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    start: tuple[int, int],
    expected_scroll: dict[str, int],
) -> None:
    """背景のドラッグでスクロールし、ボタンの上では動かさない（正常系）。"""
    # 準備
    load_preview_scripts()
    preview_page.evaluate(SCROLLER_SCRIPT)
    start_x, start_y = start
    # 実行
    preview_page.mouse.move(start_x, start_y)
    preview_page.mouse.down()
    preview_page.mouse.move(start_x - DRAG_LEFT, start_y - DRAG_UP, steps=5)
    preview_page.mouse.up()
    # 検証
    result = preview_page.evaluate(
        """() => {
            const scroller = document.getElementById("scroller");
            return {
                left: scroller.scrollLeft,
                top: scroller.scrollTop,
                dragging: scroller.classList.contains("dragging"),
            };
        }"""
    )
    assert result == {**expected_scroll, "dragging": False}


@pytest.mark.parametrize(
    ("selected", "expected"),
    [
        pytest.param("D-2", {"selected": ["D-2"], "current": "D-2"}, id="item"),
        pytest.param(None, {"selected": [], "current": None}, id="closed"),
    ],
)
def test_mark_selected(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    selected: str | None,
    expected: dict[str, Any],
) -> None:
    """開いた項目だけに selected を付け、閉じたら外す（正常系）。"""
    # 準備
    load_preview_scripts()
    preview_page.evaluate(
        """() => {
            const main = document.createElement("main");
            for (const id of ["D-1", "D-2"]) {
                const row = document.createElement("div");
                row.dataset.id = id;
                main.append(row);
            }
            document.body.append(main);
        }"""
    )
    # 実行
    result = preview_page.evaluate(
        """(selected) => {
            MindmapPreview.markSelected(selected);
            return {
                selected: Array.from(document.querySelectorAll("main [data-id].selected"))
                    .map((row) => row.dataset.id),
                current: MindmapPreview.currentSelection(),
            };
        }""",
        selected,
    )
    # 検証
    assert result == expected
