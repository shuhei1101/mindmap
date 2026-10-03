"""スキル upgrade（/mindstella:upgrade）のファイルの形の結合テスト。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .skill_files import (
    BASH_RULE,
    SKILLS_DIR,
    launches_not_in_form,
    missing_plugin_paths,
    read_skill,
    skill_markdown_texts,
    texts_with_forbidden_name,
)

if TYPE_CHECKING:
    from pathlib import Path

    from conftest import RunClaude

# 本文のコマンドの一覧に並ぶコマンド
UPGRADE_COMMANDS = [
    "migrate --plan",
    "migrate",
    "migrate --set",
    "migrate --record",
    "check",
    "build",
]


def test_normal(run_claude: RunClaude, repo_root: Path) -> None:
    """スキル upgrade のファイルが制約どおりの形で、プラグインの検証を通る（正常系）。"""
    # 実行
    front_matter, body = read_skill("upgrade")
    texts = skill_markdown_texts("upgrade")
    validate = run_claude("plugin", "validate", str(repo_root))
    # 検証
    # front matter の name が upgrade、allowed-tools が制約の値と一致する
    assert front_matter["name"] == "upgrade"
    assert front_matter["allowed-tools"] == f"Read, {BASH_RULE}"
    assert front_matter["description"]
    # ファイルは SKILL.md だけ
    assert [path.name for path in (SKILLS_DIR / "upgrade").iterdir()] == ["SKILL.md"]
    # 本文の ${CLAUDE_PLUGIN_ROOT}/ で始まるパスが全てリポジトリの中にある
    assert missing_plugin_paths(texts) == []
    # 本文のスクリプトの起動が全て python3 ${CLAUDE_PLUGIN_ROOT}/skills/mindmap/scripts/mindmap.py で始まる
    assert launches_not_in_form(texts) == []
    # 本文のコマンドの一覧に migrate --plan・migrate・migrate --set・migrate --record・check・build がある
    assert [command for command in UPGRADE_COMMANDS if f"| `{command}` |" not in body] == []
    # スキルの Markdown に特定の開発基盤の名前が無い
    assert texts_with_forbidden_name() == []
    # claude plugin validate が終了コード 0（失敗すれば run_claude が例外にする）
    assert validate.returncode == 0
