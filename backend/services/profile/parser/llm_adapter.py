"""LLM-driven adapter: converts ResumeSDK raw JSON (+ raw text) into standard ProfileData.

Zero hard-coded keywords — all mapping, filtering, and inference are done by the LLM.
"""
from __future__ import annotations

import json
import logging

from backend.llm import llm_chat, parse_json_response
from backend.services.profile.parser.schema import ProfileData

logger = logging.getLogger(__name__)

# Use a fast/cheap model for the adapter; this is a structured extraction task
_MODEL = "qwen-plus"
_TIMEOUT = 45


_ADAPT_PROMPT = """你是一位简历解析专家。请根据 ResumeSDK 的原始解析结果 + 简历原始文本，生成标准的用户画像 JSON。

【输入 1: ResumeSDK 原始输出】
ResumeSDK 是一个第三方简历解析服务，其输出字段名可能不标准。请根据语义理解每个字段的含义。
常见字段映射参考：
- basic_info → 姓名、年龄、性别等基本信息
- contact → 联系方式（电话、邮箱）
- expect_job → 求职意向/期望职位
- education → 教育背景（学校、专业、学位）
- skills → 技能列表（可能有 skill_name / skill_level 字段）
- work_experience → 工作经历/实习经历
- project_experience → 项目经历
- certificate → 证书
- award → 获奖/荣誉

注意：ResumeSDK 有时会把一个项目拆成多个管理子章节（如"实验论证""质量控制""迭代过程"等），
这些不是真实项目，请过滤掉。真实项目应该有具体的技术实现内容。

ResumeSDK 原始 JSON：
```json
{rs_json}
```

【输入 2: 简历原始文本】
原始文本用于补充 ResumeSDK 遗漏的信息，以及校验 ResumeSDK 的解析结果。

{raw_text}

【输出格式】严格 JSON，不要任何其他文字：
{{
  "name": "姓名",
  "job_target": "求职意向原文，如果没有明确写则填空字符串",
  "primary_domain": "最主要的技术方向，从以下选一个：AI/LLM开发|后端开发|前端开发|游戏开发|数据工程|系统/基础设施|安全|算法研究|嵌入式开发|产品设计/PM|其他",
  "career_signals": {{
    "has_publication": false,
    "publication_level": "无",
    "competition_awards": [],
    "domain_specialization": "",
    "research_vs_engineering": "balanced",
    "open_source": false,
    "internship_company_tier": "无"
  }},
  "experience_years": 0,
  "education": {{"degree": "", "major": "", "school": "", "graduation_year": null}},
  "skills": [{{"name": "技能名", "level": "familiar"}}],
  "knowledge_areas": ["知识领域1", "知识领域2"],
  "internships": [{{"company": "", "role": "", "duration": "", "tech_stack": [], "highlights": ""}}],
  "projects": ["项目描述1", "项目描述2"],
  "awards": ["获奖1"],
  "certificates": ["证书1"]
}}

【关键规则】
1. 项目过滤：只保留有真实技术内容的项目。管理子章节（如"实验论证""质量控制""迭代过程"）不是项目，必须丢弃。
2. 技能提取：必须完整提取所有技术技能，包括但不限于编程语言、框架、工具、算法、协议等。使用简短标准名。
3. 技能等级：宁低勿高。advanced 需硬性证据（开源贡献/竞赛获奖/工作经验）；intermediate 需项目证据；familiar 是课程/项目用过；beginner 是学过但实践少。
4. 子技能继承：若 C++ 判为 intermediate，则 STL、智能指针、RAII、右值引用、移动语义等至少也是 intermediate。
5. 技能粒度控制（严格执行）：
   - 不要提取编程语言的标准版本作为独立技能（如 C++11、C++14、C++17、Java 8、Python 3）
   - 不要提取标准库的子组件作为独立技能（如 vector、map、set、list、unordered_map）
   - 不要提取语法特性作为独立技能（如 右值引用、移动语义、lambda、auto、constexpr）
   - 这些细分内容应归并到父级技能：C++11→C++，Vector→STL，Lambda→C++
   - 例外：如果某子技能在简历中被强调为核心能力（如"精通 STL 底层实现"），可保留为 STL
6. 证书：不要遗漏任何证书，包括 CET-4/6、驾驶证、普通话等级、软考等。不要按"与求职相关"过滤。
7. 知识领域：根据技能深度和项目方向推断，如"Linux系统编程""网络编程""C++系统开发""数据库"等。不要只写"编程开发"。
8. internships：只放有真实企业实习身份的经历，个人项目/课程设计不要放这里。
"""


def adapt_resumesdk_to_profile(rs_raw_json: dict, raw_text: str) -> ProfileData | None:
    """Use LLM to convert ResumeSDK raw JSON + raw text into a standard ProfileData.

    This replaces all hard-coded mapping logic (_map_skills, _map_projects,
    _infer_primary_domain, etc.) with a single LLM call.
    """
    if not rs_raw_json:
        return None

    # Truncate inputs to avoid token overflow
    rs_json_str = json.dumps(rs_raw_json, ensure_ascii=False, default=str)[:8000]
    raw_text_truncated = raw_text[:4000]

    prompt = _ADAPT_PROMPT.format(rs_json=rs_json_str, raw_text=raw_text_truncated)

    try:
        result = llm_chat(
            messages=[{"role": "user", "content": prompt}],
            model=_MODEL,
            temperature=0,
            timeout=_TIMEOUT,
        )
        parsed = parse_json_response(result)
        if not parsed or not isinstance(parsed, dict):
            logger.warning("LLM adapter returned non-dict: %s", type(parsed).__name__)
            return None

        profile = ProfileData.model_validate(parsed)
        logger.info(
            "LLM adapter success: %d skills, %d projects, %d internships, domain=%r",
            len(profile.skills),
            len(profile.projects),
            len(profile.internships),
            profile.primary_domain,
        )
        return profile

    except Exception as e:
        logger.warning("LLM adapter failed: %s", e)
        return None
