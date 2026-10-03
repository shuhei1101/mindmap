"""プラグインの読み込み（plugins/mindstella/ の .claude-plugin/plugin.json・skills/・LICENSE）の結合テスト。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from conftest import RunClaude

PLUGIN_ID = "mindstella@mindstella"

# 取り込まれたプラグインのフォルダに無いこと（リポジトリの開発用のファイル）
OUTSIDE_PLUGIN_NAMES = ["dev", "docs", "tests", ".storybook", "package.json"]


def _find_installed_plugin(list_json: str) -> dict[str, object]:
    """claude plugin list --json の出力から mindstella@mindstella の行を取り出す。"""
    return next(plugin for plugin in json.loads(list_json) if plugin["id"] == PLUGIN_ID)


def _count_hooks(details: str) -> int:
    """claude plugin details の出力の部品の一覧から hooks の件数を取り出す。"""
    match = re.search(r"Hooks \((\d+)\)", details)
    if match is None:
        raise ValueError(f"部品の一覧に hooks の行が無い: {details}")
    return int(match.group(1))


def test_normal(run_claude: RunClaude, repo_root: Path) -> None:
    """プラグイン mindstella が 2 つのスキルと共通の置き場所と LICENSE を持ち、プラグインの外のフォルダを持たず、hooks を持たずに読み込まれる（正常系）。"""
    # 準備
    run_claude("plugin", "marketplace", "add", str(repo_root))

    # 実行
    run_claude("plugin", "install", PLUGIN_ID)
    plugin_list = run_claude("plugin", "list", "--json")
    details = run_claude("plugin", "details", PLUGIN_ID)

    # 検証
    installed = _find_installed_plugin(plugin_list.stdout)
    install_path = Path(str(installed["installPath"]))
    # claude plugin list で mindstella@mindstella が有効である
    assert installed["enabled"] is True
    # 取り込まれたプラグインのフォルダに 2 つのスキルの SKILL.md と、共通の置き場所の 4 つのフォルダがある
    assert (install_path / "skills" / "setup" / "SKILL.md").is_file()
    assert (install_path / "skills" / "session" / "SKILL.md").is_file()
    shared = install_path / "skills" / "mindmap"
    assert (shared / "references").is_dir()
    assert (shared / "playbooks").is_dir()
    assert (shared / "schemas").is_dir()
    assert (shared / "scripts").is_dir()
    # 取り込まれたプラグインのフォルダの直下に LICENSE があり、本文がリポジトリの直下の LICENSE と一致する
    assert (install_path / "LICENSE").is_file()
    assert (install_path / "LICENSE").read_bytes() == (repo_root / "LICENSE").read_bytes()
    # 取り込まれたプラグインのフォルダに .claude-plugin/plugin.json があり、リポジトリの開発用のファイルが無い
    assert (install_path / ".claude-plugin" / "plugin.json").is_file()
    assert [name for name in OUTSIDE_PLUGIN_NAMES if (install_path / name).exists()] == []
    # claude plugin details で hooks が 0 件である
    assert _count_hooks(details.stdout) == 0
