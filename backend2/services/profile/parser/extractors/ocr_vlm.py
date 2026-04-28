"""扫描件 PDF OCR 提取器 — 使用 qwen-vl-ocr 视觉模型。

本提取器注册在 PdfTextExtractor 之后，仅在 pdfplumber 返回空文本时触发。
多页 PDF 并行 OCR，自动修复中英标点和常见识别错误。
"""
from __future__ import annotations

import base64
import io
import logging
from concurrent.futures import ThreadPoolExecutor

from backend2.core.config import DASHSCOPE_API_KEY, LLM_BASE_URL
from backend2.schemas.profile import ResumeDocument
from backend2.services.profile.parser.base import TextExtractor

logger = logging.getLogger(__name__)


class OcrVlmExtractor(TextExtractor):
    """使用视觉语言模型对扫描件 PDF 进行 OCR。

    注册顺序必须在 PdfTextExtractor 之后，以保证只处理扫描件。
    """

    name = "qwen-vl-ocr"

    def supports(self, filename: str, content_type: str | None) -> bool:
        return filename.lower().endswith(".pdf")

    def extract(self, file_bytes: bytes, filename: str) -> ResumeDocument | None:
        if not DASHSCOPE_API_KEY:
            logger.warning("DASHSCOPE_API_KEY 未设置，跳过 OCR")
            return None

        raw_text = self._ocr_pdf(file_bytes)
        if not raw_text:
            return None

        return ResumeDocument(
            filename=filename,
            raw_text=raw_text,
            extractor=self.name,
            is_scanned=True,
            warnings=["文档为扫描件，OCR 识别可能存在误差"],
        )

    def _ocr_pdf(self, content: bytes) -> str:
        """对 PDF 进行 OCR：逐页并行调用 qwen-vl-ocr 模型。"""
        try:
            import fitz  # pymupdf
            import openai
        except ImportError as e:
            logger.warning("OCR 依赖缺失: %s", e)
            return ""

        try:
            with fitz.open(stream=io.BytesIO(content), filetype="pdf") as doc:
                max_pages = min(len(doc), 5)
                page_images: list[tuple[int, str]] = []
                for page_num in range(max_pages):
                    page = doc[page_num]
                    pix = page.get_pixmap(dpi=300)
                    img_b64 = base64.b64encode(pix.tobytes("png")).decode()
                    page_images.append((page_num, img_b64))
        except Exception as e:
            logger.warning("PDF 渲染失败: %s", e)
            return ""

        client = openai.OpenAI(
            api_key=DASHSCOPE_API_KEY,
            base_url=LLM_BASE_URL,
            timeout=60,
        )

        results: list[tuple[int, str]] = []
        with ThreadPoolExecutor(max_workers=max_pages) as executor:
            futures = [
                executor.submit(self._ocr_single_page, idx, b64, client)
                for idx, b64 in page_images
            ]
            for f in futures:
                results.append(f.result())

        results.sort(key=lambda x: x[0])
        texts = [text for _, text in results if text.strip()]
        raw_text = "\n\n".join(texts)
        raw_text = self._clean_ocr_text(raw_text)

        # 如果首轮 OCR 未捕获求职意向关键词，对首页顶部区域单独识别
        if texts and not self._has_job_target_signal(raw_text):
            header_text = self._ocr_header_for_job_target(page_images[0][1], client)
            if header_text:
                raw_text = header_text + "\n\n" + raw_text

        return raw_text

    def _ocr_single_page(
        self, page_idx: int, img_b64: str, client
    ) -> tuple[int, str]:
        """对单页图片进行 OCR 识别。"""
        try:
            resp = client.chat.completions.create(
                model="qwen-vl-ocr",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                            },
                            {
                                "type": "text",
                                "text": (
                                    "请识别这张简历图片中的所有文字。\n"
                                    "要求：\n"
                                    "1. 保持原始排版结构，用空行分隔不同板块\n"
                                    "2. 板块标题单独一行\n"
                                    "3. 列表项保持缩进或用'•'标记\n"
                                    "4. 不要添加任何解释，只输出识别的文字\n"
                                    "5. 模糊无法识别的文字用[模糊]标记\n"
                                    "6. 特别注意：简历顶部的求职意向/期望职位/意向岗位等信息必须完整保留"
                                ),
                            },
                        ],
                    }
                ],
                max_tokens=4000,
            )
            content = resp.choices[0].message.content or ""
            if resp.choices[0].finish_reason == "length":
                logger.warning("OCR 第 %d 页因 max_tokens 被截断", page_idx)
            return page_idx, content
        except Exception as e:
            logger.warning("OCR 第 %d 页失败: %s", page_idx, e)
            return page_idx, ""

    def _has_job_target_signal(self, text: str) -> bool:
        """检查文本中是否包含求职意向相关关键词。"""
        import re

        if not text:
            return False
        return bool(
            re.search(
                r"(?:求职意向|期望职位|目标职位|应聘职位|意向岗位|期望岗位)",
                text,
                re.IGNORECASE,
            )
        )

    def _ocr_header_for_job_target(self, img_b64: str, client) -> str:
        """对首页顶部区域单独 OCR，专门提取求职意向。"""
        try:
            resp = client.chat.completions.create(
                model="qwen-vl-ocr",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                            },
                            {
                                "type": "text",
                                "text": (
                                    "请仔细识别简历图片顶部区域（姓名、联系方式附近）的文字。\n"
                                    "特别注意提取：求职意向 / 期望职位 / 目标职位 / 意向岗位 / 应聘职位\n"
                                    "只输出识别到的文字，不要解释。"
                                ),
                            },
                        ],
                    }
                ],
                max_tokens=500,
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception as e:
            logger.warning("求职意向区域 OCR 失败: %s", e)
            return ""

    def _clean_ocr_text(self, text: str) -> str:
        """修复 OCR 常见错误：中英标点、中文空格、误识别词。"""
        import re

        # 中文间的英文标点转为中文标点
        text = re.sub(r"(?<=[一-鿿]),(?=[一-鿿])", "，", text)
        text = re.sub(r"(?<=[一-鿿])\.(?=[一-鿿])", "。", text)
        text = re.sub(r"(?<=[一-鿿]);(?=[一-鿿])", "；", text)
        text = re.sub(r"(?<=[一-鿿]):(?=[一-鿿])", "：", text)
        text = re.sub(r"(?<=[一-鿿])\((?=[一-鿿])", "（", text)
        text = re.sub(r"(?<=[一-鿿])\)(?=[一-鿿])", "）", text)

        # 清除中文间多余空格
        text = re.sub(r"(?<=[一-鿿])\s+(?=[一-鿿])", "", text)

        # 常见 OCR 误识别修正
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

        # 板块标题标准化：未独立成行的标题前后加换行
        headers = [
            "个人信息", "基本信息", "教育背景", "教育经历",
            "专业技能", "技能", "技术栈", "个人技能",
            "项目经历", "项目经验", "项目", "Projects",
            "实习经历", "实习经验", "工作经历",
            "获奖情况", "荣誉", "竞赛", "获奖",
            "证书", "资质", "资格证书", "技能证书",
            "自我评价", "个人评价", "兴趣爱好",
            "求职意向", "期望职位", "意向岗位",
        ]
        for header in headers:
            pattern = re.compile(r"(?<!\n)(?<!\w)(" + re.escape(header) + r")(?\w)(?!\n)")
            text = pattern.sub(r"\n\1\n", text)

        # 清理多余空行和模糊标记
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = text.replace("[模糊]", "")

        return text.strip()
