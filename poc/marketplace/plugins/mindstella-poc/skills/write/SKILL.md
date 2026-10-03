---
name: write
description: PoC。ワークスペースに項目を 1 件足し、プレビューの URL を示す
argument-hint: "[項目の題名]"
allowed-tools: mcp__mindstella__add_item, mcp__mindstella__preview_url, mcp__mindstella__take_submissions
---

# write

- `mcp__mindstella__add_item` を `title`: $ARGUMENTS で呼ぶ
- `mcp__mindstella__preview_url` を呼び、返った URL を示す
