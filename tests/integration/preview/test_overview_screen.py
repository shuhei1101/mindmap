"""画面設計『概要』（タイルの項目 ID で要素を引く）の結合テスト。"""

from __future__ import annotations

from playwright.sync_api import Page
from preview_fixture_types import OpenPreview, WritePreview, WriteSamplePreview
from workspace_fixtures import MakeItem

# 概要のタイルの項目 ID
TILE_IDS = (
    "tile-next",
    "tile-goal",
    "tile-review",
    "tile-hold",
    "tile-running",
    "tile-progress",
)


def _chips(page: Page) -> list[str]:
    """表の上に並んでいる条件のチップの文字を返す。"""
    return page.eval_on_selector_all(".chips .chip", "chips => chips.map(c => c.textContent)")


def _row_ids(page: Page) -> list[str]:
    """表に並んでいる行の ID を上から返す。"""
    return page.eval_on_selector_all("table.grid tbody tr", "rows => rows.map(r => r.dataset.id)")


def test_tiles_are_laid_out(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """6 つのタイルが項目 ID で引け、概要の題名が h1 になる（正常系）。"""
    # 準備
    path = write_sample_preview()
    # 実行
    page = open_preview(path)
    # 検証
    for tile_id in TILE_IDS:
        assert page.locator(f"#{tile_id}").count() == 1
    assert page.inner_text("main h1") == "要件出しのスキル mindmap を設計する"


def test_next_tile(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """次に検討する項目を build が埋め込んだ順に並べ、押すと詳細パネルを開く（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path)
    # 実行
    ids = page.eval_on_selector_all("#tile-next button[data-id]", "b => b.map(x => x.dataset.id)")
    page.click('#tile-next button[data-id="D-2"]')
    # 検証
    assert ids == ["D-2", "D-5"]
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "D-2の題"


def test_next_tile_show_all(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """すべて表示で、検討事項の表を 未決定 × 着手できる = はい で絞って開く（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path)
    # 実行
    page.click("#tile-next .t-link")
    page.wait_for_selector("table.grid")
    # 検証
    assert _chips(page) == ["状態: 未決定", "着手できる: はい"]
    assert _row_ids(page) == ["D-2", "D-5"]


def test_next_tile_when_nothing_to_discuss(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """次に検討する項目が無いときは、その旨を出して「すべて表示」を置かない（正常系）。"""
    # 準備
    path = write_preview(make_item("D-1", status="決定済み"))
    # 実行
    page = open_preview(path)
    # 検証
    assert "次に検討する項目はありません" in page.inner_text("#tile-next")
    assert page.locator("#tile-next .t-link").count() == 0


def test_goal_tile(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """ゴールのフェーズまでの決定済みの数・フェーズごとの棒・納品物のチェックリストを出す（正常系）。"""
    # 準備
    path = write_sample_preview()
    # 実行
    page = open_preview(path)
    # 検証
    assert page.inner_text("#tile-goal .big").replace("\n", "").replace(" ", "") == "1/3"
    stages = page.eval_on_selector_all(
        "#tile-goal .stage-rows li", "rows => rows.map(r => r.textContent)"
    )
    assert stages == ["目的1/1", "要件0/2"]
    assert page.locator("#tile-goal .checklist li.done").count() == 1
    assert "1/1" in page.inner_text("#tile-goal .deliv-head")
    # 納品物を押すと、その資料の詳細パネルを開く
    page.click("#tile-goal .checklist button")
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "A-1の題\n納品物"


def test_small_tiles(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """要見直し・保留・進行中のタスクの件数と名前を出し、押すと詳細パネルを開く（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path)
    # 実行
    counts = {
        tile_id: page.inner_text(f"#{tile_id} .num")
        for tile_id in ("tile-review", "tile-hold", "tile-running")
    }
    page.click('#tile-hold button[data-id="D-4"]')
    # 検証
    assert counts == {"tile-review": "1", "tile-hold": "1", "tile-running": "1"}
    page.wait_for_selector("aside.panel.open")
    assert page.inner_text("aside.panel .d-title") == "D-4の題"


def test_small_tiles_show_all(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """要見直しのすべて表示で、検討事項の表を 状態 = 要見直し で絞って開く（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path)
    # 実行
    page.click("#tile-review .t-link")
    page.wait_for_selector("table.grid")
    # 検証
    assert _chips(page) == ["状態: 要見直し"]
    assert _row_ids(page) == ["D-3"]


def test_small_tiles_when_empty(
    write_preview: WritePreview, open_preview: OpenPreview, make_item: MakeItem
) -> None:
    """該当する項目が無いタイルは 0 件と「なし」を出す（正常系）。"""
    # 準備
    path = write_preview(make_item("D-1", status="決定済み"))
    # 実行
    page = open_preview(path)
    # 検証
    for tile_id in ("tile-review", "tile-hold", "tile-running"):
        assert page.inner_text(f"#{tile_id} .num") == "0"
        assert "なし" in page.inner_text(f"#{tile_id}")


def test_progress_tile(write_sample_preview: WriteSamplePreview, open_preview: OpenPreview) -> None:
    """カテゴリー別の進み具合をカテゴリー × フェーズで出し、セルとカテゴリー名で表を絞る（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path)
    # 実行・検証
    totals = page.eval_on_selector_all("#tile-progress td.tot", "cells => cells.map(c => c.textContent)")
    assert totals == ["1/2", "0/3"]
    # 項目の無いセルは押せない
    assert page.locator("#tile-progress td >> text=—").count() == 2
    # セルを押すと、そのカテゴリーとフェーズで絞った表を開く
    page.click('#tile-progress button.cell[aria-label^="画面 の 構成"]')
    page.wait_for_selector("table.grid")
    assert _chips(page) == ["カテゴリー: 画面", "フェーズ: 構成"]
    assert _row_ids(page) == ["D-4", "D-5"]


def test_progress_tile_category_link(
    write_sample_preview: WriteSamplePreview, open_preview: OpenPreview
) -> None:
    """行の見出しを押すと、カテゴリーだけで絞った表を開く（正常系）。"""
    # 準備
    path = write_sample_preview()
    page = open_preview(path)
    # 実行
    page.click('#tile-progress button.cat-link >> text=データ構造')
    page.wait_for_selector("table.grid")
    # 検証
    assert _chips(page) == ["カテゴリー: データ構造"]
    assert _row_ids(page) == ["D-1", "D-2"]
