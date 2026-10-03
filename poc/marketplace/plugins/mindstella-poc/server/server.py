"""PoC: MCP のツールとプレビューの配信を 1 つのプロセスで持つサーバー。"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import yaml
from mcp.server.mcpserver import MCPServer

# 書き換えを見る間隔（秒）。反映の 1 秒の内訳のうち検知に充てる分
POLL_INTERVAL_SEC = 0.25
# SSE の接続を保つために空の行を送る間隔（秒）
KEEPALIVE_SEC = 15.0
ITEMS_FILE = "items.yaml"
SUBMISSIONS_FILE = "submissions.yaml"
INDEX_HTML = Path(__file__).resolve().parent / "index.html"


def get_workspace() -> Path:
    """起動スクリプトが環境変数で渡したワークスペースを返す。"""
    raw = os.environ.get("MINDSTELLA_WORKSPACE")
    if raw is None:
        raise RuntimeError("環境変数 MINDSTELLA_WORKSPACE がありません")
    return Path(raw).resolve()


def read_list(path: Path) -> list[dict[str, Any]]:
    """YAML の一覧を読む。ファイルが無ければ空の一覧。"""
    if not path.exists():
        return []
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded or []


def write_list(path: Path, rows: list[dict[str, Any]]) -> None:
    """一時ファイルに書いてから置き換え、読み手に書きかけを見せない。"""
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(yaml.safe_dump(rows, allow_unicode=True, sort_keys=False), encoding="utf-8")
    os.replace(tmp, path)


def signature(workspace: Path) -> str:
    """ワークスペースの YAML の mtime と大きさから、書き換えの印を作る。"""
    parts = []
    for name in (ITEMS_FILE, SUBMISSIONS_FILE):
        path = workspace / name
        if path.exists():
            stat = path.stat()
            parts.append(f"{name}:{stat.st_mtime_ns}:{stat.st_size}")
    return "|".join(parts)


def now_iso() -> str:
    """保存に使う UTC の時刻。"""
    return datetime.now(UTC).isoformat()


def make_handler(workspace: Path) -> type[BaseHTTPRequestHandler]:
    """ワークスペースを配る HTTP のハンドラーを作る。"""

    class Handler(BaseHTTPRequestHandler):
        """プレビュー・記録・書き換えの知らせ・送信を返す。"""

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            """標準出力は MCP が使うため、記録は標準エラーへ出す。"""
            sys.stderr.write(f"[http] {format % args}\n")

        def _send_json(self, body: object, status: HTTPStatus = HTTPStatus.OK) -> None:
            """JSON を返す。"""
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            """画面・記録・書き換えの知らせを返す。"""
            # 画面: プレビューの HTML
            if self.path == "/":
                data = INDEX_HTML.read_bytes()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            # 記録: YAML をそのまま読んで返す
            elif self.path == "/data":
                self._send_json(
                    {
                        "workspace": str(workspace),
                        "items": read_list(workspace / ITEMS_FILE),
                        "submissions": read_list(workspace / SUBMISSIONS_FILE),
                    }
                )
            # 書き換えの知らせ: mtime を見て、変わったら SSE で送る
            elif self.path == "/events":
                self._stream_events()
            else:
                self.send_error(HTTPStatus.NOT_FOUND)

        def _stream_events(self) -> None:
            """接続が切れるまで、書き換えの印が変わるたびに知らせる。"""
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            last = signature(workspace)
            last_sent = time.monotonic()
            try:
                while True:
                    time.sleep(POLL_INTERVAL_SEC)
                    current = signature(workspace)
                    # 書き換わった: 知らせる
                    if current != last:
                        last = current
                        self.wfile.write(f"event: changed\ndata: {current}\n\n".encode())
                        self.wfile.flush()
                        last_sent = time.monotonic()
                    # 長く送っていない: 接続を保つための空の行を送る
                    elif time.monotonic() - last_sent > KEEPALIVE_SEC:
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
                        last_sent = time.monotonic()
            except (BrokenPipeError, ConnectionResetError):
                return

        def do_POST(self) -> None:
            """画面からの回答・意見の送信を受けて、ワークスペースに残す。"""
            if self.path != "/submit":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            path = workspace / SUBMISSIONS_FILE
            rows = read_list(path)
            rows.append(
                {
                    "target": str(payload["target"]),
                    "body": str(payload["body"]),
                    "sent_at": now_iso(),
                    "taken": False,
                }
            )
            write_list(path, rows)
            self._send_json({"ok": True}, HTTPStatus.CREATED)

    return Handler


def start_preview(workspace: Path) -> str:
    """空きポートで配信を立て、URL を返す。"""
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(workspace))
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    host, port = httpd.server_address[:2]
    return f"http://{host}:{port}/"


WORKSPACE = get_workspace()
PREVIEW_URL = start_preview(WORKSPACE)
server = MCPServer("mindstella")


@server.tool()
def add_item(title: str) -> dict[str, str]:
    """ワークスペースに項目を 1 件足す。"""
    path = WORKSPACE / ITEMS_FILE
    rows = read_list(path)
    item = {"id": f"I{len(rows) + 1}", "title": title, "created": now_iso()}
    rows.append(item)
    write_list(path, rows)
    return item


@server.tool()
def preview_url() -> str:
    """このプロセスが配るプレビューの URL を返す。"""
    return PREVIEW_URL


@server.tool()
def take_submissions() -> list[dict[str, Any]]:
    """取り込んでいない送信を返し、取り込み済みにする。"""
    path = WORKSPACE / SUBMISSIONS_FILE
    rows = read_list(path)
    pending = [row for row in rows if not row["taken"]]
    for row in pending:
        row["taken"] = True
    write_list(path, rows)
    return pending


if __name__ == "__main__":
    sys.stderr.write(f"[mindstella] preview: {PREVIEW_URL}\n")
    server.run("stdio")
