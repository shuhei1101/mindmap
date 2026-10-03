"""スキル setup（/mindstella:setup）のファイルの形の結合テスト。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .skill_files import (
    BASH_RULE,
    launches_not_in_form,
    missing_plugin_paths,
    read_skill,
    skill_markdown_texts,
    step_files_in,
    steps_referenced_by,
)

if TYPE_CHECKING:
    from pathlib import Path

    from conftest import RunClaude

# スキル setup の steps/ のファイル
SETUP_STEP_FILES = ["新しいワークスペース.md", "既存のワークスペース.md"]


def test_normal(run_claude: RunClaude, repo_root: Path) -> None:
    """スキル setup のファイルが制約どおりの形で、プラグインの検証を通る（正常系）。"""
    # 実行
    front_matter, body = read_skill("setup")
    texts = skill_markdown_texts("setup")
    validate = run_claude("plugin", "validate", str(repo_root))
    # 検証
    # front matter の name が setup、allowed-tools が制約の値と一致する
    assert front_matter["name"] == "setup"
    assert front_matter["allowed-tools"] == f"Read, {BASH_RULE}"
    assert front_matter["description"]
    # 本文の ${CLAUDE_PLUGIN_ROOT}/ で始まるパスが全てリポジトリの中にある
    assert missing_plugin_paths(texts) == []
    # 本文が指す steps/ のファイルが全てある
    assert steps_referenced_by(body) == SETUP_STEP_FILES
    assert step_files_in("setup") == SETUP_STEP_FILES
    # 本文のスクリプトの起動が全て python3 ${CLAUDE_PLUGIN_ROOT}/skills/mindmap/scripts/mindmap.py で始まる
    assert launches_not_in_form(texts) == []
    # claude plugin validate が終了コード 0（失敗すれば run_claude が例外にする）
    assert validate.returncode == 0
