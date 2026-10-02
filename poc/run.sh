#!/usr/bin/env bash
# PoC: プラグインの 2 つのスキルの呼び名・共通のファイルの参照・サブエージェントの起動を確かめる
# 使い方: bash poc/run.sh {結果の出力先フォルダ}
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:?結果の出力先フォルダを渡す}"
mkdir -p "$OUT"
WORK="$(mktemp -d)"        # 実行時のカレント（プロジェクトの設定を持たない空のフォルダ）
TMPCFG="$(mktemp -d)"      # インストールだけに使う一時の設定フォルダ
trap 'rm -rf "$WORK" "$TMPCFG"' EXIT

run() { # $1=ケース名 $2=プラグインのフォルダ $3=プロンプト
  (cd "$WORK" && claude -p "$3" --plugin-dir "$2" \
    --setting-sources project,local --permission-mode default \
    --output-format stream-json --verbose \
    >"$OUT/$1.jsonl" 2>"$OUT/$1.stderr")
  echo "$1 exit=$?"
}

# 作業ツリーを --plugin-dir で読む
run worktree-setup "$ROOT" "/mindmap:setup"
run worktree-setup-allowed "$ROOT" "/mindmap:setup-allowed"
run worktree-poc-session "$ROOT" "/mindmap:poc-session"
run worktree-poc-session-allowed "$ROOT" "/mindmap:poc-session-allowed"

# 一時の設定フォルダでインストールし、取り込まれたフォルダを --plugin-dir で読む
CLAUDE_CONFIG_DIR="$TMPCFG" claude plugin marketplace add "$ROOT" >"$OUT/install.log" 2>&1
CLAUDE_CONFIG_DIR="$TMPCFG" claude plugin install mindmap@mindmap >>"$OUT/install.log" 2>&1
CLAUDE_CONFIG_DIR="$TMPCFG" claude plugin list --json >"$OUT/plugin-list.json" 2>>"$OUT/install.log"
INSTALL_PATH="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); p=d if isinstance(d,list) else d.get("plugins",d); print(next(x["installPath"] for x in p if x.get("id","").startswith("mindmap@") or x.get("name")=="mindmap"))' "$OUT/plugin-list.json")"
echo "installPath=$INSTALL_PATH" | tee -a "$OUT/install.log"
run installed-setup "$INSTALL_PATH" "/mindmap:setup"
run installed-setup-allowed "$INSTALL_PATH" "/mindmap:setup-allowed"
run installed-poc-session-allowed "$INSTALL_PATH" "/mindmap:poc-session-allowed"
