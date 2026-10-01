"""プラグインの読み込み（.claude-plugin/plugin.json と skills/）の結合テスト。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from conftest import RunClaude

PLUGIN_ID = "mindmap@mindmap"


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
    """プラグイン mindmap がスキルのフォルダを持ち、hooks を持たずに読み込まれる（正常系）。"""
    # 準備
    run_claude("plugin", "marketplace", "add", str(repo_root))

    # 実行
    run_claude("plugin", "install", PLUGIN_ID)
    plugin_list = run_claude("plugin", "list", "--json")
    details = run_claude("plugin", "details", PLUGIN_ID)

    # 検証
    installed = _find_installed_plugin(plugin_list.stdout)
    install_path = Path(str(installed["installPath"]))
    # claude plugin list で mindmap@mindmap が有効である
    assert installed["enabled"] is True
    # 取り込まれたプラグインのフォルダに skills/mindmap/schemas/ と skills/mindmap/scripts/ がある
    assert (install_path / "skills" / "mindmap" / "schemas").is_dir()
    assert (install_path / "skills" / "mindmap" / "scripts").is_dir()
    # claude plugin details で hooks が 0 件である
    assert _count_hooks(details.stdout) == 0
