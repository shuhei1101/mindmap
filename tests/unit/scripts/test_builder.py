"""builder.py（プレビューのデータの収集・埋め込み・書き出し）の単体テスト。"""

from __future__ import annotations

import http.server
import json
import re
import socket
import threading
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

import builder
import errors
import store
from errors import SchemaMismatchError, WriteFailedError
from export_helpers import (
    Script,
    dist_url,
    external_template,
    license_url,
    make_fetch,
    make_library,
    make_responses,
)
from fixture_types import FailingReplace, MakeItem, MakeWorkspace, SnapshotTree

# 埋め込み先の要素の開きタグ（DATA_ELEMENT から閉じタグを除いたもの）
DATA_ELEMENT_OPEN = builder.DATA_ELEMENT.removesuffix("</script>")

# 書き出した日時
BUILT_AT = "2026-10-02T08:00:00+00:00"


def _read_embedded(html: str) -> dict[str, Any]:
    """HTML の mindmap-data の要素の中身を JSON として読む。"""
    inner = html.split(DATA_ELEMENT_OPEN, 1)[1].split("</script>", 1)[0]
    return json.loads(inner)


def _write_preview_dir(preview_dir: Path, template: str) -> None:
    """雛形のフォルダに template.html と、STYLE_FILES・SCRIPT_FILES の名前のファイルを書く。"""
    preview_dir.mkdir(parents=True, exist_ok=True)
    (preview_dir / "template.html").write_text(template, encoding="utf-8")
    # 中身はファイル名のコメント（並びの順に差し込まれたかを見分けるため）
    for name in (*builder.STYLE_FILES, *builder.SCRIPT_FILES):
        path = preview_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"/* {name} */", encoding="utf-8")


@pytest.fixture
def preview_dir(tmp_path: Path) -> Path:
    """差し込み口と埋め込み先を持つ template.html と、空に近い CSS・JavaScript を置いた雛形のフォルダを返す。"""
    folder = tmp_path / "preview"
    _write_preview_dir(folder, f"{builder.STYLE_SLOT}{builder.DATA_ELEMENT}{builder.SCRIPT_SLOT}")
    return folder


def test_build_preview(
    make_workspace: MakeWorkspace, make_item: MakeItem, preview_dir: Path
) -> None:
    """データを埋め込んだ preview.html を書く（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"),
        make_item("A-1"),
        bodies={"A-1.md": "本文 </script>\n"},
    )
    workspace = store.load_workspace(root)
    # 実行
    path = builder.build_preview(workspace, built_at=BUILT_AT, preview_dir=preview_dir)
    # 検証
    assert path == root / "preview.html"
    data = _read_embedded(path.read_text(encoding="utf-8"))
    assert data["decisions"] == [make_item("D-1")]
    assert data["bodies"] == {"A-1.md": "本文 </script>\n"}
    assert data["built_at"] == BUILT_AT


def test_build_preview_when_schema_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
    preview_dir: Path,
) -> None:
    """問題があれば前の preview.html を残す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", status="完了"))
    (root / "preview.html").write_text("前の preview\n", encoding="utf-8")
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    # 実行・検証
    with pytest.raises(SchemaMismatchError):
        builder.build_preview(workspace, built_at=BUILT_AT, preview_dir=preview_dir)
    assert snapshot_tree(root) == before


