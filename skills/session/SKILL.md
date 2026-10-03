---
name: session
description: セットアップの後に、ワークスペースの話し合いを進めるとき。発言の取り込み・ヒアリング・リサーチ・方針転換・プレビュー・ゴール判定を場面に応じて回し、ゴールまで進める
argument-hint: "[ワークスペースのフォルダ]"
allowed-tools: Read, Agent, WebSearch, WebFetch, Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/mindmap/scripts/mindmap.py:*)
---

# session

作成済みのワークスペースで、利用者の発言を記録しながら、ゴールまで話し合いを進める。

## 入力

- ワークスペースのフォルダ: $ARGUMENTS
  - 空なら、同じ会話で `/mindmap:setup` が渡したフォルダを使う。それも無ければ `/mindmap:setup` を案内して終える
  - `{ワークスペースのフォルダ}/mindmap.yaml` を Read で読めないときは、何も書き込まず `/mindmap:setup` を案内して終える

## ステップ

発言のたびに、場面に合うステップを選ぶ。
ワークスペースを編集したステップは、最後に `build` を流す。

| ステップ | 手順 | 実行する場面 |
| --- | --- | --- |
| 準備 | `{ワークスペースのフォルダ}/mindmap.yaml` を Read で読み、`field` と同じ名前の進め方ガイド（`${CLAUDE_PLUGIN_ROOT}/skills/mindmap/playbooks/{field}.md`）を Read で読む | 話し合いの最初の 1 回 |
| 取り込み | `${CLAUDE_PLUGIN_ROOT}/skills/session/steps/取り込み.md` | 利用者が発言した（決め事・問い・やること・保留・中止・図や文書・脱線した質問） |
| ヒアリング | `${CLAUDE_PLUGIN_ROOT}/skills/session/steps/ヒアリング.md` | 取り込みの後に前提が揃った未決定がある、または利用者が次に決めることを求めた |
| リサーチ | `${CLAUDE_PLUGIN_ROOT}/skills/session/steps/リサーチ.md` | 外部ライブラリ・外部 API を決める検討事項が積まれた、進め方ガイドの「必ず調べるもの」に当たった、または利用者が調べるよう頼んだ |
| 方針転換 | `${CLAUDE_PLUGIN_ROOT}/skills/session/steps/方針転換.md` | 利用者が決定済みの検討事項の案を変える、またはスコープが変わって納品物が要らなくなった |
| プレビュー | `${CLAUDE_PLUGIN_ROOT}/skills/session/steps/プレビュー.md` | 利用者が記録を見たいと言った、または人に渡したいと言った |
| ゴール判定 | `${CLAUDE_PLUGIN_ROOT}/skills/session/steps/ゴール判定.md` | 利用者がゴールに届いたかを尋ねた、または `next` の候補が無くなった |

## コマンド

どれも `python3 ${CLAUDE_PLUGIN_ROOT}/skills/mindmap/scripts/mindmap.py` の後ろに続けて呼ぶ。
中身の JSON は `--json '{JSON}'` の引数で渡す。値の中に `'` が要るときは `'\''` と書く。

| コマンド | 呼び方 | 使う引数 |
| --- | --- | --- |
| `add` | `add {種類} --workspace {フォルダ} --json '{JSON}'` | `種類`（`decision`・`task`・`research`・`doc`・`term`・`note`・`log`）。`--json` に項目の JSON（`id`・`created`・`updated`・`body` は渡さない。本文は `body_markdown`） |
| `update` | `update {ID} --workspace {フォルダ} --json '{JSON}'` | `ID`。`--json` に置き換えるキーの JSON（消すキーは `null`） |
| `adopt` | `adopt {ID} {記号} --workspace {フォルダ}` | `ID`（検討事項）・`記号`（採用する案） |
| `next` | `next --workspace {フォルダ} [--limit {件数}]` | `--limit` |
| `impact` | `impact {ID} --workspace {フォルダ}` | `ID` |
| `find` | `find --workspace {フォルダ} [--text {文字}] [--kind {種類}] [--status {状態}] [--tag {タグ}] [--target {対象}] [--category {カテゴリー}] [--phase {フェーズ}] [--attr {名前=値}]` | 条件は全て任意 |
| `show` | `show {ID} --workspace {フォルダ}` | `ID` |
| `status` | `status --workspace {フォルダ}` | `--workspace` |
| `check` | `check --workspace {フォルダ}` | `--workspace` |
| `build` | `build --workspace {フォルダ}` | `--workspace` |
| `export` | `export --workspace {フォルダ} --out {パス}` | `--workspace`・`--out` |
| `goal` | `goal --workspace {フォルダ}` | `--workspace` |
| `clear-release` | `clear-release --workspace {フォルダ}` | `--workspace` |
