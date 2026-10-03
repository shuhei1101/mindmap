"""スキルのファイル（SKILL.md と steps/）を読む、スキルの結合テストの共通の関数。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

# このファイルから見たリポジトリの直下（tests/integration/skill の 3 つ上）
REPO_ROOT_PARENT_DEPTH = 3
REPO_ROOT = Path(__file__).resolve().parents[REPO_ROOT_PARENT_DEPTH]

# プラグインのフォルダ（`${CLAUDE_PLUGIN_ROOT}` の指す先）
PLUGIN_DIR = REPO_ROOT / "plugins" / "mindstella"

# スキルのフォルダの置き場所
SKILLS_DIR = PLUGIN_DIR / "skills"

# 進め方ガイドの置き場所
PLAYBOOKS_DIR = SKILLS_DIR / "mindmap" / "playbooks"

# 進め方ガイドの `## ` の見出し
SECTION_PATTERN = re.compile(r"^## (.+)$", re.MULTILINE)

# 進め方ガイドの全てが持つ節の並び
PLAYBOOK_SECTIONS = [
    "最上位の軸の呼び名",
    "カテゴリーの分け方",
    "フェーズと観点",
    "必ず調べるもの",
    "ゴールの候補",
    "リリースの形",
]

# 進め方ガイドの分野ごとのファイルの名前（並べ替えた順）
PLAYBOOK_NAMES = ["システム開発.md", "壁打ち.md", "調査.md", "資料作り.md"]

# ゴールの候補の既定の行に付く印
DEFAULT_MARK = "（既定）"

# スクリプトの起動の形（この形のまま起動したときだけ allowed-tools に当たる）
LAUNCH_PREFIX = "python3 ${CLAUDE_PLUGIN_ROOT}/skills/mindmap/scripts/mindmap.py"

# 合わない本文を示すときに出す書き出しの文字数
LEAD_CHARS = 40

# 全てのスキルの allowed-tools に入れる、スクリプトの起動だけの Bash の規則
BASH_RULE = f"Bash({LAUNCH_PREFIX}:*)"

# 本文のプラグインの中のパス
PLUGIN_PATH_PATTERN = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\s`）)、。:]+)")

# 本文の steps/ のファイル
STEP_PATTERN = re.compile(r"skills/[a-z]+/steps/([^\s`）)、。]+\.md)")

# スキルの Markdown に出してはいけない、特定の開発基盤の名前
FORBIDDEN_NAME_PATTERN = re.compile(r"AI Monitor|ai-monitor|ai_monitor", re.IGNORECASE)


def read_skill(skill_name: str) -> tuple[dict[str, Any], str]:
    """SKILL.md の front matter と本文を返す。"""
    text = (SKILLS_DIR / skill_name / "SKILL.md").read_text(encoding="utf-8")
    _, front_matter, body = text.split("---\n", 2)
    return yaml.safe_load(front_matter), body


def step_files_in(skill_name: str) -> list[str]:
    """スキルの steps/ にあるファイルの名前を並びのまま返す。"""
    return sorted(path.name for path in (SKILLS_DIR / skill_name / "steps").glob("*.md"))


def steps_referenced_by(body: str) -> list[str]:
    """本文が指す steps/ のファイルの名前を、重ならないように並びのまま返す。"""
    return sorted(set(STEP_PATTERN.findall(body)))


def skill_markdown_texts(skill_name: str) -> list[str]:
    """スキルの SKILL.md と steps/ の本文（front matter を除く）を返す。"""
    skill_dir = SKILLS_DIR / skill_name
    texts = [read_skill(skill_name)[1]]
    texts += [path.read_text(encoding="utf-8") for path in sorted(skill_dir.glob("steps/*.md"))]
    return texts


def missing_plugin_paths(texts: list[str]) -> list[str]:
    """本文の `${CLAUDE_PLUGIN_ROOT}/` で始まるパスのうち、プラグインのフォルダの中に無いものを返す。"""
    paths = {match for text in texts for match in PLUGIN_PATH_PATTERN.findall(text)}
    # `{field}` のような置き換える箇所を含むパスは、実在を確かめられない
    return sorted(path for path in paths if "{" not in path and not (PLUGIN_DIR / path).exists())


def launches_not_in_form(texts: list[str]) -> list[str]:
    """mindmap.py を指す箇所が、決まった起動の形の数と合わない本文の書き出しを返す。"""
    return [
        text[:LEAD_CHARS] for text in texts if text.count("mindmap.py") != text.count(LAUNCH_PREFIX)
    ]


def playbook_names() -> list[str]:
    """進め方ガイド（skills/mindmap/playbooks/）のファイルの名前を並びのまま返す。"""
    return sorted(path.name for path in PLAYBOOKS_DIR.glob("*.md"))


def playbooks_with_wrong_sections() -> list[str]:
    """進め方ガイドのうち、`## ` の見出しが決まった 6 つの節の並びと合わないものの名前を返す。"""
    return [
        path.name
        for path in sorted(PLAYBOOKS_DIR.glob("*.md"))
        if SECTION_PATTERN.findall(path.read_text(encoding="utf-8")) != PLAYBOOK_SECTIONS
    ]


def _default_goal_rows(text: str) -> list[str]:
    """ガイドの `## ゴールの候補` の節のうち、既定の印を含む表の行を返す。"""
    # `## ゴールの候補` の見出しの次の行から、次の `## ` の見出しの手前までを取る
    section = text.split("## ゴールの候補\n", 1)[1].split("\n## ", 1)[0]
    return [line for line in section.splitlines() if line.startswith("|") and DEFAULT_MARK in line]


def playbooks_without_single_default() -> list[str]:
    """進め方ガイドのうち、ゴールの候補の既定の行が 1 つだけでないものの名前を返す。"""
    return [
        path.name
        for path in sorted(PLAYBOOKS_DIR.glob("*.md"))
        if len(_default_goal_rows(path.read_text(encoding="utf-8"))) != 1
    ]


def texts_with_forbidden_name() -> list[str]:
    """スキルの Markdown のうち、特定の開発基盤の名前を含むファイルのパスを返す。"""
    return [
        str(path.relative_to(REPO_ROOT))
        for path in sorted(SKILLS_DIR.rglob("*.md"))
        if FORBIDDEN_NAME_PATTERN.search(path.read_text(encoding="utf-8"))
    ]
