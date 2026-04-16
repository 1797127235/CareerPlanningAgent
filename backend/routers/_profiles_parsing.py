"""Resume text extraction, post-processing, skill normalization, and VLM/OCR helpers."""
from __future__ import annotations

import json
import logging

from sqlalchemy.orm import Session

from backend.config import DASHSCOPE_API_KEY, LLM_BASE_URL
from backend.db_models import Profile
from backend.routers._profiles_graph import _build_skill_vocab

logger = logging.getLogger(__name__)

_RESUME_PARSE_PROMPT = """你是一个简历解析 AI。请从以下简历文本中提取结构化信息，以 JSON 格式返回。

返回格式（严格 JSON，不要加注释或 markdown）：
{{
  "name": "姓名（可选）",
  "job_target": "简历中明确写出的求职意向/目标岗位原文，如'产品经理实习'、'前端开发工程师'，无则填空字符串",
  "primary_domain": "此人最主要的技术/职能方向，从以下选一个：AI/LLM开发|后端开发|前端开发|游戏开发|数据工程|系统/基础设施|安全|算法研究|产品设计/PM|其他",
  "career_signals": {{
    "has_publication": true或false（是否有论文发表，包括在投/预印本）,
    "publication_level": "顶会（NeurIPS/ICML/CVPR/ACL/KDD/ICLR等）|CCF-A|CCF-B|CCF-C|无",
    "competition_awards": ["获奖竞赛名称，如Kaggle金牌、数学建模省一等奖"],
    "domain_specialization": "深耕的细分领域，如异常检测、推荐系统、计算机视觉等，无则填空字符串",
    "research_vs_engineering": "research（偏学术/算法创新）|engineering（偏工程落地）|balanced（均衡）",
    "open_source": true或false（是否有开源项目/贡献）,
    "internship_company_tier": "顶级大厂（字节/阿里/腾讯/华为/百度等）|中大厂|初创/中小公司|无"
  }},
  "experience_years": 工作年限数字（在校生/应届生填0）,
  "education": {{"degree": "学位", "major": "专业", "school": "学校"}},
  "skills": [
    {{"name": "技能名称", "level": "advanced|intermediate|familiar|beginner"}}
  ],
  "knowledge_areas": ["知识领域1", "知识领域2"],
  "internships": [
    {{
      "company": "公司名称",
      "role": "实习岗位名称",
      "duration": "时间范围，如2024.10-2024.12",
      "tech_stack": ["技术1", "技术2"],
      "highlights": "核心成果一句话描述，如：优化索引性能提升38%"
    }}
  ],
  "projects": ["项目描述1", "项目描述2"],
  "awards": ["竞赛/荣誉1", "竞赛/荣誉2"],
  "certificates": ["证书名称，必须 100% 完整抽取，见下方规则"]
}}

【技能命名规则（严格执行）】
技能名称必须使用简短标准名，不要加"语言/编程/系统/框架/开发"等后缀。
优先使用以下标准词表中的名称（如果简历中的技能可以对应上）：
{skill_vocab}
如果简历中的技能不在词表中，使用简短通用名称（如"多线程"而非"多线程编程"，"Linux"而非"Linux系统编程"，"C++"而非"C/C++语言"）。
【别名归一化（强制）】Unreal Engine 5/UE5 → Unreal，LangGraph/LangChain4j → LangChain，PGVector → Vector DB，SpringBoot → Spring Boot。

【字段分类规则（严格执行）】
- internships：**只放有真实"实习/兼职/校外工作"身份的在职经历**，必须同时满足：
  (a) company 是真实企业/机构名（含"公司/集团/科技/有限/股份/研究院/实验室/银行/医院/政府"等组织后缀）
  (b) role 是具体岗位名（如"后端实习生"、"产品助理"、"数据分析实习"）
  (c) 简历中有"实习"、"兼职"、"工作"、"onboarding"等词指向该经历
  ❌ 禁止将以下内容归类为 internships（即使提到了公司名）：
    - 个人项目（自己开发的系统/工具/App）
    - 课程项目、课程设计、毕业设计
    - 比赛/竞赛作品
    - 帮某公司/老师做的兼职小项目但没有"实习"身份
    - 工作室/社团/校内组织的项目
  ✅ internships 正确示例："在阿里巴巴实习6个月，负责后端开发"、"字节跳动暑期实习，担任测试工程师"
- projects：所有动手开发/实施的项目，包括：个人项目、课程项目、毕设、竞赛作品、技术调研实现；实习期间做的子项目不重复放这里
- awards：仅放竞赛获奖、荣誉证书、奖学金，如"软件测试大赛省二"、"程序设计省一"
- certificates：**一切资质证书**，必须 100% 完整抽取，不得按"是否与求职相关"过滤。包括但不限于：
  • 外语类：CET-4/6、BEC、TOEFL、IELTS、日语 N1/N2、韩语 TOPIK 等
  • 技术/职业类：软考（初级/中级/高级）、PMP、CFA、ACCA、CPA、一级/二级建造师、NCRE 计算机等级、华为/思科/阿里云/AWS 认证等
  • **普通话水平测试等级证书**：一甲、一乙、二甲、二乙、三甲、三乙（**必须收录**）
  • **机动车驾驶证**：C1、C2、C3、B1、B2、A1、A2（**必须收录**）
  • 教师资格证、心理咨询师、会计从业、证券从业等各类从业资格
  • 任何简历中"证书""资质""技能证书""其他""个人证书"等板块出现的内容，一律收录
  **禁止**：禁止把驾驶证/普通话证书因为"和求职无关"而丢弃——这是学生自我介绍的一部分，必须保留原样录入
- 竞赛名称禁止出现在 projects 中；项目名称禁止出现在 awards 中

技能等级判定规则（严格执行，宁低勿高，默认从低档开始）：
- advanced（高级）：须有以下任一硬性证据：主导开源项目/重要贡献、竞赛获奖（省级+）、≥1年该技术工作经验、发表相关论文/专利
- intermediate（中级）：在≥2个有实质规模的项目中担任主要负责人，OR有≥3个月该技术实习/工作经验，OR有省级及以上竞赛获奖
- familiar（了解）：课程项目或个人项目中实际使用过，有代码产出
- beginner（入门）：学过课程/看过教程，实践经验有限

【中文用词 → 等级上限映射（强制执行）】
简历中出现以下词汇时，对应技能的等级上限如下，不得超越：
- "了解" / "接触过" / "有所了解" → 上限 beginner
- "熟悉" / "能够使用" / "会使用" / "具备" / "理解" → 上限 familiar
- "熟练" / "掌握" / "能独立" → 上限 intermediate
- "精通" / "深度掌握" / "专精" → 上限 advanced（仍需核实硬性证据）
注意：简历对某技能使用"熟悉"，则该技能最高只能判 familiar，即使有相关项目也不得上调。

【强制约束 — 应届生/在校生（experience_years=0）】
1. 绝大多数技能应判为 familiar 或 beginner
2. intermediate 须同时满足：(a) 有实质项目证据 且 (b) 简历用词达到"熟练/掌握"级别
3. advanced 极少出现，仅限"精通"原词 + 开源/竞赛等可验证硬性成就同时存在
4. 竞赛获奖可将相关技能从 familiar 提升至 intermediate，但不能到 advanced
5. 证据不足时强制向下取一档

简历文本：
{resume_text}

只返回 JSON，不要有任何其他文字。"""

