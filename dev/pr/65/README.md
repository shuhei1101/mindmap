# プレビューの狭い幅で、ボードの列を最初の画面からはみ出させない

## 概要

スマートフォンなどの狭い幅でプレビューを開いた利用者が、検討事項・タスク・資料のボードを、列が最初の画面からはみ出さない形で読めるようにする。

## 背景

[Issue #62](https://github.com/shuhei1101/mindmap/issues/62) の要望。
[style.css](https://github.com/shuhei1101/mindmap/blob/develop/plugins/mindstella/skills/mindmap/preview/style.css) は `@media (max-width: 720px)` の中で `.board` を 1 列にしているが、後ろの無条件の `.board { grid-template-columns: repeat(var(--cols), 290px); }` に負け、390px でも 290px の列が横に並ぶ。
[PR #60](https://github.com/shuhei1101/mindmap/pull/60)（[Issue #58](https://github.com/shuhei1101/mindmap/issues/58)）のモックのレビューで、reviewer が [PR #21](https://github.com/shuhei1101/mindmap/pull/21) から引き継いだ検出 `first-viewport-column-overflow` として報告した（[報告](https://github.com/shuhei1101/mindmap/pull/60#discussion_r4174048392)）。
PR #60 は `.board` の左端の余白だけを扱う。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理と影響する UC 一覧 |
| [プレビュー](./プレビュー.md) | プレビューの計画書 |
| [確認ログ](./確認ログ.md) | ユーザーへの確認事項の決着 |

## タスク一覧

- [x] ~~初期構築~~（[#9](https://github.com/shuhei1101/mindmap/pull/9) で済んでいる）
- [x] ~~リバースエンジニアリング~~（プレビューの設計書が揃っている）
- [x] ~~方針決め~~（方針決めを依頼する Issue ではない）
- [x] ~~PoC 検証~~（`.board` の CSS の指定の順と値の付け替えで、未検証の技術機構に依存しない）
- [x] ~~複合ユースケース設計~~（影響なし: 業務の流れは変わらない）
- [x] ~~デザインスタイル選定~~（デザイン方針があり、見た目の方向を変えない）
- [x] ~~画面一覧・画面遷移~~（画面の追加・削除と画面遷移の変更を含まない）
- [x] ~~単一ユースケース設計~~（利用者の操作と結果は変わらず、シナリオの記述は変わらない）
- [x] モック作成
- [x] ~~インターフェース定義設計~~（プレビューを開く入出力は変わらない）
- [x] ~~部品設計~~（ボードは部品設計を持たず、部品の引数・スロット・イベント・状態は変わらない）
- [x] 画面設計
- [x] ~~モジュール構成設計~~（関数・型を変えない）
- [x] ~~ドキュメント修正~~（設計書のほかに更新するページが無い）
- [x] ~~単体テスト作成~~（モジュール構成の関数・型を変えず、直すのは `style.css` だけ）
- [x] 実装
- [x] 結合テスト作成
- [x] ~~E2E テスト作成~~（シナリオが変わらない）