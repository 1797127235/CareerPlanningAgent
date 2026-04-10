"""Semantic intent router — Tier 2 classification between regex and LLM.

Uses semantic-router with DashScope embedding API for fast
intent classification (~93% accuracy, sub-second).
"""
from __future__ import annotations

import logging
import os

import tiktoken

logger = logging.getLogger(__name__)

_router = None
_initialized = False


def _make_encoder():
    """Create OpenAIEncoder compatible with DashScope text-embedding-v3."""
    from semantic_router.encoders import OpenAIEncoder

    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

    if not api_key or api_key == "sk-placeholder":
        return None

    # Monkey-patch tiktoken to handle unknown DashScope model names
    _original = tiktoken.encoding_for_model

    def _patched(model_name: str):
        try:
            return _original(model_name)
        except KeyError:
            return tiktoken.get_encoding("cl100k_base")

    tiktoken.encoding_for_model = _patched
    try:
        encoder = OpenAIEncoder(
            name="text-embedding-v3",
            openai_api_key=api_key,
            openai_base_url=base_url,
            score_threshold=0.72,
        )
    finally:
        tiktoken.encoding_for_model = _original

    return encoder


def _build_router():
    """Build and cache the semantic router with Chinese example utterances."""
    global _router, _initialized
    if _initialized:
        return _router

    _initialized = True

    try:
        from semantic_router import Route
        from semantic_router.routers import SemanticRouter

        encoder = _make_encoder()
        if encoder is None:
            logger.warning("No API key for semantic router, skipping")
            return None

        routes = [
            Route(
                name="navigator",
                utterances=[
                    # 图谱推荐/方向分析（不含搜索动词）
                    "推荐适合我的岗位方向",
                    "我能做什么方向的工作",
                    "根据我的技能推荐方向",
                    "帮我看看转型路径",
                    "从后端转前端可行吗",
                    "有哪些方向和我匹配",
                    "探索一下岗位图谱",
                    "分析一下我适合的技术方向",
                    "哪个方向更适合我",
                    "C++能去哪些方向",
                    "这个方向的市场前景怎么样",
                ],
            ),
            Route(
                name="search_jd",
                utterances=[
                    # 明确搜索意图
                    "帮我搜几份招聘",
                    "搜搜C++后端开发的工作",
                    "搜索前端工程师招聘信息",
                    "找几份Java开发的JD",
                    "看看市场上有什么岗位在招",
                    "帮我找工作机会",
                    "搜一下大厂的后端招聘",
                    # 搜+适合我的岗位（容易和navigator混淆）
                    "帮我搜搜我适合的岗位信息",
                    "找找适合我的岗位招聘",
                    "搜搜有没有适合我的招聘",
                    "帮我找找适合的岗位",
                    "搜一下适合我的工作机会",
                    "搜搜看有哪些适合我的职位",
                    "帮我找找我能投的岗位",
                    "给我搜几个合适的工作",
                    "找找大厂适合我的招聘",
                    "搜搜字节腾讯的招聘",
                    "帮我找找最新的校招信息",
                ],
            ),
            Route(
                name="jd_agent",
                utterances=[
                    "诊断这份JD的匹配度",
                    "帮我分析这个岗位要求",
                    "看看我和这份工作差多少",
                    "诊断JD匹配度",
                    "分析一下这个职位描述",
                ],
            ),
            Route(
                name="profile_agent",
                utterances=[
                    "看看我的画像",
                    "分析我的技能",
                    "我有哪些能力",
                    "我的简历怎么样",
                    "帮我评估一下我的背景",
                ],
            ),
            Route(
                name="practice_agent",
                utterances=[
                    "出一道面试题",
                    "练习面试",
                    "来道算法题",
                    "模拟面试",
                    "帮我练练面试",
                    "出一道关于数据库的题",
                    "练一道系统设计题",
                ],
            ),
            Route(
                name="growth_agent",
                utterances=[
                    "看看我的成长数据",
                    "学习进度怎么样了",
                    "下一步该做什么",
                    "我的学习路径进展如何",
                ],
            ),
            Route(
                name="report_agent",
                utterances=[
                    "生成职业报告",
                    "帮我出一份分析报告",
                    "导出职业发展报告",
                ],
            ),
            Route(
                name="chat",
                utterances=[
                    "不知道该往哪个方向发展",
                    "我很迷茫不知道干什么",
                    "前端和后端该怎么选",
                    "我是计算机专业学生",
                    "你好",
                    "这个系统能做什么",
                    "我大三了很焦虑",
                    "计算机方向太多了不知道选哪个",
                    "该怎么办",
                    "谢谢",
                ],
            ),
        ]

        _router = SemanticRouter(encoder=encoder, routes=[])
        # Synchronously add routes (embeds all utterances and populates index)
        for route in routes:
            _router.add(route)
        logger.info("Semantic intent router initialized with %d routes", len(routes))
        return _router

    except Exception as e:
        logger.warning("Failed to build semantic router: %s", e)
        return None


def classify_intent(text: str) -> tuple[str | None, str]:
    """Classify user intent using semantic similarity.

    Returns (agent_name, tool_hint) or (None, "") if no confident match.
    """
    router = _build_router()
    if router is None:
        return None, ""

    try:
        result = router(text)
        if result and result.name:
            if result.name == "search_jd":
                return "navigator", "search_real_jd"
            if result.name == "chat":
                return "coach_agent", ""
            return result.name, ""
        return "coach_agent", ""  # Default to coach for unmatched
    except Exception as e:
        logger.warning("Semantic router classification failed: %s", e)
        return None, ""