_AWARD_KEYWORDS = (
    "大赛", "竞赛", "比赛", "获奖", "奖学金", "省一", "省二", "省三",
    "国一", "国二", "国三", "一等奖", "二等奖", "三等奖", "特等奖",
    "金奖", "银奖", "铜奖", "优秀奖", "荣誉", "证书", "认证",
)

# Keywords that indicate a real company/organization entity
_ORG_ENTITY_KEYWORDS = (
    "公司", "集团", "科技", "有限", "股份", "研究院", "研究所", "实验室",
    "银行", "医院", "学院", "大学", "政府", "局", "部", "中心",
    "Ltd", "Co.", "Inc.", "Corp", "Technology", "Tech",
)

# Keywords that suggest the name is a project title, not a company
_PROJECT_TITLE_KEYWORDS = (
    "项目", "系统", "平台", "工程", "模块", "框架", "工具", "脚本",
    "App", "应用", "网站", "小程序", "后台", "前台", "管理后台",
)

# Internship identity words that should appear in the full entry text
_INTERNSHIP_IDENTITY_WORDS = (
    "实习", "兼职", "intern", "internship",
)

# Role suffixes / patterns that indicate a real job title
_VALID_ROLE_SUFFIXES = (
    "工程师", "实习生", "助理", "分析师", "经理", "专员",
    "开发者", "架构师", "设计师", "运营", "产品", "研发",
    "engineer", "intern", "analyst", "manager", "developer",
)

