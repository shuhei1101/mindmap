# 71

プレビューの詳細パネルから、項目の ID ごとに回答・意見を送る（[PR #71](https://github.com/shuhei1101/mindstella/pull/71)）。
画面は 52 の見本のデータと、52 のスクリプトに送信の入力とサーバーにつながらないときの表示を足したもの（`assets/app.js`）を読み、スタイルは 65 の上に送信の分（`assets/style.css`）を重ねる。
モック専用の操作列で、サーバーにつながらない・配る書き出しの状態に切り替える。

| 画面 | 中身 |
| --- | --- |
| [detail-panel](../../pages/detail-panel/71/index.md) | 詳細パネル。入力の置き方を 2 案（下端に留める・本文の最後） |
| [detail-full](../../pages/detail-full/71/index.md) | 詳細の全画面。入力の置き方を 2 案（下端に留める・本文の最後） |
| [send-form](../../components/send-form/index.html) | 回答・意見の送信の部品の状態と、サーバーにつながらないときのトップバーの表示 |
