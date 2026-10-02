"""マーケットプレイスの登録（.claude-plugin/marketplace.json）の結合テスト。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from conftest import RunClaude

MARKETPLACE_NAME = "mindmap"


def _registered_marketplace_names(list_json: str) -> list[str]:
    """claude plugin marketplace list --json の出力から登録済みの名前を取り出す。"""
    return [marketplace["name"] for marketplace in json.loads(list_json)]


def _available_plugin_names(list_json: str) -> list[str]:
    """claude plugin list --available --json の出力から mindmap から入れられるプラグインの名前を取り出す。"""
    available = json.loads(list_json)["available"]
    return [
        plugin["name"] for plugin in available if plugin["marketplaceName"] == MARKETPLACE_NAME
    ]


def test_normal(run_claude: RunClaude, repo_root: Path) -> None:
    """マニフェストが検証を通り、マーケットプレイス mindmap として登録される（正常系）。"""
    # 実行
    validate = run_claude("plugin", "validate", "--json", str(repo_root))
    run_claude("plugin", "marketplace", "add", str(repo_root))
    marketplace_list = run_claude("plugin", "marketplace", "list", "--json")
    plugin_list = run_claude("plugin", "list", "--available", "--json")

    # 検証
    # claude plugin validate は終了コード 0 で、誤りが無く、警告は plugin.json の version の 1 件だけ
    report = json.loads(validate.stdout)
    assert validate.returncode == 0
    assert report["manifest"]["errors"] == []
    assert [warning["path"] for warning in report["manifest"]["warnings"]] == [
        "plugins[0] plugin.json → version"
    ]
    # claude plugin marketplace add の後、登録済みのマーケットプレイスの一覧に mindmap が出る
    assert MARKETPLACE_NAME in _registered_marketplace_names(marketplace_list.stdout)
    # マーケットプレイス mindmap から入れられるプラグインが mindmap の 1 件だけ
    assert _available_plugin_names(plugin_list.stdout) == ["mindmap"]