def test_build_preview_when_replace_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
    failing_replace: FailingReplace,
    preview_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """置き換えに失敗したら前の preview.html を残す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    (root / "preview.html").write_text("前の preview\n", encoding="utf-8")
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    # builder モジュールの参照を、preview.html への置き換えが失敗するものに差し替える
    monkeypatch.setattr(builder.os, "replace", failing_replace("preview.html"))
    # 実行・検証
    with pytest.raises(WriteFailedError):
        builder.build_preview(workspace, built_at=BUILT_AT, preview_dir=preview_dir)
    assert snapshot_tree(root) == before
    assert list(root.rglob("*.tmp")) == []


def test_collect_preview_data(make_workspace: MakeWorkspace, make_item: MakeItem) -> None:
    """種類ごとのキーと、指された本文だけを集める（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("A-1"),
        make_item("R-1", body="R-1.md"),
        bodies={"A-1.md": "資料の本文\n", "X-1.md": "どこからも指されない本文\n"},
    )
    workspace = store.load_workspace(root)
    # 実行
    data = builder.collect_preview_data(workspace, built_at=BUILT_AT)
    # 検証
    assert set(data) == {
        "settings",
        "decisions",
        "tasks",
        "research",
        "docs",
        "terms",
        "notes",
        "logs",
        "bodies",
        "derived",
        "built_at",
    }
    assert data["bodies"] == {"A-1.md": "資料の本文\n"}


def test_escape_for_script() -> None:
    """置き換えた文字列は </script> を含まず、JSON として読むと元に戻る（正常系）。"""
    # 準備
    original = {"a": "</script>&<b>"}
    json_text = json.dumps(original, ensure_ascii=False)
    # 実行
    escaped = builder.escape_for_script(json_text)
    # 検証
    assert "<" not in escaped
    assert ">" not in escaped
    assert "&" not in escaped
    assert json.loads(escaped) == original


def test_embed_data() -> None:
    """要素の中身に JSON を入れる（正常系）。"""
    # 準備
    template = "<p></p>" + builder.DATA_ELEMENT
    data = {"a": "</script>"}
    # 実行
    html = builder.embed_data(template, data)
    # 検証
    assert html.count("</script>") == 1
    assert _read_embedded(html) == data


@pytest.mark.parametrize(
    ("template", "count_text"),
    [
        pytest.param("<p></p>", "0 個", id="none"),
        pytest.param(builder.DATA_ELEMENT * 2, "2 個", id="two"),
    ],
)
def test_embed_data_when_element_count_wrong(template: str, count_text: str) -> None:
    """埋め込み先が 1 つでない雛形は受け付けない（異常系）。"""
    # 実行・検証
    with pytest.raises(ValueError, match=count_text):
        builder.embed_data(template, {"a": 1})


def test_assemble_template(preview_dir: Path) -> None:
    """CSS と JavaScript を並びの順に差し込む（正常系）。"""
    # 実行
    html = builder.assemble_template(preview_dir=preview_dir)
    # 検証
    style = html.split('<style id="mindmap-style">', 1)[1].split("</style>", 1)[0]
    script = html.split('<script id="mindmap-app">', 1)[1].split("</script>", 1)[0]
    assert style == "\n".join(f"/* {name} */" for name in builder.STYLE_FILES)
    assert script == "\n".join(f"/* {name} */" for name in builder.SCRIPT_FILES)
    # 埋め込み先は空のまま
    assert builder.DATA_ELEMENT in html


@pytest.mark.parametrize(
    ("kind", "closing_tag"),
    [
        pytest.param("style", "</STYLE>", id="style"),
        pytest.param("script", "</script>", id="script"),
    ],
)
def test_assemble_template_when_closing_tag(preview_dir: Path, kind: str, closing_tag: str) -> None:
    """閉じタグを含むファイルは差し込まない（異常系）。"""
    # 準備
    file_name = builder.STYLE_FILES[0] if kind == "style" else builder.SCRIPT_FILES[0]
    (preview_dir / file_name).write_text(f"x {closing_tag} y", encoding="utf-8")
    # 実行・検証
    with pytest.raises(ValueError, match=file_name):
        builder.assemble_template(preview_dir=preview_dir)


