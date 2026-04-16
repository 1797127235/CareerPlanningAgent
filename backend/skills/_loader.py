"""Skill loader: parse YAML frontmatter + Markdown body from SKILL.md files.

Usage:
    from backend.skills import load_skill, render_skill

    skill = load_skill("narrative")
    system_prompt, user_prompt, cfg = render_skill("narrative",
        target_label="系统C++工程师",
        claimed_skills="C++, Python, PyTorch",
        projects_list="- Muduo 网络库复现\n- ...",
        education_line="某 211 学校 · 计算机 · 硕士",
        delta_line="距上次报告 8 天，期间完成了 Redis 基础。",
        market_line="目前招聘窗口一般，薪资 p50 ¥28k。",
    )
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml

_SKILLS_DIR = Path(__file__).parent


class SkillNotFoundError(Exception): ...
class SkillFormatError(Exception): ...
class SkillOutputParseError(Exception): ...


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    model: Literal["fast", "strong"]
    temperature: float
    max_tokens: int
    output: Literal["text", "json"]
    system: str
    user_template: str


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


@lru_cache(maxsize=32)
def load_skill(name: str) -> Skill:
    """Load and cache a skill by directory name."""
    skill_path = _SKILLS_DIR / name / "SKILL.md"
    if not skill_path.is_file():
        raise SkillNotFoundError(f"{skill_path} not found")

    raw = skill_path.read_text(encoding="utf-8")
    m = _FRONTMATTER_RE.match(raw)
    if not m:
        raise SkillFormatError(f"{skill_path}: missing YAML frontmatter")

    meta = yaml.safe_load(m.group(1)) or {}
    body = m.group(2)

    # 拆 ## System / ## User. Convention: `## System` always precedes `## User`,
    # and `## User` is the last top-level section. The user block runs to EOF so
    # that `##` sub-headings inside the template aren't mistaken for section
    # boundaries (earlier versions truncated user_template at the first sub-heading).
    system_match = re.search(r"##\s*System\s*\n(.*?)\n##\s*User\s*\n", body, re.DOTALL)
    user_match = re.search(r"##\s*User\s*\n(.*)\Z", body, re.DOTALL)
    if not system_match or not user_match:
        raise SkillFormatError(f"{skill_path}: missing ## System or ## User section")

    required = {"name", "description", "model", "temperature", "max_tokens", "output"}
    missing = required - set(meta.keys())
    if missing:
        raise SkillFormatError(f"{skill_path}: frontmatter missing {missing}")

    return Skill(
        name=meta["name"],
        description=meta["description"],
        model=meta["model"],
        temperature=float(meta["temperature"]),
        max_tokens=int(meta["max_tokens"]),
        output=meta["output"],
        system=system_match.group(1).strip(),
        user_template=user_match.group(1).strip(),
    )


def render_skill(name: str, **ctx) -> tuple[str, str, Skill]:
    """Load a skill and render its user template with ctx variables.

    Returns (system_prompt, user_prompt, skill) — skill carries model config.
    """
    skill = load_skill(name)
    try:
        user_prompt = skill.user_template.format(**ctx)
    except KeyError as e:
        raise SkillFormatError(f"{name}: missing template variable {e}") from e
    return skill.system, user_prompt, skill


def invoke_skill(name: str, **ctx) -> str | dict:
    """End-to-end: render + call LLM + optional JSON parse.

    For skills with output=json, returns parsed dict (raises SkillOutputParseError
    on malformed output).  For text, returns raw string.
    """
    from backend.llm import get_llm_client, get_model
    system, user, skill = render_skill(name, **ctx)

    resp = get_llm_client(timeout=120).chat.completions.create(
        model=get_model(skill.model),
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=skill.temperature,
        max_tokens=skill.max_tokens,
    )
    raw = resp.choices[0].message.content.strip()

    if skill.output == "json":
        import json
        # 容错剥壳 ```json ... ```
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        try:
            return json.loads(raw.strip())
        except json.JSONDecodeError as e:
            raise SkillOutputParseError(f"{name}: {e}") from e

    return raw
