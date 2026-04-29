"""backend2/services/opportunity/evaluator.py — Profile vs JD 匹配评估。

约束：
- 不读数据库
- 不访问 graph / history / report / coach / application
- 不修改任何状态
- 允许调用 LLM（无状态副作用）
- 先计算本地 evidence，再调用 LLM
- 只接收 ProfileData + JDExtract，返回 JDDiagnosisResult
"""
from __future__ import annotations

import json
import logging

from backend2.llm.client import llm_chat, parse_json_response
from backend2.schemas.opportunity import JDExtract, JDDiagnosisResult
from backend2.schemas.profile import ProfileData
from backend2.services.opportunity.evidence import build_skill_evidence
from backend2.services.opportunity.prompts import build_jd_evaluator_messages

logger = logging.getLogger(__name__)


def evaluate(profile: ProfileData, jd: JDExtract) -> JDDiagnosisResult:
    """评估用户画像与 JD 的匹配度。

    流程：
    1. 本地计算技能匹配证据
    2. 调用 LLM 进行深度匹配分析（evidence 作为输入参考）
    3. 返回结构化诊断结果

    LLM 失败时返回默认空结果（match_score=0）。
    """
    # 1. 本地 evidence
    evidence = build_skill_evidence(profile, jd)
    evidence_json = json.dumps(evidence, ensure_ascii=False, indent=2)

    # 2. 准备 LLM 输入
    profile_json = json.dumps(profile.model_dump(mode="json"), ensure_ascii=False)
    jd_extract_json = json.dumps(jd.model_dump(mode="json"), ensure_ascii=False)

    messages = build_jd_evaluator_messages(profile_json, jd_extract_json, evidence_json)

    # 3. 调用 LLM
    try:
        raw = llm_chat(messages, temperature=0.5, timeout=90)
    except Exception:
        logger.exception("Evaluator LLM 调用失败")
        return JDDiagnosisResult()

    if not raw:
        logger.warning("Evaluator LLM 返回空")
        return JDDiagnosisResult()

    # 4. 解析 JSON
    try:
        data = parse_json_response(raw)
    except Exception:
        logger.exception("Evaluator JSON 解析失败")
        return JDDiagnosisResult()

    if not data:
        logger.warning("Evaluator 无法从 LLM 响应解析 JSON")
        return JDDiagnosisResult()

    # 5. 校验
    try:
        return JDDiagnosisResult.model_validate(data)
    except Exception as exc:
        logger.warning("Evaluator 校验失败: %s", exc)
        return JDDiagnosisResult()