@pytest.mark.parametrize(
    ("slot_kind", "count_text"),
    [
        pytest.param("style_slot_none", "0 個", id="style_slot_none"),
        pytest.param("script_slot_two", "2 個", id="script_slot_two"),
    ],
)
def test_assemble_template_when_slot_count_wrong(
    tmp_path: Path, slot_kind: str, count_text: str
) -> None:
    """差し込み口が 1 つでない雛形は受け付けない（異常系）。"""
    # 準備
    if slot_kind == "style_slot_none":
        template = f"{builder.DATA_ELEMENT}{builder.SCRIPT_SLOT}"
    else:
        template = f"{builder.STYLE_SLOT}{builder.DATA_ELEMENT}{builder.SCRIPT_SLOT * 2}"
    folder = tmp_path / "preview"
    _write_preview_dir(folder, template)
    # 実行・検証
    with pytest.raises(ValueError, match=count_text):
        builder.assemble_template(preview_dir=folder)


def test_derive_preview_values(
    make_workspace: MakeWorkspace, make_item: MakeItem, valid_settings: dict[str, Any]
) -> None:
    """コマンドと同じ答えをまとめる（正常系）。"""
    # 準備
    settings = {
        **valid_settings,
        "phases": ["目的", "要件"],
        "categories": [
            {"name": "A", "target": "mindmap", "summary": "カテゴリー A"},
            {"name": "B", "target": "mindmap", "summary": "カテゴリー B"},
        ],
        "goal": {"phase": "要件", "summary": "要件が決まる", "deliverables": []},
    }
    root = make_workspace(
        make_item("D-1", category="A", phase="目的", status="決定済み"),
        make_item("D-2", category="A", phase="要件", status="未決定", depends_on=["D-1"]),
        make_item("D-3", category="B", phase="要件", status="対象外"),
        settings=settings,
    )
    workspace = store.load_workspace(root)
    # 実行
    derived = builder.derive_preview_values(workspace)
    # 検証
    assert [candidate["id"] for candidate in derived["next"]] == ["D-2"]
    assert derived["goal"]["phase_progress"] == [
        {"phase": "目的", "settled": 1, "total": 1},
        {"phase": "要件", "settled": 1, "total": 2},
    ]
    assert derived["progress"] == [
        {
            "category": "A",
            "cells": [
                {"phase": "目的", "settled": 1, "total": 1},
                {"phase": "要件", "settled": 0, "total": 1},
            ],
            "settled": 1,
            "total": 2,
        },
        {
            "category": "B",
            "cells": [
                {"phase": "目的", "settled": 0, "total": 0},
                {"phase": "要件", "settled": 1, "total": 1},
            ],
            "settled": 1,
            "total": 1,
        },
    ]


# 配る書き出しのテストが雛形に置く外の読み込み（実物の VENDOR_LIBRARIES にあるパッケージ）
MARKED_SCRIPTS: list[Script] = [("marked", b"/* marked */")]

# 手元の HTTP サーバーが 200 で返す本文
SERVED_BODY = b"abc"


class _Handler(http.server.BaseHTTPRequestHandler):
    """/a.js は 200 で本文を、/no-content は 204 を返し、それ以外は 404 を返す手元の HTTP サーバーの処理。"""

    def do_GET(self) -> None:
        """GET を受けて、パスで 200 か 404 かを決める。"""
        # /a.js だけが取れる
        if self.path == "/a.js":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(SERVED_BODY)
        elif self.path == "/no-content":
            # 200 以外の成功（本文が無い）
            self.send_response(204)
            self.end_headers()
        else:
            # それ以外は 404
            self.send_error(404)

    def log_message(self, format: str, *args: Any) -> None:
        """標準エラーへのアクセスログを出さない。"""


def _failing_fetch(url: str) -> bytes:
    """どの URL も取れない fetch の代わり。"""
    raise errors.DownloadFailedError(f"取れませんでした: {url}")


def _assert_in_order(text: str, parts: list[str]) -> None:
    """parts の各文字列が、text の中にこの順で現れることを確かめる。"""
    positions = [text.index(part) for part in parts]
    assert positions == sorted(positions)


def _fill_marks(template: str) -> str:
    """`<<START>>`・`<<END>>` を、外の読み込みの始まりと終わりの印に置き換える。"""
    return template.replace("<<START>>", builder.EXTERNAL_START).replace(
        "<<END>>", builder.EXTERNAL_END
    )


