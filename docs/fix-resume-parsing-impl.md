# 简历解析修复实现文档

## 问题

用户简历解析结果严重缺失：
- 技能仅提取"项目管理"1项（实际应有 PyTorch、Python、图像分割、Mamba 等）
- 项目经历只显示1个（实际应有多个）
- 实习经历完全缺失
- 证书/英语能力完全缺失

## 根因

1. **扫描版 PDF 处理错误**：VLM 直接做"图片→结构化JSON"不可靠，LLM 文本解析比 VLM 结构化更稳定
2. **无分字段补充**：主解析漏字段后无补救
3. **实习验证过严**：合法实习被误判为项目
4. **文本截断粗暴**：4000字符一刀切，丢失后半部分内容
5. **证书无兜底**：仅依赖 LLM 自觉性

## 实施步骤

### Step 1: 修改 `backend/routers/profiles.py`

**修改位置**：第191-201行，扫描版PDF处理流程

**当前代码**：
```python
    # Scanned PDF: use multimodal VL to extract profile directly (image → structured data)
    if not raw_text.strip() and filename.lower().endswith(".pdf"):
        profile_data = _extract_profile_multimodal_vl(content)
        vl_skills = profile_data.get("skills", []) if profile_data else []
        # Accept VL result only if it has a reasonable number of skills;
        # a single skill usually means the VL model missed the专业技能/tech_stack sections.
        if len(vl_skills) >= 3:
            quality_data = ProfileService.compute_quality(profile_data)
            return ok({"profile": profile_data, "quality": quality_data})
        # Fallback: OCR text → LLM
        raw_text = _ocr_pdf_with_vl(content)
```

**替换为**：
```python
    # Scanned PDF: VLM OCR → text LLM parsing (more reliable than VLM direct struct)
    # VLM is good at OCR but poor at categorizing text into skills/projects/internships.
    # Decoupling OCR and structurization gives consistent quality for scanned vs text PDFs.
    if not raw_text.strip() and filename.lower().endswith(".pdf"):
        raw_text = _ocr_pdf_with_vl(content)
        if not raw_text.strip():
            raise HTTPException(400, "无法提取简历文本，请使用文字版 PDF 或直接粘贴简历文本")
```

同时删除导入 `_extract_profile_multimodal_vl`（如果不再使用），但保留 `_ocr_pdf_with_vl`。

### Step 2: 修改 `backend/routers/_profiles_parsing.py` — 放宽实习验证

**当前代码**（第254-293行）：
```python
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
```

**替换为**：
```python
def _is_valid_internship(entry: dict) -> bool:
    """Return True if this entry is a genuine internship (not a misclassified project).

    Relaxed rules for student resumes — many student internships are at labs,
    research groups, or small companies that don't have formal org suffixes.
    """
    company = (entry.get("company") or "").strip()
    role = (entry.get("role") or "").strip()

    # Must have company; role can be empty (some resumes only list company)
    if not company:
        return False

    combined = " ".join([
        company, role,
        str(entry.get("duration") or ""),
        str(entry.get("highlights") or ""),
    ])

    # Fast path: explicit internship keyword in combined text → almost always valid
    if any(w in combined for w in _INTERNSHIP_IDENTITY_WORDS):
        return True

    # Without internship keyword, require both company and role
    if not role:
        return False

    # Company looks like a pure project title (e.g. "图书管理系统") AND no org hint → reject
    has_org = any(kw in company for kw in _ORG_ENTITY_KEYWORDS)
    has_project_title = any(kw in company for kw in _PROJECT_TITLE_KEYWORDS)
    if has_project_title and not has_org:
        return False

    # Role that ends in task-description suffix (e.g. "测试工作") → likely not a real position
    role_is_task_desc = any(role.endswith(sfx) for sfx in _TASK_DESCRIPTION_ROLE_SUFFIXES)
    if role_is_task_desc:
        return False

    return True
```

### Step 3: 添加证书正则兜底 + 分字段补充提取

**在 `backend/routers/_profiles_parsing.py` 中，`_SKILLS_RETRY_PROMPT` 之前添加以下代码**。

插入位置：大约在第796行之前（`_SKILLS_RETRY_PROMPT` 定义之前）。

