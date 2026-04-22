"""VLM / OCR helpers for resume parsing."""
from __future__ import annotations

import base64
import io as _io
import json
import logging


from backend.config import DASHSCOPE_API_KEY, LLM_BASE_URL
from backend.llm import parse_json_response

logger = logging.getLogger(__name__)

def _vlm_supplement_certificates(content: bytes) -> list[str]:
    """Secondary VLM call dedicated to extracting certificates.

    Why a separate call: qwen-vl-ocr often subjectively filters out items like
    "普通话二级乙等" or "机动车驾驶证C2" during JSON extraction even when the main
    prompt says "100% include" — too many instructions dilute attention.

    This isolated single-task call gets much higher compliance.
    Returns raw list of certificate strings (may be empty on failure).
    """
    try:
        import base64
        import io as _io
        import fitz  # pymupdf
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
            model="qwen-vl-ocr",
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
    """Directly extract structured profile from scanned PDF pages using qwen-vl-ocr.

    Skips the OCR→text intermediate step. Sends each page image + resume parse prompt
    to the vision model and returns a structured profile dict.
    """
    try:
        import base64
        import io as _io
        import fitz  # pymupdf
        from backend.llm import parse_json_response

        if not DASHSCOPE_API_KEY:
            logger.warning("No DASHSCOPE_API_KEY for multimodal profile extraction")
            return {}

        doc = fitz.open(stream=_io.BytesIO(content), filetype="pdf")
        from backend.routers._profiles_graph import _build_skill_vocab
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
            model="qwen-vl-ocr",
            messages=[{"role": "user", "content": content_parts}],
            max_tokens=3000,
        )
        raw_result = resp.choices[0].message.content or ""
        parsed = parse_json_response(raw_result)
        if not parsed or not isinstance(parsed, dict):
            logger.warning("Multimodal VL profile extraction: invalid JSON response")
            return {}

        parsed.setdefault("skills", [])
        if not isinstance(parsed.get("skills"), list):
            parsed["skills"] = [parsed["skills"]] if parsed["skills"] else []
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

        # Supplement missing fields (same treatment as text-based path)
        raw_placeholder = parsed.get("raw_text", "")
        if raw_placeholder.startswith("[multimodal_extracted]"):
            # Use the VLM raw response as pseudo-text for supplement extraction
            supplement_text = raw_placeholder.replace("[multimodal_extracted]", "").strip()
            parsed = _supplement_missing_fields(parsed, supplement_text)

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


def _ocr_single_page(page_idx: int, img_b64: str, client) -> tuple[int, str]:
    """OCR a single page. Returns (page_idx, text) to preserve order."""
    try:
        resp = client.chat.completions.create(
            model="qwen-vl-ocr",
            messages=[{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                {"type": "text", "text": (
                    "请识别这张简历图片中的所有文字。\n"
                    "要求：\n"
                    "1. 保持原始排版结构，用空行分隔不同板块\n"
                    "2. 板块标题（如'专业技能''项目经历''实习经历'）单独一行\n"
                    "3. 列表项保持缩进或用'•'标记\n"
                    "4. 不要添加任何解释，只输出识别的文字\n"
                    "5. 如果某些文字模糊无法识别，用[模糊]标记，不要猜测\n"
                    "6. 特别注意：简历顶部（姓名、联系方式附近）常常有'求职意向''期望职位''意向岗位'等简短信息，必须完整识别并保留，不要遗漏"
                )},
            ]}],
            max_tokens=4000,
        )
        content = resp.choices[0].message.content or ""
        if resp.choices[0].finish_reason == "length":
            logger.warning("OCR page %d output truncated by max_tokens", page_idx)
        return page_idx, content
    except Exception as e:
        logger.warning("OCR page %d failed: %s", page_idx, e)
        return page_idx, ""


def _ocr_pdf_with_vl(content: bytes) -> str:
    """OCR for scanned PDFs using qwen-vl-ocr vision API.

    Parallelized: all pages OCR'd concurrently, cutting total time ~3x.
    """
    try:
        import base64
        import io as _io
        import fitz  # pymupdf
        from concurrent.futures import ThreadPoolExecutor

        if not DASHSCOPE_API_KEY:
            return ""

        with fitz.open(stream=_io.BytesIO(content), filetype="pdf") as doc:
            if len(doc) > 5:
                logger.warning("OCR truncating %d-page PDF to 5 pages", len(doc))
            max_pages = min(len(doc), 5)

            # Pre-render all page images
            page_images: list[tuple[int, str]] = []
            for page_num in range(max_pages):
                page = doc[page_num]
                pix = page.get_pixmap(dpi=300)
                img_b64 = base64.b64encode(pix.tobytes("png")).decode()
                page_images.append((page_num, img_b64))

        # Parallel OCR across all pages
        client = openai.OpenAI(api_key=DASHSCOPE_API_KEY, base_url=LLM_BASE_URL, timeout=60)
        results: list[tuple[int, str]] = []
        with ThreadPoolExecutor(max_workers=max_pages) as executor:
            futures = [
                executor.submit(_ocr_single_page, idx, b64, client)
                for idx, b64 in page_images
            ]
            for f in futures:
                results.append(f.result())

        # Sort by page index to preserve order
        results.sort(key=lambda x: x[0])
        texts = [text for _, text in results if text.strip()]

        raw_text = "\n\n".join(texts)
        raw_text = _clean_ocr_text(raw_text)

        # ── Secondary extraction: if no job_target signal found, do targeted OCR on page 1 header
        if texts and not _has_job_target_signal(raw_text):
            logger.info("Primary OCR missed job_target signal, running targeted header extraction")
            header_text = _ocr_header_for_job_target(page_images[0][1], client)
            if header_text:
                raw_text = header_text + "\n\n" + raw_text
                logger.info("Header extraction appended: %r", header_text[:120])

        return raw_text
    except Exception as e:
        logger.warning("OCR fallback failed: %s", e)
        return ""


