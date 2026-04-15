"""Coach skill 体系 — Anthropic Skill 规范实现。

每个子目录含一个 SKILL.md，loader 运行时扫描并注入 coach_agent 的 BASE_IDENTITY。
LLM 读完所有 skill 后自行判断该用哪个（不做硬编码预匹配）。
"""
from agent.skills.loader import SkillLoader, format_skills_for_prompt  # noqa: F401