# Role patterns that are task descriptions, NOT job titles
_TASK_DESCRIPTION_ROLE_SUFFIXES = (
    "工作",   # "测试工作", "开发工作" — describes the type of work, not the position
    "任务",
)


# ── Skill alias normalization ─────────────────────────────────────────────────
# Maps common resume variants → canonical graph vocab names (lowercase key)
_SKILL_ALIASES: dict[str, str] = {
    # Game engine
    "unreal engine 5": "Unreal", "unreal engine 4": "Unreal",
    "ue5": "Unreal", "ue4": "Unreal", "unreal engine": "Unreal",
    "unity3d": "Unity",
    # Spring / Java
    "springboot": "Spring Boot", "spring-boot": "Spring Boot",
    "spring boot framework": "Spring Boot",
    "mybatisplus": "MyBatis", "mybatis-plus": "MyBatis",
    # LangChain ecosystem
    "langgraph": "LangChain", "langchain4j": "LangChain",
    "langserve": "LangChain", "langchain/langgraph": "LangChain",
    # Vector DBs
    "pgvector": "Vector DB", "pinecone": "Vector DB",
    "weaviate": "Vector DB", "chroma": "Vector DB",
    "milvus": "Vector DB", "qdrant": "Vector DB",
    # LLM APIs
    "openai api": "OpenAI API", "chatgpt api": "OpenAI API",
    "gpt-4": "OpenAI API", "gpt4": "OpenAI API",
    "dashscope": "OpenAI API",
    # Frontend
    "react.js": "React", "reactjs": "React",
    "vue.js": "Vue.js", "vuejs": "Vue.js",
    "nextjs": "Next.js",
    "nodejs": "Node.js",
    # DB
    "postgresql": "PostgreSQL", "postgres": "PostgreSQL",
    # K8s
    "k8s": "Kubernetes",
    # PyTorch / TF
    "pytorch": "PyTorch", "tensorflow": "TensorFlow",
}


def _normalize_skill_name(name: str) -> str:
    return _SKILL_ALIASES.get(name.lower().strip(), name)


def _normalize_skills(skills: list) -> list:
    """Normalize each skill's name using the alias map."""
    result = []
    for s in skills:
        if isinstance(s, dict):
            result.append({**s, "name": _normalize_skill_name(s.get("name", ""))})
        else:
            result.append(s)
    return result


def _is_valid_internship(entry: dict) -> bool:
    """Return True only if this entry is a genuine internship (not a misclassified project).

    Rules (ALL must pass):
    1. Must have non-empty company AND role.
    2. company must not look like a project title (project-title keyword without org-entity keyword).
    3. role must look like a job title (has valid role suffix OR has internship identity word).
    4. combined text must suggest employment relationship — at least one internship signal OR
       a valid job title pattern.
    """
    company = (entry.get("company") or "").strip()
    role = (entry.get("role") or "").strip()

    # Rule 1: must have both fields
    if not company or not role:
        return False

    combined = " ".join([
        company, role,
        str(entry.get("duration") or ""),
        str(entry.get("highlights") or ""),
    ])

    # Rule 2: company looks like a project title AND has no org-entity keyword → reject
    has_org = any(kw in company for kw in _ORG_ENTITY_KEYWORDS)
    has_project_title = any(kw in company for kw in _PROJECT_TITLE_KEYWORDS)
    if has_project_title and not has_org:
        # Last-chance: explicit internship word saves it
        if any(w in combined for w in _INTERNSHIP_IDENTITY_WORDS):
            return True
        return False

    # Rule 3: role that ends in a task-description suffix → reject unless explicit internship word
    role_is_task_desc = any(role.endswith(sfx) for sfx in _TASK_DESCRIPTION_ROLE_SUFFIXES)
    if role_is_task_desc:
        if any(w in combined for w in _INTERNSHIP_IDENTITY_WORDS):
            return True
        return False

    return True


