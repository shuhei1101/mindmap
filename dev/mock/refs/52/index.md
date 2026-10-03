# 52

プレビューの画面とスキルの文言を 1 語ずつ点検して直す（[PR #52](https://github.com/shuhei1101/mindmap/pull/52)）。
画面は 21 の共通のスクリプト・スタイル・見本のデータに 40 の資料のボードを合わせ、点検で直した語を当てたもの（`assets/`）を読む。

| 画面 | 中身 |
| --- | --- |
| [overview](../../pages/overview/52/standard/index.html) | 見出し「ゴールまでの進捗」「カテゴリー別の進捗」、要見直し・保留・進行中のタスクの空の表示、次に検討する項目の「影響度 大」 |
| [decisions](../../pages/decisions/52/standard/index.html) | 表の列「着手可否」（着手可能 / 前提待ち）、マップの「タイトルで強調」と空の表示 |
| [tasks](../../pages/tasks/52/standard/index.html) | ボードの空の列「タスクはありません。」 |
| [docs](../../pages/docs/52/standard/index.html) | 資料の絞り込みのチップの「解除」、ボードの空の列 |
| [records](../../pages/records/52/standard/index.html) | 調査・用語集・メモ・会話ログの表の絞り込みのチップの「解除」 |
| [graph](../../pages/graph/52/standard/index.html) | 項目を 1 つも表示しないときの「表示する項目はありません。」 |
| [detail-panel](../../pages/detail-panel/52/standard/index.html) | 関係の見出し「参照元」、履歴の矢印「前の項目へ戻る」「次の項目へ進む」、全画面表示のボタン（押していない） |
| [detail-full](../../pages/detail-full/52/standard/index.html) | 全画面表示のボタン（押されている） |
| [search](../../pages/search/52/standard/index.html) | 入力欄の名前「検索キーワード」と、入力前の案内「ID・タイトル・本文で、すべての項目を検索します。」 |
| [diagram-viewer](../../pages/diagram-viewer/52/standard/index.html) | 図の「拡大表示」のボタン |

| 部品 | 中身 |
| --- | --- |
| [fullscreen-button](../../components/fullscreen-button/index.html) | 全画面表示のボタン（押していない・押されている） |