@pytest.fixture
def marked_preview_dir(tmp_path: Path) -> Path:
    """外の読み込みの印の間に marked の <script src integrity> を 1 つ持つ雛形のフォルダを返す。"""
    folder = tmp_path / "preview"
    _write_preview_dir(folder, external_template(MARKED_SCRIPTS))
    return folder


@pytest.fixture
def local_server(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    """127.0.0.1 の空きポートで HTTP サーバーを立て、`http://127.0.0.1:{ポート}` を返す。"""
    # 環境のプロキシを通さずに、手元のサーバーへ届かせる
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join()


@pytest.fixture
def closed_url(monkeypatch: pytest.MonkeyPatch) -> str:
    """誰も待ち受けていないポートの URL を返す。"""
    # 環境のプロキシを通さずに、手元のポートへ届かせる
    monkeypatch.setenv("no_proxy", "127.0.0.1")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    return f"http://127.0.0.1:{port}/a.js"


def test_replace_file(tmp_path: Path) -> None:
    """中身を書いて置き換える（正常系）。"""
    # 準備
    path = tmp_path / "a.html"
    path.write_text("古い", encoding="utf-8")
    # 実行
    builder.replace_file(path, "新しい")
    # 検証
    assert path.read_text(encoding="utf-8") == "新しい"
    assert list(tmp_path.glob("*.tmp")) == []


def test_replace_file_when_parent_missing(tmp_path: Path) -> None:
    """親のフォルダが無ければフォルダを作らずに失敗する（異常系）。"""
    # 準備
    path = tmp_path / "無い" / "a.html"
    # 実行・検証
    with pytest.raises(WriteFailedError, match=r"a\.html"):
        builder.replace_file(path, "新しい")
    assert not (tmp_path / "無い").exists()


def test_export_preview(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    snapshot_tree: SnapshotTree,
    marked_preview_dir: Path,
    tmp_path: Path,
) -> None:
    """記録と取ったライブラリとライセンスの表示を持つ HTML を out に書き、preview.html は触らない（正常系）。"""
    # 準備
    root = make_workspace(
        make_item("D-1"),
        make_item("A-1"),
        bodies={"A-1.md": "本文 </script>\n"},
    )
    (root / "preview.html").write_text("前の preview\n", encoding="utf-8")
    workspace = store.load_workspace(root)
    before = snapshot_tree(root)
    out = tmp_path / "配る.html"
    fetch, _calls = make_fetch(make_responses(MARKED_SCRIPTS))
    # 実行
    path = builder.export_preview(
        workspace, out=out, built_at=BUILT_AT, preview_dir=marked_preview_dir, fetch=fetch
    )
    # 検証
    assert path == out
    html = out.read_text(encoding="utf-8")
    data = _read_embedded(html)
    assert data["decisions"] == [make_item("D-1")]
    assert data["bodies"] == {"A-1.md": "本文 </script>\n"}
    assert "src=" not in html
    assert "href=" not in html
    assert builder.LICENSES_OPEN in html
    assert snapshot_tree(root) == before


def test_export_preview_when_schema_mismatch(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    marked_preview_dir: Path,
    tmp_path: Path,
) -> None:
    """問題があれば取らずに前の out を残す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1", status="完了"))
    workspace = store.load_workspace(root)
    out = tmp_path / "配る.html"
    out.write_text("前の配る\n", encoding="utf-8")
    fetch, calls = make_fetch(make_responses(MARKED_SCRIPTS))
    # 実行・検証
    with pytest.raises(SchemaMismatchError):
        builder.export_preview(
            workspace, out=out, built_at=BUILT_AT, preview_dir=marked_preview_dir, fetch=fetch
        )
    assert out.read_text(encoding="utf-8") == "前の配る\n"
    assert calls == []


def test_export_preview_when_download_fails(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    marked_preview_dir: Path,
    tmp_path: Path,
) -> None:
    """取れなければ前の out を残す（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    workspace = store.load_workspace(root)
    out = tmp_path / "配る.html"
    out.write_text("前の配る\n", encoding="utf-8")
    # 実行・検証
    with pytest.raises(errors.DownloadFailedError):
        builder.export_preview(
            workspace,
            out=out,
            built_at=BUILT_AT,
            preview_dir=marked_preview_dir,
            fetch=_failing_fetch,
        )
    assert out.read_text(encoding="utf-8") == "前の配る\n"


def test_export_preview_when_out_dir_missing(
    make_workspace: MakeWorkspace,
    make_item: MakeItem,
    marked_preview_dir: Path,
    tmp_path: Path,
) -> None:
    """out の親のフォルダが無ければ書かない（異常系）。"""
    # 準備
    root = make_workspace(make_item("D-1"))
    workspace = store.load_workspace(root)
    out = tmp_path / "無い" / "配る.html"
    fetch, _calls = make_fetch(make_responses(MARKED_SCRIPTS))
    # 実行・検証
    with pytest.raises(WriteFailedError):
        builder.export_preview(
            workspace, out=out, built_at=BUILT_AT, preview_dir=marked_preview_dir, fetch=fetch
        )
    assert not (tmp_path / "無い").exists()


def test_validate_export_out(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """相対パスを起動した場所から読んで絶対パスにする（正常系）。"""
    # 準備
    monkeypatch.chdir(tmp_path)
    # 実行
    result = builder.validate_export_out(Path("配る.HTML"), root=tmp_path / "ws")
    # 検証
    assert result == tmp_path / "配る.HTML"


@pytest.mark.parametrize(
    ("relative_out", "message"),
    [
        pytest.param("配る.txt", "は .html のファイルを指してください", id="not_html"),
        pytest.param("ws/sub/../preview.html", "preview.html は指せません", id="preview_html"),
    ],
)
def test_validate_export_out_when_invalid(tmp_path: Path, relative_out: str, message: str) -> None:
    """html でないか preview.html を指す out を弾く（異常系）。"""
    # 実行・検証
    with pytest.raises(errors.OutPathError, match=message):
        builder.validate_export_out(tmp_path / relative_out, root=tmp_path / "ws")


def test_list_external_scripts() -> None:
    """印の間の script を並びの順に読み、印の外と link は読まない（正常系）。"""
    # 準備
    template = _fill_marks(
        '<script src="a.js"></script>'
        "<<START>>"
        '<script src="https://cdn.jsdelivr.net/npm/x@1.0.0/x.js" integrity="sha384-AAA"'
        ' crossorigin="anonymous" defer></script>'
        '<link rel="stylesheet" href="https://fonts.example/css">'
        '<script src="https://cdn.jsdelivr.net/npm/y@2.1.0/dist/y.min.js" integrity="sha384-BBB">'
        "</script>"
        "<<END>>"
    )
    # 実行
    scripts = builder.list_external_scripts(template)
    # 検証
    assert scripts == [
        builder.ExternalScript(
            url="https://cdn.jsdelivr.net/npm/x@1.0.0/x.js",
            integrity="sha384-AAA",
            package="x",
            version="1.0.0",
        ),
        builder.ExternalScript(
            url="https://cdn.jsdelivr.net/npm/y@2.1.0/dist/y.min.js",
            integrity="sha384-BBB",
            package="y",
            version="2.1.0",
        ),
    ]


@pytest.mark.parametrize(
    "template",
    [
        pytest.param(
            '<script src="https://cdn.jsdelivr.net/npm/x@1.0.0/x.js" integrity="sha384-AAA">'
            "</script><<END>>",
            id="start_none",
        ),
        pytest.param(
            "<<START>>"
            '<script src="https://cdn.jsdelivr.net/npm/x@1.0.0/x.js" integrity="sha384-AAA">'
            "</script><<END>><<END>>",
            id="end_two",
        ),
        pytest.param(
            "<<END>><<START>>"
            '<script src="https://cdn.jsdelivr.net/npm/x@1.0.0/x.js" integrity="sha384-AAA">'
            "</script>",
            id="end_first",
        ),
        pytest.param(
            '<<START>><script src="https://cdn.jsdelivr.net/npm/x@1.0.0/x.js"></script><<END>>',
            id="integrity_missing",
        ),
        pytest.param(
            '<<START>><script src="https://cdn.jsdelivr.net/npm/x/x.js" integrity="sha384-AAA">'
            "</script><<END>>",
            id="version_missing",
        ),
    ],
)
def test_list_external_scripts_when_invalid(template: str) -> None:
    """印や script の形が違う雛形は受け付けない（異常系）。"""
    # 実行・検証
    with pytest.raises(ValueError):  # noqa: PT011 メッセージは印の欠け・script の形の違いで分かれる
        builder.list_external_scripts(_fill_marks(template))


def test_template_matches_vendor_libraries() -> None:
    """本物の雛形の外の読み込みと VENDOR_LIBRARIES が 1 対 1 で結べる（正常系）。"""
    # 準備
    template = (builder.PREVIEW_DIR / "template.html").read_text(encoding="utf-8")
    # 実行
    scripts = builder.list_external_scripts(template)
    # 検証
    assert [script.package for script in scripts] == [
        library.package for library in builder.VENDOR_LIBRARIES
    ]
    bundled_files = [
        library.bundled_license_file
        for library in builder.VENDOR_LIBRARIES
        if library.bundled_license_file is not None
    ]
    assert [name for name in bundled_files if not (builder.PREVIEW_DIR / name).is_file()] == []


def test_fetch_url(local_server: str) -> None:
    """本文を返す（正常系）。"""
    # 実行
    body = builder.fetch_url(f"{local_server}/a.js")
    # 検証
    assert body == SERVED_BODY


@pytest.mark.parametrize(
    "make_url",
    [
        pytest.param(lambda base, closed: closed, id="closed_port"),
        pytest.param(lambda base, closed: f"{base}/missing", id="not_found"),
        pytest.param(lambda base, closed: f"{base}/no-content", id="no_content"),
    ],
)
def test_fetch_url_when_unreachable(
    local_server: str, closed_url: str, make_url: Callable[[str, str], str]
) -> None:
    """届かないか 200 以外なら DownloadFailedError にする（異常系）。"""
    # 準備
    url = make_url(local_server, closed_url)
    # 実行・検証
    with pytest.raises(errors.DownloadFailedError, match=re.escape(url)):
        builder.fetch_url(url)


def test_assemble_standalone_template(tmp_path: Path) -> None:
    """外の読み込みを取った配布ファイルとライセンスの表示に置き換える（正常系）。"""
    # 準備
    scripts: list[Script] = [("a", b"/* a */"), ("b", b"/* b */")]
    folder = tmp_path / "preview"
    _write_preview_dir(folder, external_template(scripts))
    fetch, calls = make_fetch(make_responses(scripts))
    libraries = (make_library("a"), make_library("b"))
    # 実行
    html = builder.assemble_standalone_template(
        preview_dir=folder, libraries=libraries, fetch=fetch
    )
    # 検証
    assert "https://" not in html
    assert builder.EXTERNAL_START not in html
    assert builder.EXTERNAL_END not in html
    _assert_in_order(html, ["/* a */", "/* b */", '<script id="mindmap-app">'])
    licenses = html.split(builder.LICENSES_OPEN, 1)[1].split("</script>", 1)[0]
    assert "本文 a" in licenses
    assert "本文 b" in licenses
    assert sorted(calls) == sorted(
        [dist_url("a"), dist_url("b"), license_url("a"), license_url("b")]
    )


def test_assemble_standalone_template_when_integrity_mismatch(tmp_path: Path) -> None:
    """integrity と合わない配布ファイルは差し込まない（異常系）。"""
    # 準備
    folder = tmp_path / "preview"
    _write_preview_dir(folder, external_template([("a", b"/* a */")]))
    # 雛形の integrity と違う中身を返す
    fetch, _calls = make_fetch(make_responses([("a", b"/* x */")]))
    # 実行・検証
    with pytest.raises(errors.DownloadFailedError, match=re.escape(dist_url("a"))):
        builder.assemble_standalone_template(
            preview_dir=folder, libraries=(make_library("a"),), fetch=fetch
        )


@pytest.mark.parametrize(
    ("dist_text", "license_text", "bundled_text", "match"),
    [
        pytest.param(
            "</SCRIPT>", "本文 a", "束ねた本文", re.escape(dist_url("a")), id="dist_closing"
        ),
        pytest.param(
            "x <!--<script y", "本文 a", "束ねた本文", re.escape(dist_url("a")), id="dist_opening"
        ),
        pytest.param(
            "/* a */", "本文 </script>", "束ねた本文", re.escape(license_url("a")), id="license"
        ),
        pytest.param("/* a */", "本文 a", "束ねた <Script", "bundled.txt", id="bundled"),
    ],
)
def test_assemble_standalone_template_when_tag_inside(
    tmp_path: Path, dist_text: str, license_text: str, bundled_text: str, match: str
) -> None:
    """閉じタグか開きタグを含む中身は差し込まない（異常系）。"""
    # 準備
    scripts: list[Script] = [("a", dist_text.encode("utf-8"))]
    folder = tmp_path / "preview"
    _write_preview_dir(folder, external_template(scripts))
    (folder / "licenses").mkdir()
    (folder / "licenses" / "bundled.txt").write_text(bundled_text, encoding="utf-8")
    fetch, _calls = make_fetch(make_responses(scripts, {"a": license_text}))
    libraries = (make_library("a", bundled_license_file="licenses/bundled.txt"),)
    # 実行・検証
    with pytest.raises(ValueError, match=match):
        builder.assemble_standalone_template(preview_dir=folder, libraries=libraries, fetch=fetch)


def test_assemble_standalone_template_when_library_unknown(tmp_path: Path) -> None:
    """VENDOR_LIBRARIES に無いパッケージの外の読み込みは受け付けない（異常系）。"""
    # 準備
    scripts: list[Script] = [("c", b"/* c */")]
    folder = tmp_path / "preview"
    _write_preview_dir(folder, external_template(scripts))
    fetch, calls = make_fetch(make_responses(scripts))
    # 実行・検証
    with pytest.raises(ValueError, match="ライセンスの表示が無い外の読み込み: c"):
        builder.assemble_standalone_template(
            preview_dir=folder, libraries=(make_library("a"),), fetch=fetch
        )
    assert calls == []


def test_format_licenses() -> None:
    """ライブラリごとに名前・版・著作権・ライセンス・入手先・本文を並べる（正常系）。"""
    # 準備
    first = builder.LicenseBlock(
        library=make_library(
            "a",
            name="A",
            notice="(c) A",
            license="MIT",
            repository="https://example.com/a",
            tag="v{version}",
        ),
        version="1.2.3",
        license_text="本文 A",
        bundled_text=None,
    )
    second = builder.LicenseBlock(
        library=make_library(
            "b",
            name="B",
            notice="(c) B",
            license="EPL-2.0",
            repository="https://example.com/b",
            tag="{version}",
        ),
        version="4.5.6",
        license_text="本文 B",
        bundled_text="束ねた本文",
    )
    # 実行
    text = builder.format_licenses([first, second])
    # 検証
    _assert_in_order(
        text,
        [
            "A 1.2.3",
            "(c) A",
            "License: MIT",
            "Source: https://example.com/a/tree/v1.2.3",
            "本文 A",
            "\n\nB 4.5.6",
            "(c) B",
            "License: EPL-2.0",
            "Source: https://example.com/b/tree/4.5.6",
            "本文 B",
            "B が中に持つライブラリ",
            "束ねた本文",
        ],
    )
    assert "A が中に持つライブラリ" not in text