def _internship_to_project_str(entry: dict) -> str:
    """Convert a misclassified internship entry back to a project description string."""
    parts = []
    company = (entry.get("company") or "").strip()
    role = (entry.get("role") or "").strip()
    if company:
        parts.append(company)
    if role and role != company:
        parts.append(f"（{role}）")
    highlights = (entry.get("highlights") or "").strip()
    if highlights:
        parts.append(f"：{highlights}")
    tech = entry.get("tech_stack") or []
    if isinstance(tech, list) and tech:
        parts.append(f"技术栈：{', '.join(str(t) for t in tech)}")
    return "".join(parts) or str(entry)


def _postprocess_profile(parsed: dict) -> dict:
    projects: list = parsed.get("projects", [])
    awards: list = parsed.get("awards", [])

    # Move award-like items from projects → awards
    clean_projects = []
    for item in projects:
        text = str(item)
        if any(kw in text for kw in _AWARD_KEYWORDS):
            if text not in awards:
                awards.append(text)
        else:
            clean_projects.append(item)
    parsed["projects"] = clean_projects
    parsed["awards"] = awards

    # Validate internships — move misclassified entries back to projects
    raw_internships = parsed.get("internships", [])
    valid_internships = []
    for entry in raw_internships:
        if not isinstance(entry, dict):
            continue
        if _is_valid_internship(entry):
            valid_internships.append(entry)
        else:
            # Demote to project string
            proj_str = _internship_to_project_str(entry)
            if proj_str and proj_str not in parsed["projects"]:
                parsed["projects"].append(proj_str)
            logger.info("Demoted internship→project: company=%s role=%s",
                        entry.get("company"), entry.get("role"))
    parsed["internships"] = valid_internships

    return parsed


def _vlm_supplement_certificates(content: bytes) -> list[str]:
    """Secondary VLM call dedicated to extracting certificates.

    Why a separate call: qwen-vl-plus often subjectively filters out items like
    "普通话二级乙等" or "机动车驾驶证C2" during JSON extraction even when the main
    prompt says "100% include" — too many instructions dilute attention.

    This isolated single-task call gets much higher compliance.
    Returns raw list of certificate strings (may be empty on failure).
    """
    try:
        import base64
        import io as _io
        import fitz  # pymupdf
        import openai
        from backend.llm import parse_json_response

        if not DASHSCOPE_API_KEY:
            return []

        doc = fitz.open(stream=_io.BytesIO(content), filetype="pdf")
        content_parts: list[dict] = []
        for page_num in range(min(len(doc), 3)):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=150)
            img_b64 = base64.b64encode(pix.tobytes("png")).decode()
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"},
            })

        # Single-task prompt: much higher instruction compliance than multi-field JSON
        prompt_text = (
            "请识别图像中的简历，找出所有「证书 / 资质 / 技能证书 / 其他」板块里的**全部内容**，"
            "一字不落地原样列出。\n"
            "必须收录（不得按相关性过滤）：\n"
            "- 外语证书：CET-4/6、BEC、TOEFL、IELTS、日语 N1/N2、韩语 TOPIK 等\n"
            "- 普通话水平测试：一甲、一乙、二甲、二乙、三甲、三乙\n"
            "- 机动车驾驶证：C1、C2、C3、B1、B2、A1、A2\n"
            "- 计算机等级 / 软考 / PMP / 云厂商认证\n"
            "- 教师资格证、会计/证券/心理从业证\n"
            "- 任何出现在证书板块的内容\n\n"
            '返回严格 JSON 数组，如：["英语（CET-4）", "普通话二级乙等", "机动车驾驶证C2"]\n'
            "只返回 JSON 数组，不要任何解释。找不到则返回 []。"
        )
        content_parts.append({"type": "text", "text": prompt_text})

        client = openai.OpenAI(api_key=DASHSCOPE_API_KEY, base_url=LLM_BASE_URL)
        resp = client.chat.completions.create(
            model="qwen-vl-plus",
            messages=[{"role": "user", "content": content_parts}],
            max_tokens=500,
        )
        raw = resp.choices[0].message.content or ""
        parsed = parse_json_response(raw)
        if isinstance(parsed, list):
            return [str(c).strip() for c in parsed if c and str(c).strip()]
        return []
    except Exception as e:
        logger.warning("VLM certificate supplement failed: %s", e)
        return []


