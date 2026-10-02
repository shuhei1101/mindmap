# ワークスペースの YAML のスキーマと、読み書き・検索・点検・プレビューのビルドのスクリプトを作る

## 概要

スキルが、ワークスペース（1 つの話し合いのフォルダ）の YAML をスクリプトのコマンドで読み書き・検索・点検し、プレビューの HTML を書き出せるようにする。
YAML の形は JSON Schema で決め、書き込む前にスキーマと突き合わせる。

## 背景

[Issue #3](https://github.com/shuhei1101/mindmap/issues/3) の要望。
[#9](https://github.com/shuhei1101/mindmap/pull/9) で `skills/mindmap/schemas/`・`skills/mindmap/scripts/` の枠（`.gitkeep` だけ）を作り、中身をこの PR に渡した。
スキルの手順は [#4](https://github.com/shuhei1101/mindmap/issues/4)、`build` が書き出す画面の中身は [#5](https://github.com/shuhei1101/mindmap/issues/5) が持ち、どちらもこの PR のコマンドの上に載る。

## 計画書

| ファイル | 中身 |
| --- | --- |
| [要件](./要件.md) | 要望の整理と影響する UC 一覧 |
| [スクリプト](./スクリプト.md) | スクリプトの計画書 |
| [確認ログ](./確認ログ.md) | ユーザーへの確認事項の決着 |

## タスク一覧

- [x] ~~初期構築~~（[#9](https://github.com/shuhei1101/mindmap/pull/9) で済んでいる）
- [x] ~~リバースエンジニアリング~~（スクリプトの既存の実装が無い）
- [x] ~~方針決め~~（方針決めを依頼する Issue ではない）
- [x] PoC 検証
- [x] ~~複合ユースケース設計~~（コマンドを連ねる手順はスキルのステップが持つ。[#4](https://github.com/shuhei1101/mindmap/issues/4)）
- [x] ~~デザインスタイル選定~~（画面の見た目を変えない。プレビューの画面は [#5](https://github.com/shuhei1101/mindmap/issues/5)）
- [x] ~~画面一覧・画面遷移~~（画面の見た目を変えない。プレビューの画面は [#5](https://github.com/shuhei1101/mindmap/issues/5)）
- [x] 単一ユースケース設計
- [x] ~~モック作成~~（画面の見た目を変えない。プレビューの画面は [#5](https://github.com/shuhei1101/mindmap/issues/5)）
- [x] インターフェース定義設計
- [x] ~~部品設計~~（画面を持たない）
- [x] ~~画面設計~~（画面を持たない。`build` はデータを埋め込むだけで、UI 項目を足さない）
- [x] モジュール構成設計
- [x] ドキュメント修正
- [ ] 単体テスト作成
- [ ] 実装
- [ ] 結合テスト作成
- [ ] E2E テスト作成