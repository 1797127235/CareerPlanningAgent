"""Extract raw text from PDF, DOCX, and TXT files."""
from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)

_MAX_TEXT_LEN = 30000  # Hard cap to avoid token explosion


def extract_raw_text(content: bytes, filename: str) -> str:
    """Extract plain text from resume file bytes."""
    fname = filename.lower()
    text = ""

    if fname.endswith(".pdf"):
        text = _extract_pdf_text(content)
    elif fname.endswith(".docx"):
        text = _extract_docx_text(content)
    elif fname.endswith(".doc"):
        # .doc is binary; skip extraction — third-party APIs handle raw bytes
        text = ""
    else:
        # Plain text (txt, md, etc.)
        text = content.decode("utf-8", errors="ignore")

    # Hard cap to prevent token explosion on scanned/OCR'd files
    if len(text) > _MAX_TEXT_LEN:
        logger.warning("Extracted text truncated: %d → %d chars", len(text), _MAX_TEXT_LEN)
        text = text[:_MAX_TEXT_LEN]

    return text


def _extract_pdf_text(content: bytes) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    except ImportError:
        logger.warning("pdfplumber not installed, falling back to raw decode")
        return content.decode("utf-8", errors="ignore")
    except Exception as e:
        logger.warning("PDF text extraction failed: %s", e)
        return ""


def _extract_docx_text(content: bytes) -> str:
    try:
        import docx
        doc = docx.Document(io.BytesIO(content))
        return "\n".join(p.text for p in doc.paragraphs if p.text)
    except ImportError:
        logger.warning("python-docx not installed, falling back to raw decode")
        return content.decode("utf-8", errors="ignore")
    except Exception as e:
        logger.warning("DOCX text extraction failed: %s", e)
        return ""


def is_scanned_pdf(content: bytes, filename: str, raw_text: str) -> bool:
    """Heuristic: if PDF has no extractable text, treat as scanned/image-based."""
    return not raw_text.strip() and filename.lower().endswith(".pdf")
