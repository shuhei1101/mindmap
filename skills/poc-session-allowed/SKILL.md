---
name: poc-session-allowed
description: PoC 用の話し合いを進めるスキル（allowed-tools あり）。サブエージェントへ許可が及ぶかを確かめる
allowed-tools: Read, Agent, WebSearch
---

目印: SESSION-SKILL-MARKER-5820

次の順に実行する。

1. 「SESSION-SKILL-MARKER-5820」を出力する
2. Agent ツールで general-purpose のサブエージェントを 1 体起動し、「`${CLAUDE_PLUGIN_ROOT}/skills/mindmap/references/marker.md` を Read で読み、中の目印の文字列を返す。続けて WebSearch で `Claude Code plugin skills` を 1 回検索し、最初の結果の URL を返す」と依頼する
3. サブエージェントの返答をそのまま出力する
