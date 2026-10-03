"""プレビューを開く（`build` が書き出した `preview.html` と、`export` が書き出した配る書き出しを開く）の結合テスト。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from preview_fixture_types import BODY_WITH_DIAGRAM, OpenPreview, WritePreview
from workspace_fixtures import MakeItem, MakeWorkspace, RunMindmap

# 描画のライブラリの配信元への要求（全て失敗させるときの URL の形）
LIBRARY_HOST_PATTERN = "https://cdn.jsdelivr.net/**"

# 描画のライブラリを描いた後の図（SVG）が出るまで待つ上限ミリ秒
DIAGRAM_TIMEOUT_MS = 20_000


# `file:` 以外の URL への要求（外への要求）を全て拾う条件
def _is_not_file_url(url: str) -> bool:
    """`file:` で始まらない URL かを返す。"""
    return not url.startswith("file:")


def _row_ids(page: Any) -> list[str]:
    """表に並んでいる行の ID を上から返す。"""
    return page.eval_on_selector_all("table.grid tbody tr", "rows => rows.map(r => r.dataset.id)")


def test_normal(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """ハッシュが指す画面・表示形式・項目を開く（正常系）。"""
    # 準備
    path = write_preview(
        make_item("D-1"),
        make_item("D-3", status="要見直し", body="D-3.md"),
        bodies={"D-3.md": BODY_WITH_DIAGRAM},
    )
    hash_text = "#tab=decisions&view=table&id=D-3"
    # 実行
    page = open_preview(path, hash_text)
    page.wait_for_selector("aside.panel.open .mermaid svg", timeout=DIAGRAM_TIMEOUT_MS)
    # 検証
    assert page.get_attribute('nav.tabbar a[data-tab="decisions"]', "aria-current") == "page"
    assert page.get_attribute('.segment button[data-view="table"]', "aria-pressed") == "true"
    assert _row_ids(page) == ["D-1", "D-3"]
    assert page.inner_text("aside.panel .d-title") == "D-3の題"
    assert page.locator("aside.panel .md h4").count() == 1
    assert page.locator("aside.panel .mermaid svg").count() == 1
    # 同じ URL を開き直すと同じ画面と項目が開く
    page.reload()
    page.wait_for_selector("aside.panel.open .d-title")
    assert page.get_attribute('nav.tabbar a[data-tab="decisions"]', "aria-current") == "page"
    assert page.get_attribute('.segment button[data-view="table"]', "aria-pressed") == "true"
    assert page.inner_text("aside.panel .d-title") == "D-3の題"


def test_normal_when_no_hash(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """ハッシュが無いと概要を開く（正常系）。"""
    # 準備
    path = write_preview(make_item("D-1"))
    # 実行
    page = open_preview(path)
    # 検証
    assert page.get_attribute('nav.tabbar a[data-tab="overview"]', "aria-current") == "page"
    assert page.locator("aside.panel").count() == 0
    assert "#" not in page.url


def test_normal_when_filter_in_hash(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """ハッシュの f.{列} で絞った表を、条件のチップ付きで開く（正常系）。"""
    # 準備
    path = write_preview(
        make_item("D-1", status="未決定"),
        make_item("D-3", status="要見直し"),
        make_item("D-4", status="保留"),
    )
    # 実行
    page = open_preview(path, "#tab=decisions&view=table&f.status=要見直し|保留")
    # 検証
    chips = page.eval_on_selector_all(".chips .chip", "chips => chips.map(c => c.textContent)")
    assert chips == ["状態: 要見直し", "状態: 保留"]
    assert _row_ids(page) == ["D-3", "D-4"]
    # 開いた後は、ハッシュから f. の引数が消えている
    assert "f." not in page.evaluate("location.hash")
    # チップを解除すると、D-1 の行も出る
    page.click(".chips >> text=すべて解除")
    page.wait_for_function("document.querySelectorAll('table.grid tbody tr').length === 3")
    assert _row_ids(page) == ["D-1", "D-3", "D-4"]
    assert "f." not in page.evaluate("location.hash")


def test_normal_when_item_not_found(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """記録に無い ID を指すハッシュでは、画面だけを開く（正常系）。"""
    # 準備
    path = write_preview(make_item("D-1"))
    # 実行
    page = open_preview(path, "#tab=decisions&id=D-99")
    # 検証
    assert page.get_attribute('nav.tabbar a[data-tab="decisions"]', "aria-current") == "page"
    assert page.get_attribute('.segment button[data-view="map"]', "aria-pressed") == "true"
    assert page.locator("aside.panel").count() == 0
    assert "id=" not in page.evaluate("location.hash")


def test_normal_when_exported_offline(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    run_mindmap: RunMindmap,
    open_preview: OpenPreview,
    page: Any,
    tmp_path: Path,
) -> None:
    """描画のライブラリを中に持つ配る書き出しは、通信が無くても本文・図・マップを描く（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-3", status="要見直し", body="D-3.md"), bodies={"D-3.md": BODY_WITH_DIAGRAM}
    )
    out = tmp_path / "配る.html"
    result = run_mindmap("export", "--workspace", str(root), "--out", str(out))
    assert result.returncode == 0, result.stderr
    # `file:` 以外への要求を全て失敗させ、数える
    blocked: list[str] = []

    def _block(route: Any) -> None:
        """外への要求を数えて失敗させる。"""
        blocked.append(route.request.url)
        route.abort()

    page.route(_is_not_file_url, _block)
    # 実行
    open_preview(out, "#tab=decisions&id=D-3")
    page.wait_for_selector("aside.panel.open .mermaid svg", timeout=DIAGRAM_TIMEOUT_MS)
    # 検証
    assert blocked == []
    assert page.locator('[role="alert"]').count() == 0
    assert page.locator('#decision-map button[data-node="D-3"]').count() == 1
    assert page.inner_text("aside.panel .d-title") == "D-3の題"
    assert page.locator("aside.panel .md h4").count() == 1
    assert page.locator("aside.panel .mermaid svg").count() == 1


def test_error_when_library_unavailable(
    write_preview: WritePreview,
    open_preview: OpenPreview,
    make_item: MakeItem,
    page: Any,
) -> None:
    """描画のライブラリの配信元に届かないと、使う箇所に読み込めなかったライブラリの名前を出す（異常系）。"""
    # 準備
    path = write_preview(
        make_item("D-3", status="要見直し", body="D-3.md"), bodies={"D-3.md": BODY_WITH_DIAGRAM}
    )
    page.route(LIBRARY_HOST_PATTERN, lambda route: route.abort())
    # 実行
    open_preview(path, "#tab=decisions&id=D-3")
    page.wait_for_selector("aside.panel.open .md .lib-error")
    # 検証
    map_notice = page.inner_text("main .lib-error[role=alert]")
    assert "読み込めなかったライブラリ: elkjs" in map_notice
    assert "通信を確認して、ページを再読み込みしてください。" in map_notice
    body_notice = page.inner_text("aside.panel .md .lib-error[role=alert]")
    assert "読み込めなかったライブラリ" in body_notice
    for name in ("marked", "DOMPurify", "mermaid"):
        assert name in body_notice
    assert "本文の段落" in page.inner_text("aside.panel .md-raw")
    # 配置できない案内は、表への切り替えを促す
    assert "表示形式を「表」に切り替えると、検討事項を表示できます。" in page.inner_text("main")
    # 表示形式を表に切り替えると、D-3 の行がある
    page.click('.segment button[data-view="table"]')
    page.wait_for_selector("table.grid tbody tr")
    assert _row_ids(page) == ["D-3"]
