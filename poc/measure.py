"""PoC: 書き換えの画面への反映・送信・待ち受けの重なり・使うメモリを測る。"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from playwright.async_api import Page, async_playwright

SERVER = Path(__file__).resolve().parent / "marketplace/plugins/mindstella-poc/server/server.py"
# 1 つの条件で測る回数
TRIALS = 10
# 反映を待つ上限（秒）。成功条件の 1 秒より長く待ち、超えた分も実測として残す
WAIT_LIMIT_SEC = 5.0
# 反映が届かないことを確かめるときに待つ時間（秒）
QUIET_SEC = 1.5


@dataclass(kw_only=True)
class Server:
    """MCP のクライアントでつないだサーバー 1 つ。"""

    name: str
    session: ClientSession
    stop: asyncio.Event
    task: asyncio.Task[None]
    url: str
    pid: int

    async def close(self) -> None:
        """接続を閉じ、サーバーのプロセスを終わらせる。"""
        self.stop.set()
        await self.task


async def call(server: Server, tool: str, args: dict[str, Any] | None = None) -> Any:
    """ツールを呼び、構造化された結果か本文の JSON を返す。"""
    result = await server.session.call_tool(tool, args or {})
    if result.structured_content is not None:
        return result.structured_content.get("result", result.structured_content)
    text = result.content[0].text
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def find_server_pid(workspace: Path, known: set[int]) -> int:
    """起動したサーバーのプロセスを /proc から探す。"""
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit() or int(proc.name) in known:
            continue
        try:
            cmdline = (proc / "cmdline").read_bytes().split(b"\0")
            environ = (proc / "environ").read_bytes().split(b"\0")
        except (PermissionError, FileNotFoundError, ProcessLookupError):
            continue
        if str(SERVER).encode() in cmdline and f"MINDSTELLA_WORKSPACE={workspace}".encode() in environ:
            return int(proc.name)
    raise RuntimeError(f"サーバーのプロセスが見つかりません: {workspace}")


def rss_mb(pid: int) -> float:
    """プロセスの常駐メモリ（MB）。"""
    for line in Path(f"/proc/{pid}/status").read_text().splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1]) / 1024
    raise RuntimeError(f"VmRSS がありません: {pid}")


async def start(name: str, workspace: Path, known: set[int]) -> Server:
    """サーバーを立て、プレビューの URL を受け取る。接続は専用のタスクが閉じるまで持つ。"""
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER)],
        env={**os.environ, "MINDSTELLA_WORKSPACE": str(workspace)},
    )
    ready: asyncio.Future[ClientSession] = asyncio.get_running_loop().create_future()
    stop = asyncio.Event()

    async def hold() -> None:
        """接続を開き、閉じる合図まで待つ。"""
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            ready.set_result(session)
            await stop.wait()

    task = asyncio.create_task(hold())
    session = await ready
    server = Server(name=name, session=session, stop=stop, task=task, url="", pid=0)
    server.url = await call(server, "preview_url")
    server.pid = find_server_pid(workspace, known)
    known.add(server.pid)
    return server


async def wait_render(page: Page, title: str, since: int) -> float | None:
    """題名を含む描き直しが来るまで待ち、見つけた時刻（time.monotonic）を返す。

    画面の時計と計測の時計がずれないよう、計測の側の単調な時計だけで測る。
    見つけるまでの問い合わせの間隔の分だけ、実際より長めに出る。
    """
    deadline = time.monotonic() + WAIT_LIMIT_SEC
    while time.monotonic() < deadline:
        renders = await page.evaluate("window.__renders")
        for render in renders[since:]:
            if title in render["titles"]:
                return time.monotonic()
        await asyncio.sleep(0.005)
    return None


async def measure_reflect(writer: Server, pages: dict[str, Page], label: str) -> dict[str, list[int]]:
    """writer のツールで書いてから、各画面が描き直すまでのミリ秒を測る。"""
    results: dict[str, list[int]] = {name: [] for name in pages}
    for trial in range(TRIALS):
        title = f"{label}-{trial}"
        counts = {name: len(await page.evaluate("window.__renders")) for name, page in pages.items()}
        written_at = time.monotonic()
        await call(writer, "add_item", {"title": title})
        for name, page in pages.items():
            rendered_at = await wait_render(page, title, counts[name])
            # 届かなかった: 上限の時間を超えた印として -1 を残す
            results[name].append(-1 if rendered_at is None else round((rendered_at - written_at) * 1000))
    return results


async def assert_quiet(page: Page, writer: Server, title: str) -> bool:
    """別のワークスペースへの書き換えで、この画面が描き直さないかを確かめる。"""
    before = len(await page.evaluate("window.__renders"))
    await call(writer, "add_item", {"title": title})
    await asyncio.sleep(QUIET_SEC)
    return len(await page.evaluate("window.__renders")) == before


async def main(base: Path) -> dict[str, Any]:
    """成功条件ごとに測って結果を返す。"""
    ws1 = base / "ws1"
    ws2 = base / "ws2"
    for ws in (ws1, ws2):
        ws.mkdir(parents=True, exist_ok=True)
        for name in ("items.yaml", "submissions.yaml"):
            (ws / name).unlink(missing_ok=True)
    known: set[int] = set()
    report: dict[str, Any] = {}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        # 同じワークスペースを開く 2 つのサーバー（A・B）と、別のワークスペースのサーバー（C）
        a = await start("A", ws1, known)
        b = await start("B", ws1, known)
        c = await start("C", ws2, known)
        report["urls"] = {"A": a.url, "B": b.url, "C": c.url}
        report["rss_mb_idle"] = {s.name: round(rss_mb(s.pid), 1) for s in (a, b, c)}

        pages: dict[str, Page] = {}
        for server in (a, b, c):
            page = await browser.new_page()
            await page.goto(server.url)
            await page.wait_for_function("window.__renders.length > 0")
            pages[server.name] = page

        # 同じプロセスのツールで書いた場合と、別のプロセスのツールで書いた場合
        report["same_process_A_writes"] = await measure_reflect(a, {"A": pages["A"], "B": pages["B"]}, "byA")
        report["other_process_B_writes"] = await measure_reflect(b, {"A": pages["A"], "B": pages["B"]}, "byB")

        # 別のワークスペース: C の書き換えは C の画面だけ。A・B の書き換えは C の画面に届かない
        report["other_workspace_C_writes"] = await measure_reflect(c, {"C": pages["C"]}, "byC")
        report["C_page_quiet_when_A_writes"] = await assert_quiet(pages["C"], a, "quiet-A")
        report["A_page_quiet_when_C_writes"] = await assert_quiet(pages["A"], c, "quiet-C")
        report["rss_mb_after"] = {s.name: round(rss_mb(s.pid), 1) for s in (a, b, c)}

        # 1 つ目（A）を閉じた後も、B・C の画面の反映が続く
        await a.close()
        report["after_A_closed_B_writes"] = await measure_reflect(b, {"B": pages["B"]}, "afterA-B")
        report["after_A_closed_C_writes"] = await measure_reflect(c, {"C": pages["C"]}, "afterA-C")

        # 送信: C の画面から送り、C を止めて立て直したサーバーで取り込む
        page = pages["C"]
        target = await page.locator("#target").input_value()
        await page.fill("#body", "PoC の送信")
        await page.click("button[type=submit]")
        await page.wait_for_function("document.getElementById('result').textContent === '送りました'")
        report["submissions_yaml_after_post"] = yaml.safe_load((ws2 / "submissions.yaml").read_text(encoding="utf-8"))
        await c.close()
        await b.close()
        c2 = await start("C2", ws2, known)
        report["take_after_restart"] = await call(c2, "take_submissions")
        report["take_again"] = await call(c2, "take_submissions")
        report["submit_target"] = target
        await c2.close()
        await browser.close()
    return report


if __name__ == "__main__":
    out = asyncio.run(main(Path(sys.argv[1])))
    print(json.dumps(out, ensure_ascii=False, indent=1))
