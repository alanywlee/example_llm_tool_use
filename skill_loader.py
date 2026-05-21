from __future__ import annotations

import json
from pathlib import Path


SKILLS_DIR = Path("skills")


def load_skill_instruction(skill_name: str) -> str:
    path = SKILLS_DIR / skill_name / "SKILL.md"
    if not path.exists():
        raise FileNotFoundError(f"Missing skill instruction: {path}")
    return path.read_text(encoding="utf-8")


def load_skill_allowed_tools(skill_name: str) -> set[str]:
    path = SKILLS_DIR / skill_name / "tools.json"
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    return set(data.get("allowed_tools", []))


def build_skill_instruction_block(skill_names: list[str]) -> str:
    if not skill_names:
        return "本輪沒有載入任何 skill。不要使用工具，除非工具已明確提供且任務需要。"

    sections = []
    for skill_name in skill_names:
        instruction = load_skill_instruction(skill_name)
        sections.append(f"<skill name=\"{skill_name}\">\n{instruction}\n</skill>")

    return "以下是本輪載入的 skill instructions。請只依照這些 skill 使用工具。\n\n" + "\n\n".join(sections)


def collect_allowed_tools_from_skills(skill_names: list[str]) -> set[str]:
    allowed_tools = set()
    for skill_name in skill_names:
        allowed_tools.update(load_skill_allowed_tools(skill_name))
    return allowed_tools
