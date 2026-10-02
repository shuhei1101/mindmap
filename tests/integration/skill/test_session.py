"""スキル session（/mindmap:session）と共通の置き場所のファイルの形の結合テスト。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .skill_files import (
    BASH_RULE,
    PLAYBOOK_NAMES,
    SKILLS_DIR,
    launches_not_in_form,
    missing_plugin_paths,
    playbook_names,
    playbooks_with_wrong_sections,
    playbooks_without_single_default,
    read_skill,
    skill_markdown_texts,
    step_files_in,
    steps_referenced_by,
    texts_with_forbidden_name,
)

if TYPE_CHECKING:
    from pathlib import Path

    from conftest import RunClaude

# スキル session の steps/ のファイル
SESSION_STEP_FILES = [
    "ゴール判定.md",
    "ヒアリング.md",
    "プレビュー.md",
    "リサーチ.md",
    "取り込み.md",
    "方針転換.md",
]


def test_normal(run_claude: RunClaude, repo_root: Path) -> None:
    """スキル session と共通の置き場所のファイルが制約どおりの形で、プラグインの検証を通る（正常系）。"""
    # 実行
    front_matter, body = read_skill("session")
    texts = skill_markdown_texts("session")
    validate = run_claude("plugin", "validate", str(repo_root))
    # 検証
    # front matter の name が session、allowed-tools が制約の値と一致する
    assert front_matter["name"] == "session"
    assert front_matter["allowed-tools"] == f"Read, Agent, WebSearch, WebFetch, {BASH_RULE}"
    assert front_matter["description"]
    # steps/ に 6 つのステップのファイルがあり、SKILL.md のステップの表がその全てを指す
    assert step_files_in("session") == SESSION_STEP_FILES
    assert steps_referenced_by(body) == SESSION_STEP_FILES
    # SKILL.md と steps/ の本文の ${CLAUDE_PLUGIN_ROOT}/ で始まるパスが全てリポジトリの中にある
    assert missing_plugin_paths(texts) == []
    # 本文のスクリプトの起動が全て python3 ${CLAUDE_PLUGIN_ROOT}/skills/mindmap/scripts/mindmap.py で始まる
    assert launches_not_in_form(texts) == []
    # skills/mindmap/ に SKILL.md が無く、references/・playbooks/ がある
    assert not (SKILLS_DIR / "mindmap" / "SKILL.md").exists()
    assert (SKILLS_DIR / "mindmap" / "references").is_dir()
    assert (SKILLS_DIR / "mindmap" / "playbooks").is_dir()
    # playbooks/ に システム開発・調査・資料作り・壁打ち の 4 つのガイドがある
    assert playbook_names() == PLAYBOOK_NAMES
    # どのガイドも 6 つの節をその並びで持つ
    assert playbooks_with_wrong_sections() == []
    # どのガイドも `## ゴールの候補` に（既定）の行を 1 つだけ持つ
    assert playbooks_without_single_default() == []
    # スキルの全ての Markdown に特定の開発基盤の名前が無い
    assert texts_with_forbidden_name() == []
    # claude plugin validate が終了コード 0（失敗すれば run_claude が例外にする）
    assert validate.returncode == 0
