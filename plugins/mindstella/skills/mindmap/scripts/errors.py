"""コマンドが終了コード 1 にする例外。"""

from __future__ import annotations


class MindmapError(Exception):
    """入口が捕まえて終了コード 1 と標準エラーにする例外の親。"""

    def __init__(self, message: str, lines: list[str] | None = None) -> None:
        """メッセージと、`エラー: {内容}` の後に続けて出す行を持つ。"""
        super().__init__(message)
        self.lines: list[str] = lines if lines is not None else []


class WorkspaceNotFoundError(MindmapError):
    """`mindmap.yaml` が無いフォルダを指した。"""


class WorkspaceExistsError(MindmapError):
    """`mindmap.yaml` が既にあるフォルダに作ろうとした。"""


class SchemaMismatchError(MindmapError):
    """書き込もうとした・書き出そうとしたワークスペースがスキーマに合わない。"""

    def __init__(self, lines: list[str], *, legacy: bool = False) -> None:
        """合わない箇所ごとの `{ファイル名}: {キーのパス}: {理由}` の行と、前の版の形式の問題があるかを持つ。"""
        super().__init__("スキーマに合いません", lines)
        # 問題に前の版の形式（資料の `done`・題名の無い設定）のものがあるか
        self.legacy = legacy


class ItemNotFoundError(MindmapError):
    """渡した ID の項目が無い。"""


class OptionNotFoundError(MindmapError):
    """検討事項が渡した記号の案を持たない。"""


class WriteFailedError(MindmapError):
    """ファイルの書き込み・置き換えで OSError が起きた。"""


class OutPathError(MindmapError):
    """`export` の `--out` が `.html` で終わらないか、ワークスペースの `preview.html` を指す（入口は終了コード 2）。"""


class DownloadFailedError(MindmapError):
    """配る書き出しで jsDelivr から配布ファイルかライセンスの本文を取れないか、配布ファイルが `integrity` と合わない。"""


class WorkspaceNewerError(MindmapError):
    """ワークスペースの版がプラグインの版より新しいのに、手順を当てる・版を書こうとした。メッセージに 2 つの版とプラグインの更新の案内を持つ。"""


class StepFailedError(MindmapError):
    """移し替えの手順が失敗し、写しから戻した。メッセージは `{版} の手順 {番号}（{操作}）: {理由}`。"""


class StepsInvalidError(MindmapError):
    """プラグインの `steps.yaml` が読めないか、手順の形のスキーマに合わない。`lines` は合わない箇所。"""
