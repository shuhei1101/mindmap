---
name: upgrade
description: プラグインを上げた後、ワークスペースの版が古いと案内されたときに、ワークスペースの版とプラグインの版を比べ、版ごとの手順を当てて今の版へ移し替えるスキル
argument-hint: "[ワークスペースのフォルダ]"
allowed-tools: Read, Bash(python3 ${CLAUDE_PLUGIN_ROOT}/skills/mindmap/scripts/mindmap.py:*)
---

# upgrade

ワークスペースの版とプラグインの版を比べ、版ごとの手順を当てて今の版へ移し替える。
写しを取る・手順を当てる・値を入れる・版を書き換えるは `migrate` が行い、このスキルが自分でファイルを書くことはない。

## 入力

- ワークスペースのフォルダ: $ARGUMENTS
  - 空ならフォルダの指定を尋ねて終える
  - `{ワークスペースのフォルダ}/mindmap.yaml` を Read で読めないときは、何も書き込まず `/mindstella:setup` を案内して終える

## ステップ

上から順に進む。

| ステップ | 手順 |
| --- | --- |
| 依存の確認 | `check-env` を実行する。終了コードが 1 なら、足りないものと出力の `install` のコマンドを示して止まる（以降は実行しない）。`install` が `null` なら、Python 3.12 以上を入れるよう伝えて止まる |
| 版の比較 | `migrate --plan` を呼び、出力の `relation` を読む。`same` なら移し替えるものが無いと示して終える。`newer` ならプラグインを更新するよう案内して止まる（以降は実行しない） |
| 手順の一覧 | 出力の `steps` を版の順に、`version` と `summary` で示す。`destructive` が `true` の手順があるときだけ、当ててよいかを利用者に確かめる（利用者が断ったら止まる） |
| 手順を当てる | `migrate`（`--plan` なし）を呼ぶ。終了コードが 1 なら、標準エラーの失敗した版・手順・理由を示して止まる（`migrate` が写しから戻している）。出力の `backup` が写しの場所になる |
| 点検 | `check` を呼ぶ。`migrate` の出力の `needs_values` のキーだけを、`description` を添えて利用者に聞き、答えを `migrate --set` で入れる。`needs_values` のキー以外の問題が出たときは、示して止まる |
| 版の書き換え | `migrate --record` を呼ぶ。終了コードが 1 なら、標準エラーの合わない箇所を示して止まる |
| 仕上げ | `build` を呼ぶ。出力の `recorded` の版と、`backup` の写しの場所を示し、`/mindstella:session {ワークスペースのフォルダ}` で続けるよう案内する |

## コマンド

どれも `python3 ${CLAUDE_PLUGIN_ROOT}/skills/mindmap/scripts/mindmap.py` の後ろに続けて呼ぶ。

| コマンド | 呼び方 | 使う引数 |
| --- | --- | --- |
| `check-env` | `check-env` | なし |
| `migrate --plan` | `migrate --workspace {フォルダ} --plan` | `--workspace` |
| `migrate` | `migrate --workspace {フォルダ}` | `--workspace` |
| `migrate --set` | `migrate --workspace {フォルダ} --set {ファイル}:{キーのパス}={値}` | `--set`（値が要るキーごとに繰り返す。値の中に空白があるときは引用符で囲む） |
| `migrate --record` | `migrate --workspace {フォルダ} --record` | `--workspace` |
| `check` | `check --workspace {フォルダ}` | `--workspace` |
| `build` | `build --workspace {フォルダ}` | `--workspace` |
