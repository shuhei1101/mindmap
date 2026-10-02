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

    def __init__(self, lines: list[str]) -> None:
        """合わない箇所ごとの `{ファイル名}: {キーのパス}: {理由}` の行を持つ。"""
        super().__init__("スキーマに合いません", lines)


class ItemNotFoundError(MindmapError):
    """渡した ID の項目が無い。"""


class OptionNotFoundError(MindmapError):
    """検討事項が渡した記号の案を持たない。"""


class WriteFailedError(MindmapError):
    """ファイルの書き込み・置き換えで OSError が起きた。"""