```python
# ── Certificate regex fallback ───────────────────────────────────────────────

_CERTIFICATE_PATTERNS: list[tuple[str, str]] = [
    # English / Language
    (r"CET[-\s]?4", "英语（CET-4）"),
    (r"CET[-\s]?6", "英语（CET-6）"),
    (r"BEC\s*(高级|中级|初级|Higher|Vantage|Preliminary)?", "BEC商务英语"),
    (r"TOEFL", "TOEFL"),
    (r"IELTS", "IELTS"),
    (r"托福", "托福"),
    (r"雅思", "雅思"),
    (r"日语\s*N1", "日语 N1"),
    (r"日语\s*N2", "日语 N2"),
    (r"日语\s*N3", "日语 N3"),
    (r"日语\s*N4", "日语 N4"),
    (r"日语\s*N5", "日语 N5"),
    (r"韩语\s*TOPIK", "韩语 TOPIK"),
    (r"法语\s*(TEF|TCF|DELF|DALF)", r"法语 \1"),
    (r"德语\s*(TestDaF|DSH|Goethe)", r"德语 \1"),
    # Mandarin / Driver
    (r"普通话\s*(一甲|一乙|二甲|二乙|三甲|三乙)", r"普通话\1"),
    (r"机动车\s*驾驶\s*证\s*[ABC]\d", r"机动车驾驶证"),
    (r"驾驶证\s*[ABC]\d", r"机动车驾驶证"),
    (r"C1", "机动车驾驶证 C1"),
    (r"C2", "机动车驾驶证 C2"),
    # IT / Professional
    (r"软考\s*(初级|中级|高级)", r"软考\1"),
    (r"计算机\s*等级\s*(一级|二级|三级|四级)", r"NCRE \1"),
    (r"NCRE\s*[1234]", r"NCRE"),
    (r"PMP", "PMP"),
    (r"CFA", "CFA"),
    (r"ACCA", "ACCA"),
    (r"CPA", "CPA"),
    (r"一级建造师", "一级建造师"),
    (r"二级建造师", "二级建造师"),
    (r"教师资格证", "教师资格证"),
    (r"心理咨询师", "心理咨询师"),
    (r"会计从业", "会计从业资格"),
    (r"证券从业", "证券从业资格"),
    (r"基金从业", "基金从业资格"),
    (r"银行从业", "银行从业资格"),
    (r"期货从业", "期货从业资格"),
    (r"华为\s*(HCIA|HCIP|HCIE)", r"华为\1认证"),
    (r"思科\s*(CCNA|CCNP|CCIE)", r"思科\1认证"),
    (r"阿里云\s*(ACA|ACP|ACE)", r"阿里云\1认证"),
    (r"AWS\s*(CLF|SCS|DVA|SAA|SAP|DOP|DEA)", "AWS 认证"),
    (r"腾讯云\s*(TCP|TCE|TCA)", "腾讯云认证"),
    (r"Azure\s*(AZ-900|AZ-104|AZ-305)", "Azure 认证"),
]


def _extract_certificates_by_regex(raw_text: str) -> list[str]:
    """Extract common certificates from raw text using regex patterns.

    Serves as a deterministic fallback when LLM misses certificates.
    """
    import re as _re
    found: set[str] = set()
    for pattern, replacement in _CERTIFICATE_PATTERNS:
        for match in _re.finditer(pattern, raw_text, _re.IGNORECASE):
            cert = _re.sub(pattern, replacement, match.group(0), flags=_re.IGNORECASE)
            found.add(cert.strip())
    return sorted(found)


# ── Per-field supplement extraction prompts ──────────────────────────────────

_PROJECTS_RETRY_PROMPT = """从以下简历文本中提取所有项目经历，返回严格 JSON，不要其他文字。

注意：
1. 提取"项目经历"、"项目经验"、"Projects"板块中的全部内容
2. 包括课程项目、毕业设计、竞赛作品、个人项目、开源项目等
3. 每个项目用一句话或一段简短描述概括
4. 不要遗漏任何项目

返回格式：
{{"projects": ["项目1描述", "项目2描述", "项目3描述"]}}

简历文本：
{resume_text}"""


_INTERNSHIPS_RETRY_PROMPT = """从以下简历文本中提取所有实习/工作经历，返回严格 JSON，不要其他文字。

注意：
1. 提取"实习经历"、"工作经历"、"Internship"、"Work Experience"板块中的全部内容
2. 包括企业实习、兼职、校内助研、实验室实习等
3. 每个实习返回：company（公司/机构名）、role（岗位）、duration（时间）、highlights（核心成果，一句话）
4. 不要遗漏任何实习

返回格式：
{{"internships": [{{"company": "公司名", "role": "岗位", "duration": "时间", "highlights": "成果描述"}}]}}

简历文本：
{resume_text}"""


_CERTIFICATES_RETRY_PROMPT = """从以下简历文本中提取所有证书/资质，返回严格 JSON，不要其他文字。

注意：
1. 提取"证书"、"资质"、"技能证书"、"其他"等板块中的全部内容
2. 包括但不限于：CET-4/6、TOEFL、IELTS、日语 N1/N2、普通话等级、驾驶证、软考、计算机等级、PMP、华为/阿里云/AWS 认证等
3. 一字不落地提取证书名称
4. 不要按"是否与求职相关"过滤

返回格式：
{{"certificates": ["证书1", "证书2", "证书3"]}}

简历文本：
{resume_text}"""


def _supplement_missing_fields(parsed: dict, raw_text: str) -> dict:
    """After primary LLM extraction, supplement any missing fields.

    Uses focused per-field prompts to catch what the main all-in-one prompt missed.
    """
    from backend.llm import llm_chat, parse_json_response

    # 1. Skills — already has retry in _extract_profile_with_llm, skip here

    # 2. Projects — if empty or suspiciously few
    projects = parsed.get("projects", [])
    if len(projects) == 0:
        logger.warning("Primary parse returned 0 projects, running projects supplement")
        try:
            prompt = _PROJECTS_RETRY_PROMPT.format(resume_text=raw_text[:3000])
            result = llm_chat([{"role": "user", "content": prompt}], temperature=0, timeout=30)
            retry_parsed = parse_json_response(result)
            if retry_parsed and retry_parsed.get("projects"):
                parsed["projects"] = retry_parsed["projects"]
                logger.info("Projects supplement: extracted %d projects", len(retry_parsed["projects"]))
        except Exception as e:
            logger.warning("Projects supplement failed: %s", e)

    # 3. Internships — if empty
    internships = parsed.get("internships", [])
    if len(internships) == 0:
        logger.warning("Primary parse returned 0 internships, running internships supplement")
        try:
            prompt = _INTERNSHIPS_RETRY_PROMPT.format(resume_text=raw_text[:3000])
            result = llm_chat([{"role": "user", "content": prompt}], temperature=0, timeout=30)
            retry_parsed = parse_json_response(result)
            if retry_parsed and retry_parsed.get("internships"):
                # Validate each entry but with relaxed rules (already done in _is_valid_internship)
                valid = []
                for entry in retry_parsed["internships"]:
                    if isinstance(entry, dict) and entry.get("company"):
                        valid.append(entry)
                if valid:
                    parsed["internships"] = valid
                    logger.info("Internships supplement: extracted %d internships", len(valid))
        except Exception as e:
            logger.warning("Internships supplement failed: %s", e)

    # 4. Certificates — regex fallback + LLM supplement
    certificates = parsed.get("certificates", [])
    if len(certificates) == 0:
        # Regex first
        regex_certs = _extract_certificates_by_regex(raw_text)
        if regex_certs:
            parsed["certificates"] = regex_certs
            logger.info("Certificates regex fallback: found %d certs", len(regex_certs))
        # LLM supplement as second chance
        try:
            prompt = _CERTIFICATES_RETRY_PROMPT.format(resume_text=raw_text[:3000])
            result = llm_chat([{"role": "user", "content": prompt}], temperature=0, timeout=30)
            retry_parsed = parse_json_response(result)
            if retry_parsed and retry_parsed.get("certificates"):
                existing = {c.lower() for c in parsed.get("certificates", [])}
                added = 0
                for c in retry_parsed["certificates"]:
                    if c and c.lower() not in existing:
                        parsed.setdefault("certificates", []).append(c)
                        existing.add(c.lower())
                        added += 1
                if added:
                    logger.info("Certificates LLM supplement: added %d certs", added)
        except Exception as e:
            logger.warning("Certificates supplement failed: %s", e)

    return parsed
```

