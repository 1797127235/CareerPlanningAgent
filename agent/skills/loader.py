"""Skill loader — 扫 agent/skills/*/SKILL.md 加载所有 skill。

遵循 Anthropic Skill 规范：目录 + SKILL.md 结构。
LLM 读完所有 skill 的 description + body 自行判断该用哪个。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    name: str
    description: str
    body: str
    path: Path  # skill 目录路径，供未来 progressive disclosure 使用


class SkillLoader:
    _skills: list[Skill] = []
    _loaded: bool = False

    @classmethod
    def load_all(cls, skills_dir: Optional[Path] = None) -> None:
        """扫描 skills_dir 下所有子目录，加载其中的 SKILL.md。"""
        if skills_dir is None:
            skills_dir = Path(__file__).parent

        skills: list[Skill] = []
        for sub_dir in sorted(skills_dir.iterdir()):
            if not sub_dir.is_dir() or sub_dir.name.startswith("__"):
                continue
            skill_file = sub_dir / "SKILL.md"
            if not skill_file.exists():
                continue
            try:
                text = skill_file.read_text(encoding="utf-8")
                if not text.startswith("---"):
                    logger.warning("Skill %s missing frontmatter", sub_dir.name)
                    continue
                parts = text.split("---", 2)
                if len(parts) < 3:
                    continue
                frontmatter = yaml.safe_load(parts[1]) or {}
                body = parts[2].strip()
                skills.append(Skill(
                    name=frontmatter.get("name", sub_dir.name),
                    description=frontmatter.get("description", "").strip(),
                    body=body,
                    path=sub_dir,
                ))
            except Exception as e:
                logger.warning("Failed to load skill %s: %s", sub_dir.name, e)

        cls._skills = skills
        cls._loaded = True
        logger.info("SkillLoader loaded %d skills: %s",
                    len(skills), [s.name for s in skills])

    @classmethod
    def all_skills(cls) -> list[Skill]:
        if not cls._loaded:
            cls.load_all()
        return cls._skills


def format_skills_for_prompt() -> str:
    """把所有 skill 的 name + description + body 拼成 prompt 片段。

    LLM 读这个片段后，根据用户本轮消息自行判断该应用哪个 skill（或都不应用）。
    这是 Anthropic 官方 skill 激活机制——信任 LLM 的判断，不做硬编码预匹配。
    """
    skills = SkillLoader.all_skills()
    if not skills:
        return "（尚无可用 skill）"

    parts = []
    for s in skills:
        parts.append(f"### Skill: `{s.name}`")
        parts.append(f"**适用场景**：{s.description}")
        parts.append("")
        parts.append(s.body)
        parts.append("")
    return "\n".join(parts)
