---
name: setup
description: 話し合いを始める・再開するときに、依存を確かめ、新しいワークスペースを作るか既存のワークスペースの状況を示して、話し合いを進めるスキル session へ渡す
argument-hint: "[ワークスペースのフォルダ]"
allowed-tools: Read, Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/mindmap/scripts/mindmap.py:*)
---

# setup

依存を確かめ、新しいワークスペースを作るか、既存のワークスペースの状況を示して、`/mindstella:session` へ渡す。

## 入力

- ワークスペースのフォルダ: $ARGUMENTS
  - 空ならフォルダの指定を尋ねて終える

## ステップ

上から順に進む。

| ステップ | 手順 | 実行する条件 |
| --- | --- | --- |
| 依存の確認 | `check-env` を実行する。終了コードが 1 なら、足りないものと出力の `install` のコマンドを示して止まる（以降は実行しない）。`install` が `null` なら、Python 3.12 以上を入れるよう伝えて止まる | 毎回最初 |
| 新しいワークスペース | `${CLAUDE_PLUGIN_ROOT}/skills/setup/steps/新しいワークスペース.md` | `{ワークスペースのフォルダ}/mindmap.yaml` を Read で読めない |
| 既存のワークスペース | `${CLAUDE_PLUGIN_ROOT}/skills/setup/steps/既存のワークスペース.md` | `{ワークスペースのフォルダ}/mindmap.yaml` を Read で読める |

## コマンド

どれも `python3 ${CLAUDE_PLUGIN_ROOT}/skills/mindmap/scripts/mindmap.py` の後ろに続けて呼ぶ。
中身の JSON は `--json '{JSON}'` の引数で渡す。値の中に `'` が要るときは `'\''` と書く。

| コマンド | 呼び方 | 使う引数 |
| --- | --- | --- |
| `check-env` | `check-env` | なし |
| `init` | `init --workspace {フォルダ} --json '{JSON}'` | `--json` に設定の JSON（`summary`・`field`・`target_label`・`phases`・`targets`・`categories`・`goal`・`links`） |
| `status` | `status --workspace {フォルダ}` | `--workspace` |
| `find` | `find --workspace {フォルダ} --text {文字}` | `--text` |
| `build` | `build --workspace {フォルダ}` | `--workspace` |