def _has_job_target_signal(text: str) -> bool:
    """Quick check if OCR text already contains job-target related keywords."""
    import re as _re
    if not text:
        return False
    return bool(_re.search(r'(?:求职意向|期望职位|目标职位|应聘职位|意向岗位|期望岗位)', text, _re.IGNORECASE))


def _ocr_header_for_job_target(img_b64: str, client) -> str:
    """Targeted OCR on page 1 header area to catch job_target that primary OCR missed."""
    try:
        resp = client.chat.completions.create(
            model="qwen-vl-ocr",
            messages=[{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                {"type": "text", "text": (
                    "请仔细识别这张简历图片顶部区域（姓名、联系方式附近）的文字。\n"
                    "特别注意提取以下信息，不要遗漏任何一个字：\n"
                    "- 求职意向 / 期望职位 / 目标职位 / 意向岗位 / 应聘职位\n"
                    "- 意向城市 / 工作地点\n"
                    "- 到岗时间\n"
                    "只输出识别到的文字，不要解释。"
                )},
            ]}],
            max_tokens=500,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        logger.warning("Header targeted OCR failed: %s", e)
        return ""


def _clean_ocr_text(text: str) -> str:
    """Clean common OCR artifacts from scanned document text."""
    import re as _re

    # 1. Fix mixed-width punctuation — only between Chinese characters to avoid
    # corrupting URLs, code, version numbers, English text.
    text = _re.sub(r'(?<=[\u4e00-\u9fff]),(?=[\u4e00-\u9fff])', '，', text)
    text = _re.sub(r'(?<=[\u4e00-\u9fff])\.(?=[\u4e00-\u9fff])', '。', text)
    text = _re.sub(r'(?<=[\u4e00-\u9fff]);(?=[\u4e00-\u9fff])', '；', text)
    text = _re.sub(r'(?<=[\u4e00-\u9fff]):(?=[\u4e00-\u9fff])', '：', text)
    text = _re.sub(r'(?<=[\u4e00-\u9fff])\((?=[\u4e00-\u9fff])', '（', text)
    text = _re.sub(r'(?<=[\u4e00-\u9fff])\)(?=[\u4e00-\u9fff])', '）', text)
    text = _re.sub(r'(?<=[\u4e00-\u9fff])\[(?=[\u4e00-\u9fff])', '［', text)
    text = _re.sub(r'(?<=[\u4e00-\u9fff])\](?=[\u4e00-\u9fff])', '］', text)

    # 2. Remove spurious spaces in Chinese text
    # e.g. "图 像 分 割" -> "图像分割"
    text = _re.sub(r'(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])', '', text)

    # 3. Fix common OCR confusions
    replacements = {
        "P y T o r c h": "PyTorch",
        "P y t h o n": "Python",
        "T e n s o r F l o w": "TensorFlow",
        "深 度 学 习": "深度学习",
        "图 像 分 割": "图像分割",
        "计 算 机 视 觉": "计算机视觉",
        "项 目 管 理": "项目管理",
    }
    for wrong, correct in replacements.items():
        text = text.replace(wrong, correct)

    # 4. Normalize section headers (ensure they stand out)
    section_headers = [
        "个人信息", "基本信息", "教育背景", "教育经历",
        "专业技能", "技能", "技术栈", "个人技能",
        "项目经历", "项目经验", "项目", "Projects",
        "实习经历", "实习经验", "工作经历", "工作经历",
        "获奖情况", "荣誉", "竞赛", "获奖",
        "证书", "资质", "资格证书", "技能证书",
        "自我评价", "个人评价", "兴趣爱好",
        "求职意向", "期望职位", "意向岗位",
    ]
    for header in section_headers:
        # Ensure section headers are on their own line (match as whole words only)
        pattern = _re.compile(r'(?<!\n)(?<!\w)(' + _re.escape(header) + r')(?!\w)(?!\n)')
        text = pattern.sub(r'\n\1\n', text)

    # 5. Remove excessive blank lines
    text = _re.sub(r'\n{3,}', '\n\n', text)

    # 6. Remove [模糊] markers that appear mid-word (VLM uncertainty markers)
    text = text.replace("[模糊]", "")

    return text.strip()