def _extract_profile_multimodal_vl(content: bytes) -> dict:
    """Directly extract structured profile from scanned PDF pages using qwen-vl-plus.

    Skips the OCR→text intermediate step. Sends each page image + resume parse prompt
    to the vision model and returns a structured profile dict.
    """
    try:
        import base64
        import io as _io
        import fitz  # pymupdf
        import openai
        from backend.llm import parse_json_response

        if not DASHSCOPE_API_KEY:
            logger.warning("No DASHSCOPE_API_KEY for multimodal profile extraction")
            return {}

        doc = fitz.open(stream=_io.BytesIO(content), filetype="pdf")
        skill_vocab = _build_skill_vocab()

        # Build message content: all page images + extraction prompt
        content_parts: list[dict] = []
        for page_num in range(min(len(doc), 3)):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=150)
            img_b64 = base64.b64encode(pix.tobytes("png")).decode()
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"},
            })

        # CRITICAL: use .format() (NOT .replace()) so {{...}} double-braces
        # are correctly converted to {..} in the JSON template shown to the LLM.
        # Using .replace() leaves double-braces intact, confusing the model.
        prompt_text = _RESUME_PARSE_PROMPT.format(
            resume_text="[见上方简历图片，请仔细识别图片中的所有文字并按要求提取结构化信息]",
            skill_vocab=skill_vocab,
        )
        content_parts.append({"type": "text", "text": prompt_text})

        client = openai.OpenAI(api_key=DASHSCOPE_API_KEY, base_url=LLM_BASE_URL)
        resp = client.chat.completions.create(
            model="qwen-vl-plus",
            messages=[{"role": "user", "content": content_parts}],
            max_tokens=3000,
        )
        raw_result = resp.choices[0].message.content or ""
        parsed = parse_json_response(raw_result)
        if not parsed or not isinstance(parsed, dict):
            logger.warning("Multimodal VL profile extraction: invalid JSON response")
            return {}

        parsed.setdefault("skills", [])
        parsed.setdefault("knowledge_areas", [])
        parsed.setdefault("experience_years", 0)
        parsed.setdefault("projects", [])
        parsed.setdefault("awards", [])
        parsed.setdefault("internships", [])
        parsed.setdefault("certificates", [])

        # Double-insurance: VLM tends to subjectively drop items like 普通话/驾驶证 from
        # the main JSON call. Run a dedicated single-task cert extraction and merge.
        supplemental_certs = _vlm_supplement_certificates(content)
        if supplemental_certs:
            existing_norm = {str(c).strip().lower() for c in parsed.get("certificates", [])}
            for c in supplemental_certs:
                if c.strip().lower() not in existing_norm:
                    parsed["certificates"].append(c)
                    existing_norm.add(c.strip().lower())
            logger.info("Certificate supplement merged: %d total after merge", len(parsed["certificates"]))

        parsed = _postprocess_profile(parsed)
        parsed["soft_skills"] = {
            "_version": 2,
            "communication": None, "learning": None, "collaboration": None,
            "innovation": None, "resilience": None,
        }
        # Store a raw_text placeholder so hasProfile check and reparse work.
        # We use the LLM's raw response as a text record.
        if not parsed.get("raw_text"):
            parsed["raw_text"] = f"[multimodal_extracted] {raw_result[:3000]}"
        logger.info(
            "Multimodal VL extraction: %d skills, %d projects, job_target=%s",
            len(parsed.get("skills", [])), len(parsed.get("projects", [])),
            parsed.get("job_target", ""),
        )
        return parsed
    except Exception as e:
        logger.warning("Multimodal VL profile extraction failed: %s", e)
        return {}