### Step 4: 修改 `_extract_profile_with_llm` 调用分字段补充

**当前代码**（第805-858行）：

```python
def _extract_profile_with_llm(raw_text: str) -> dict:
    try:
        from backend.llm import llm_chat, parse_json_response
        skill_vocab = _build_skill_vocab()
        prompt = _RESUME_PARSE_PROMPT.format(
            resume_text=raw_text[:4000],
            skill_vocab=skill_vocab,
        )
        result = llm_chat([{"role": "user", "content": prompt}], temperature=0)
        parsed = parse_json_response(result)

        # Retry: if primary parse failed or returned no skills, do a focused skills-only call
        if not parsed or not parsed.get("skills"):
            logger.warning("_extract_profile_with_llm: primary parse returned no skills, retrying")
            retry_prompt = _SKILLS_RETRY_PROMPT.format(
                skill_vocab=skill_vocab,
                resume_text=raw_text[:2500],
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
```

**替换为**：

```python
def _extract_profile_with_llm(raw_text: str) -> dict:
    try:
        from backend.llm import llm_chat, parse_json_response
        skill_vocab = _build_skill_vocab()

        # Smart truncation: preserve key sections, drop fluff
        truncated = _smart_truncate_resume(raw_text, max_chars=4000)

        prompt = _RESUME_PARSE_PROMPT.format(
            resume_text=truncated,
            skill_vocab=skill_vocab,
        )
        result = llm_chat([{"role": "user", "content": prompt}], temperature=0)
        parsed = parse_json_response(result)

        # Retry: if primary parse failed or returned no skills, do a focused skills-only call
        if not parsed or not parsed.get("skills"):
            logger.warning("_extract_profile_with_llm: primary parse returned no skills, retrying")
            retry_prompt = _SKILLS_RETRY_PROMPT.format(
                skill_vocab=skill_vocab,
                resume_text=raw_text[:2500],
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

        # Supplement missing fields with focused per-field extraction
        parsed = _supplement_missing_fields(parsed, raw_text)

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
```

