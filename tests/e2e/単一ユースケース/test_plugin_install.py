"""プラグインのインストール（マーケットプレイスの登録からプラグイン mindmap のインストールまで）の E2E テスト。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from conftest import RunClaude

MARKETPLACE_NAME = "mindmap"
PLUGIN_ID = "mindmap@mindmap"


def _registered_marketplace_names(list_json: str) -> list[str]:
    """claude plugin marketplace list --json の出力から登録済みの名前を取り出す。"""
    return [marketplace["name"] for marketplace in json.loads(list_json)]


def _find_installed_plugin(list_json: str) -> dict[str, object]:
    """claude plugin list --json の出力から mindmap@mindmap の行を取り出す。"""
    return next(plugin for plugin in json.loads(list_json) if plugin["id"] == PLUGIN_ID)


def _count_hooks(details: str) -> int:
    """claude plugin details の出力の部品の一覧から hooks の件数を取り出す。"""
    match = re.search(r"Hooks \((\d+)\)", details)
    if match is None:
        raise ValueError(f"部品の一覧に hooks の行が無い: {details}")
    return int(match.group(1))


def test_normal(run_claude: RunClaude, repo_root: Path) -> None:
    """利用者がマーケットプレイスを登録してプラグイン mindmap をインストールし、一覧で有効になる（正常系）。"""
    # 実行
    run_claude("plugin", "marketplace", "add", str(repo_root))
    marketplace_list = run_claude("plugin", "marketplace", "list", "--json")
    run_claude("plugin", "install", PLUGIN_ID)
    plugin_list = run_claude("plugin", "list", "--json")
    details = run_claude("plugin", "details", PLUGIN_ID)

    # 検証
    installed = _find_installed_plugin(plugin_list.stdout)
    install_path = Path(str(installed["installPath"]))
    # 登録済みのマーケットプレイスの一覧に mindmap がある
    assert MARKETPLACE_NAME in _registered_marketplace_names(marketplace_list.stdout)
    # インストール済みのプラグインの一覧に mindmap@mindmap が有効である
    assert installed["enabled"] is True
    # インストールしたプラグインのフォルダに 2 つのスキルの SKILL.md と、共通の置き場所の 4 つのフォルダがある
    assert (install_path / "skills" / "setup" / "SKILL.md").is_file()
    assert (install_path / "skills" / "session" / "SKILL.md").is_file()
    shared = install_path / "skills" / "mindmap"
    assert (shared / "references").is_dir()
    assert (shared / "playbooks").is_dir()
    assert (shared / "schemas").is_dir()
    assert (shared / "scripts").is_dir()
    # インストールしたプラグインが hooks を持たない
    assert _count_hooks(details.stdout) == 0
