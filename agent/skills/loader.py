"""Skill loader — Progressive Disclosure 版本。

职责拆分：
  - scan / catalog: 启动时加载 name + description，~500 tokens，永久驻留
  - full: 按需加载 body，首次读文件 + memoize

遵循 Anthropic Skill 规范：目录 + SKILL.md 结构。
LLM 读 catalog 后调 load_skill(name) tool 拿 full body，不做硬编码预匹配。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class SkillCatalogEntry:
    """Lightweight metadata（只含 name + description + 目录路径）。"""
    name: str
    description: str
    path: Path  # skill 目录路径（load_full 用）


class SkillLoader:
    """Skill 存储层。启动加载 catalog，body 按需 + cache。"""

    _catalog: list[SkillCatalogEntry] = []
    _body_cache: dict[str, str] = {}
    _loaded: bool = False

    @classmethod
    def load_catalog(cls, skills_dir: Optional[Path] = None) -> None:
        """扫描所有子目录，只解析 frontmatter（快速启动）。"""
        if skills_dir is None:
            skills_dir = Path(__file__).parent

        catalog: list[SkillCatalogEntry] = []
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
                catalog.append(SkillCatalogEntry(
                    name=frontmatter.get("name", sub_dir.name),
                    description=frontmatter.get("description", "").strip(),
                    path=sub_dir,
                ))
            except Exception as e:
                logger.warning("Failed to scan skill %s: %s", sub_dir.name, e)

        cls._catalog = catalog
        cls._body_cache = {}
        cls._loaded = True
        logger.info("SkillLoader catalog loaded: %d skills %s",
                    len(catalog), [s.name for s in catalog])

    @classmethod
    def all_catalog(cls) -> list[SkillCatalogEntry]:
        if not cls._loaded:
            cls.load_catalog()
        return cls._catalog

    @classmethod
    def skill_names(cls) -> list[str]:
        """用于 load_skill tool 的 docstring 动态注入。"""
        return [s.name for s in cls.all_catalog()]

    @classmethod
    def load_full(cls, name: str) -> Optional[str]:
        """按需加载 skill 的完整 body，memoize。

        返回 None = skill 不存在。
        """
        if name in cls._body_cache:
            return cls._body_cache[name]

        entry = next((s for s in cls.all_catalog() if s.name == name), None)
        if entry is None:
            logger.warning("load_full: unknown skill %r", name)
            return None

        skill_file = entry.path / "SKILL.md"
        try:
            text = skill_file.read_text(encoding="utf-8")
            parts = text.split("---", 2)
            body = parts[2].strip() if len(parts) >= 3 else ""
            cls._body_cache[name] = body
            return body
        except Exception as e:
            logger.warning("load_full(%s) failed: %s", name, e)
            return None


def format_catalog_for_prompt() -> str:
    """把 catalog（name + description）拼成轻量 prompt 片段。

    LLM 读 catalog 后判断需要哪个 skill，调 load_skill(name) 按需加载 body。
    """
    catalog = SkillLoader.all_catalog()
    if not catalog:
        return "（尚无可用 skill）"

    lines = ["## 可用场景 skill（读完本轮消息后判断是否需要其中某个，需要则调 `load_skill` 工具加载详细规则）", ""]
    for s in catalog:
        lines.append(f"- **{s.name}**: {s.description}")
    return "\n".join(lines)