def _ocr_pdf_with_vl(content: bytes) -> str:
    """OCR fallback for scanned PDFs using qwen-vl-plus vision API.
    Used as last resort when _extract_profile_multimodal_vl also fails.
    """
    try:
        import base64
        import io as _io
        import fitz  # pymupdf
        import openai

        if not DASHSCOPE_API_KEY:
            return ""

        doc = fitz.open(stream=_io.BytesIO(content), filetype="pdf")
        texts: list[str] = []
        client = openai.OpenAI(api_key=DASHSCOPE_API_KEY, base_url=LLM_BASE_URL)

        for page_num in range(min(len(doc), 3)):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=150)
            img_b64 = base64.b64encode(pix.tobytes("png")).decode()
            resp = client.chat.completions.create(
                model="qwen-vl-plus",
                messages=[{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                    {"type": "text", "text": "请识别并提取这张简历图片中的所有文字内容，保持原始格式，不要添加额外说明。"},
                ]}],
                max_tokens=2000,
            )
            page_text = resp.choices[0].message.content or ""
            if page_text.strip():
                texts.append(page_text)

        return "\n\n".join(texts)
    except Exception as e:
        logger.warning("OCR fallback failed: %s", e)
        return ""


_SKILLS_RETRY_PROMPT = """从以下简历文本中只提取技能列表，返回严格 JSON，不要其他文字：
{{"skills": [{{"name": "技能名（英文或通用短名）", "level": "familiar"}}]}}

优先使用词表中的名称：{skill_vocab}
简历：{resume_text}"""


def _extract_profile_with_llm(raw_text: str) -> dict:
    try:
        from backend.llm import llm_chat, parse_json_response
        skill_vocab = _build_skill_vocab()
        prompt = _RESUME_PARSE_PROMPT.format(
            resume_text=raw_text[:2500],
            skill_vocab=skill_vocab,
        )
        result = llm_chat([{"role": "user", "content": prompt}], temperature=0)
        parsed = parse_json_response(result)

        # Retry: if primary parse failed or returned no skills, do a focused skills-only call
        if not parsed or not parsed.get("skills"):
            logger.warning("_extract_profile_with_llm: primary parse returned no skills, retrying")
            retry_prompt = _SKILLS_RETRY_PROMPT.format(
                skill_vocab=skill_vocab,
                resume_text=raw_text[:1500],
            )
            retry_result = llm_chat([{"role": "user", "content": retry_prompt}], temperature=0)
            retry_parsed = parse_json_response(retry_result)
            if retry_parsed and retry_parsed.get("skills"):
                if not parsed:
                    parsed = {}
                parsed["skills"] = retry_parsed["skills"]

        if not parsed:
            parsed = {}
        # Normalize skill names using alias map
        parsed["skills"] = _normalize_skills(parsed.get("skills", []))
        parsed.setdefault("knowledge_areas", [])
        parsed.setdefault("experience_years", 0)
        parsed.setdefault("projects", [])
        parsed.setdefault("awards", [])
        parsed.setdefault("internships", [])
        parsed.setdefault("certificates", [])
        parsed = _postprocess_profile(parsed)
        parsed["raw_text"] = raw_text[:6000]
        parsed["soft_skills"] = {
            "_version": 2,
            "communication": None,
            "learning": None,
            "collaboration": None,
            "innovation": None,
            "resilience": None,
        }
        return parsed
    except Exception as e:
        logger.exception("_extract_profile_with_llm failed: %s", e)
        return {
            "skills": [],
            "knowledge_areas": [],
            "experience_years": 0,
            "raw_text": raw_text[:6000],
        }


def _lazy_fix_misclassified_internships(profile: Profile, db: Session) -> bool:
    """One-time lazy migration: move misclassified internship entries back to projects.

    Returns True if any fix was applied (so caller can commit).
    """
    try:
        data = json.loads(profile.profile_json or "{}")
        raw_internships = data.get("internships", [])
        valid_interns = []
        rescued_projects = list(data.get("projects", []))
        changed = False
        for entry in raw_internships:
            if not isinstance(entry, dict):
                valid_interns.append(entry)
                continue
            if _is_valid_internship(entry):
                valid_interns.append(entry)
            else:
                proj_str = _internship_to_project_str(entry)
                if proj_str and proj_str not in rescued_projects:
                    rescued_projects.append(proj_str)
                changed = True
                logger.info(
                    "Lazy-fix: demoted internship→project profile_id=%s company=%s",
                    profile.id, entry.get("company"),
                )
        if changed:
            data["internships"] = valid_interns
            data["projects"] = rescued_projects
            profile.profile_json = json.dumps(data, ensure_ascii=False)
            db.add(profile)
            db.commit()
        return changed
    except Exception as e:
        logger.warning("Lazy internship fix failed for profile %s: %s", profile.id, e)
        return False
