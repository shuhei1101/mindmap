"""core/libs.ts（描画のライブラリの有無と呼び出し）の単体テスト。"""

from __future__ import annotations

from playwright.sync_api import Page

from .fixture_types import LoadLibrary, LoadPreviewScripts

# 本文の Markdown（見出し・表・実行される属性を持つ画像・mermaid のコードブロック）
MARKDOWN_SOURCE = (
    "# 見出し\n\n"
    "| 列 A | 列 B |\n| --- | --- |\n| 1 | 2 |\n\n"
    "<img src=x onerror=alert(1)>\n\n"
    "```mermaid\nflowchart TD\n  A --> B\n```\n"
)


def test_missing_libraries(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """グローバルが無いものだけ返す（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    missing = preview_page.evaluate(
        """() => {
            window.marked = {};
            return MindmapPreview.missingLibraries(["marked", "DOMPurify"]);
        }"""
    )
    # 検証
    assert missing == ["DOMPurify"]


def test_library_notice(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """名前を並べた知らせを返す（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    notice = preview_page.evaluate(
        """() => {
            const element = MindmapPreview.libraryNotice({names: ["marked", "DOMPurify"], what: "本文"});
            return {role: element.getAttribute("role"), text: element.textContent};
        }"""
    )
    # 検証
    assert notice["role"] == "alert"
    assert "読み込めなかったライブラリ: marked・DOMPurify" in notice["text"]
    assert "通信を確認して、ページを再読み込みしてください。" in notice["text"]


def test_render_markdown(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, load_library: LoadLibrary
) -> None:
    """無害化して描き、図の入れ物を作る（正常系）。"""
    # 準備
    load_preview_scripts()
    load_library("marked")
    load_library("DOMPurify")
    # 実行
    result = preview_page.evaluate(
        """(source) => {
            const root = MindmapPreview.renderMarkdown(source);
            const containers = root.querySelectorAll("[data-source]");
            return {
                hasHeading: root.querySelector("h1") !== null,
                hasTable: root.querySelector("table") !== null,
                html: root.innerHTML,
                containerCount: containers.length,
                source: containers.length > 0 ? containers[0].getAttribute("data-source") : null,
            };
        }""",
        MARKDOWN_SOURCE,
    )
    # 検証
    assert result["hasHeading"] is True
    assert result["hasTable"] is True
    assert "onerror" not in result["html"]
    assert result["containerCount"] == 1
    assert "flowchart TD" in result["source"]


def test_render_markdown_when_library_missing(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """ライブラリが無ければ知らせと原文（正常系）。"""
    # 準備
    load_preview_scripts()
    # 実行
    result = preview_page.evaluate(
        """(source) => {
            const root = MindmapPreview.renderMarkdown(source);
            return {
                alert: root.querySelector('[role="alert"]').textContent,
                pre: root.querySelector("pre").textContent,
            };
        }""",
        MARKDOWN_SOURCE,
    )
    # 検証
    for name in ("marked", "DOMPurify", "mermaid"):
        assert name in result["alert"]
    assert result["pre"] == MARKDOWN_SOURCE


def test_render_diagrams(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts, load_library: LoadLibrary
) -> None:
    """図を SVG に描き、描けない図は原文を残す（正常系）。"""
    # 準備
    load_preview_scripts()
    load_library("mermaid")
    broken_source = "これは図の構文ではない ((("
    # 実行
    result = preview_page.evaluate(
        """async (brokenSource) => {
            const root = document.createElement("div");
            for (const source of ["flowchart TD\\n  A --> B", brokenSource]) {
                const container = document.createElement("div");
                container.setAttribute("data-source", source);
                root.append(container);
            }
            document.body.append(root);
            await MindmapPreview.renderDiagrams(root);
            return [...root.children].map((container) => ({
                hasSvg: container.querySelector("svg") !== null,
                text: container.textContent,
            }));
        }""",
        broken_source,
    )
    # 検証
    assert result[0]["hasSvg"] is True
    assert result[1]["hasSvg"] is False
    assert "この図は表示できませんでした。原文を表示します。" in result[1]["text"]
    assert broken_source in result[1]["text"]
