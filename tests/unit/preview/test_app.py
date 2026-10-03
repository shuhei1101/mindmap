"""app.ts（起動・端末の保存領域・埋め込みのデータの読み込み）の単体テスト。"""

from __future__ import annotations

from typing import Any

import pytest
from playwright.sync_api import Page

from .fixture_types import LoadPreviewScripts

# 既定の設定
DEFAULT_PREFS = {"theme": None, "columns": {}}

# `</script>` を JSON のエスケープ（バックスラッシュに続けて u003c・u003e）で持つ埋め込みの JSON
ESCAPED_JSON = '{"text": "\\u003c/script\\u003e"}'


def test_read_embedded_data(preview_page: Page, load_preview_scripts: LoadPreviewScripts) -> None:
    """要素の JSON を読む（正常系）。"""
    # 準備
    load_preview_scripts(include_app=True)
    html = f'<script type="application/json" id="mindmap-data">{ESCAPED_JSON}</script>'
    # 実行
    data = preview_page.evaluate(
        """(html) => {
            const doc = new DOMParser().parseFromString(html, "text/html");
            return MindmapPreview.readEmbeddedData(doc);
        }""",
        html,
    )
    # 検証
    assert data == {"text": "</script>"}


def test_read_embedded_data_when_missing(
    preview_page: Page, load_preview_scripts: LoadPreviewScripts
) -> None:
    """要素が無ければ送る（異常系）。"""
    # 準備
    load_preview_scripts(include_app=True)
    # 実行
    error = preview_page.evaluate(
        """() => {
            const doc = new DOMParser().parseFromString("<p></p>", "text/html");
            try {
                MindmapPreview.readEmbeddedData(doc);
            } catch (caught) {
                return {isError: caught instanceof Error, message: caught.message};
            }
            return null;
        }"""
    )
    # 検証
    assert error is not None
    assert error["isError"] is True
    assert "書き出し直してください" in error["message"]


@pytest.mark.parametrize(
    ("stored", "expected"),
    [
        pytest.param(
            '{"theme": "dark", "columns": {}}', {"theme": "dark", "columns": {}}, id="dark"
        ),
        pytest.param("{", DEFAULT_PREFS, id="broken_json"),
        pytest.param(None, DEFAULT_PREFS, id="storage_throws"),
    ],
)
def test_load_prefs(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    stored: str | None,
    expected: dict[str, Any],
) -> None:
    """残した設定を読み、読めなければ既定（正常系）。"""
    # 準備
    load_preview_scripts(include_app=True)
    # 実行
    prefs = preview_page.evaluate(
        """(stored) => {
            // stored が null のときは、getItem が例外を送る保存領域にする
            const storage = {
                getItem: (key) => {
                    if (stored === null) throw new Error("保存領域が使えません");
                    return key === "mindmap-preview" ? stored : null;
                },
            };
            return MindmapPreview.loadPrefs(storage);
        }""",
        stored,
    )
    # 検証
    assert prefs == expected


# 保存する設定
SAVED_PREFS = {"theme": "dark", "columns": {"decisions": {"hidden": ["tags"], "pinTo": "id"}}}


@pytest.mark.parametrize(
    ("setitem_throws", "expected_loaded"),
    [
        pytest.param(False, SAVED_PREFS, id="working_storage"),
        # 例外を送る保存領域では、読み戻した値は確かめない（例外を送らないことだけを確かめる）
        pytest.param(True, None, id="setitem_throws"),
    ],
)
def test_save_prefs(
    preview_page: Page,
    load_preview_scripts: LoadPreviewScripts,
    setitem_throws: bool,
    expected_loaded: dict[str, Any] | None,
) -> None:
    """残した設定を読める。保存領域が例外を送っても例外を送らない（正常系）。"""
    # 準備
    load_preview_scripts(include_app=True)
    # 実行（savePrefs が例外を送ると evaluate が失敗する）
    loaded = preview_page.evaluate(
        """({prefs, setitemThrows}) => {
            const values = new Map();
            const storage = {
                getItem: (key) => values.get(key) ?? null,
                setItem: (key, value) => {
                    if (setitemThrows) throw new Error("保存領域が使えません");
                    values.set(key, value);
                },
            };
            MindmapPreview.savePrefs({storage, prefs});
            return MindmapPreview.loadPrefs(storage);
        }""",
        {"prefs": SAVED_PREFS, "setitemThrows": setitem_throws},
    )
    # 検証
    assert expected_loaded is None or loaded == expected_loaded
