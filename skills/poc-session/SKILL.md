---
name: poc-session
description: PoC 用の話し合いを進めるスキル。サブエージェントの起動を確かめる
---

目印: SESSION-SKILL-MARKER-5820

次の順に実行する。

1. 「SESSION-SKILL-MARKER-5820」を出力する
2. Agent ツールで general-purpose のサブエージェントを 1 体起動し、「`${CLAUDE_PLUGIN_ROOT}/skills/mindmap/references/marker.md` を Read で読み、中の目印の文字列だけを返す」と依頼する
3. サブエージェントの返答をそのまま出力する