### Step 5: 添加智能文本截断函数

**插入位置**：在 `_extract_profile_with_llm` 函数之前（大约第804行之前），添加：

```python
def _smart_truncate_resume(text: str, max_chars: int = 4000) -> str:
    """Intelligently truncate resume text, preserving key sections.

    Strategy:
    1. Identify section headers (专业技能, 项目经历, 实习经历, etc.)
    2. Always include Education + Skills + Projects + Internships
    3. Compress or drop low-value sections (自我评价, 兴趣爱好, etc.)
    4. If still over limit, truncate from the least important sections
    """
    if len(text) <= max_chars:
        return text

    import re as _re

    # Section priority: higher = more important, must keep
    section_priority = {
        "专业技能": 10, "技能": 10, "技术栈": 10, "technical skills": 10,
        "项目经历": 9, "项目经验": 9, "projects": 9, "项目": 9,
        "实习经历": 9, "实习经验": 9, "工作经历": 9, "work experience": 9, "internship": 9,
        "教育背景": 8, "教育经历": 8, "education": 8,
        "获奖情况": 7, "荣誉": 7, "竞赛": 7, "awards": 7,
        "证书": 7, "资质": 7, "certificates": 7,
        "求职意向": 6, "自我评价": 3, "兴趣爱好": 2, "个人简介": 3,
    }

    # Try to split by common section headers
    # Pattern: line starts with 2-8 Chinese chars (section header) followed by separator
    section_pattern = _re.compile(
        r'(?:^|\n)\s*([\u4e00-\u9fff\w\s]{2,15})\s*(?:[：:]|\n)',
        _re.MULTILINE | _re.IGNORECASE
    )

    # Find all potential section boundaries
    matches = list(section_pattern.finditer(text))
    if len(matches) < 3:
        # Can't reliably detect sections — fall back to simple truncation
        # But keep beginning (personal info + education) and end (projects + skills)
        head = text[:max_chars // 2]
        tail = text[-max_chars // 2:] if len(text) > max_chars else ""
        return head + "\n...\n" + tail

    # Build sections
    sections: list[tuple[str, str, int]] = []  # (header, content, priority)
    for i, match in enumerate(matches):
        header = match.group(1).strip()
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end]

        pri = 5  # default priority
        for key, p in section_priority.items():
            if key.lower() in header.lower():
                pri = p
                break
        sections.append((header, content, pri))

    # Always include pre-header text (name, contact info)
    pre_header = text[:matches[0].start()] if matches else ""

    # Sort by priority desc, then by original order
    sections.sort(key=lambda s: (-s[2], text.index(s[1])))

    # Greedily add sections by priority until we hit max_chars
    result_parts = [pre_header]
    used_chars = len(pre_header)
    used_sections: set[str] = set()

    for header, content, pri in sections:
        if header in used_sections:
            continue
        if used_chars + len(content) <= max_chars:
            result_parts.append(content)
            used_chars += len(content)
            used_sections.add(header)
        elif pri >= 9 and used_chars + len(content) > max_chars:
            # Critical section (skills/projects/internships) — truncate content to fit
            remaining = max_chars - used_chars
            if remaining > 200:
                result_parts.append(content[:remaining])
                used_sections.add(header)
            break
        else:
            # Lower priority section — skip if over limit
            continue

    # If we still have room, try to add skipped lower-priority sections
    for header, content, pri in sections:
        if header in used_sections:
            continue
        if used_chars + len(content) <= max_chars:
            result_parts.append(content)
            used_chars += len(content)
            used_sections.add(header)

    return "\n".join(result_parts)
```

