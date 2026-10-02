---
name: setup-allowed
description: PoC 用のセットアップのスキル（allowed-tools あり）。共通のファイルの参照とスクリプトの起動を確かめる
allowed-tools: Read, Bash(python3:*)
---

目印: SETUP-SKILL-MARKER-7341
PLUGIN_ROOT=${CLAUDE_PLUGIN_ROOT}
SKILL_DIR=${CLAUDE_SKILL_DIR}

次の順に実行し、各手順の結果をそのまま出力する。

1. 「SETUP-SKILL-MARKER-7341」と、上の `PLUGIN_ROOT=` と `SKILL_DIR=` の行をそのまま出力する
2. Read ツールで `${CLAUDE_PLUGIN_ROOT}/skills/mindmap/references/marker.md` を読み、中の目印の文字列を出力する
3. Bash ツールで `python3 ${CLAUDE_PLUGIN_ROOT}/skills/mindmap/scripts/mindmap.py check-env` を実行し、標準出力をそのまま出力する

ツールが使えなかった手順は、使えなかった旨を書いて次の手順へ進む。