### Step 6: 更新 `_extract_profile_multimodal_vl` 使其也走补充逻辑

**当前代码**：第487行附近，在 `parsed = _postprocess_profile(parsed)` 之前，添加对 `_supplement_missing_fields` 的调用。

找到这一行：
```python
        parsed = _postprocess_profile(parsed)
```

改为：
```python
        # Supplement missing fields (same treatment as text-based path)
        raw_placeholder = parsed.get("raw_text", "")
        if raw_placeholder.startswith("[multimodal_extracted]"):
            # Use the VLM raw response as pseudo-text for supplement extraction
            supplement_text = raw_placeholder.replace("[multimodal_extracted]", "").strip()
            parsed = _supplement_missing_fields(parsed, supplement_text)

        parsed = _postprocess_profile(parsed)
```

### Step 7: 验证语法

修改完成后，运行：
```bash
.venv/Scripts/python.exe -m py_compile backend/routers/_profiles_parsing.py
.venv/Scripts/python.exe -m py_compile backend/routers/profiles.py
```

### Step 8: 手动测试

```bash
.venv/Scripts/python.exe -c "
import sys
sys.path.insert(0, '.')
from backend.routers._profiles_parsing import (
    _extract_certificates_by_regex,
    _is_valid_internship,
    _smart_truncate_resume,
)

# Test 1: certificate regex
resume = '英语 CET-6 通过，普通话二甲，驾驶证 C1，软考中级'
certs = _extract_certificates_by_regex(resume)
print('Certs:', certs)

# Test 2: internship validation (relaxed)
entry = {'company': 'XX实验室', 'role': '研究助理', 'highlights': '参与CV项目'}
print('Valid (lab):', _is_valid_internship(entry))

entry2 = {'company': 'XX实验室', 'role': '实习生', 'highlights': '实习期间'}
print('Valid (intern keyword):', _is_valid_internship(entry2))

# Test 3: smart truncate
long_text = '个人信息\n张三\n\n教育背景\n硕士\n\n专业技能\nPython\n\n自我评价\n' + 'x' * 5000 + '\n\n项目经历\n项目A\n\n实习经历\n实习A'
truncated = _smart_truncate_resume(long_text, max_chars=100)
print('Truncated length:', len(truncated))
print('Has 项目:', '项目' in truncated)
print('Has 自我评价:', '自我评价' in truncated)
"
```

## 关键改动总结

| 改动 | 文件 | 作用 |
|------|------|------|
| VLM OCR 优先 | profiles.py | 扫描版PDF改为OCR+文本LLM，不再信任VLM结构化 |
| 放宽实习验证 | _profiles_parsing.py | 含"实习"关键词直接通过，降低公司名要求 |
| 证书正则兜底 | _profiles_parsing.py | CET/TOEFL/普通话/驾驶证等20+证书正则匹配 |
| 分字段补充 | _profiles_parsing.py | 主解析后，对缺失的projects/internships/certificates做专项提取 |
| 智能截断 | _profiles_parsing.py | 优先保留专业技能/项目/实习板块，压缩自我评价等 |
