"""
DataShuddi — Node 1: Extractor Node.

Extracts raw text from supported document types (PDF, DOCX, TXT) with
page-level separation. Falls back to PaddleOCR CPU mode when character
density is below the configured threshold (< OCR_CHAR_DENSITY_THRESHOLD
chars/page on average).

Accepted MIME types:
    - application/pdf
    - application/vnd.openxmlformats-officedocument.wordprocessingml.document
    - text/plain

Policy:
    - Corrupted or password-protected files are caught gracefully.
    - OCR lines with confidence < PADDLEOCR_MIN_CONFIDENCE are discarded.
    - _pages preserves page-level splits for H/F frequency analysis in Node 2.
"""
import time
from pathlib import Path
from typing import Any

from loguru import logger

from src.agent.state import DataShuddiState
from src.utils.config import settings


def extractor_node(state: DataShuddiState) -> DataShuddiState:
    """
    Node 1: Multi-format document text extractor with OCR fallback.

    Extracts text from PDF, DOCX, and TXT documents. Stores per-page text
    in _pages for downstream header/footer frequency analysis.

    Args:
        state: Current DataShuddiState with doc_path and mime_type set.

    Returns:
        Updated DataShuddiState with raw_text and _pages populated.

    Raises:
        No exceptions raised — extraction failures are captured in state.
    """
    node_name = "extractor"
    timestamps: dict[str, float] = dict(state.get("node_timestamps", {}))
    timestamps[node_name] = time.time()

    doc_path = Path(state["doc_path"])
    mime_type = state["mime_type"]

    # If doc_path does not exist on disk but state already has raw_text (e.g. test fixtures or retries), preserve existing text
    if not doc_path.exists() and state.get("raw_text"):
        logger.info("doc_id={} | Preserving inline raw_text ({} chars, {} pages)", state.get("doc_id", "UNKNOWN"), len(state["raw_text"]), len(state.get("_pages", [])))
        return {**state, "node_timestamps": timestamps}

    try:
        if mime_type == "application/pdf":
            pages, raw_text = _extract_pdf(doc_path)
        elif mime_type in (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ):
            pages, raw_text = _extract_docx(doc_path)
        elif mime_type == "text/plain":
            pages, raw_text = _extract_txt(doc_path)
        else:
            logger.error("doc_id={} | Unsupported MIME type: {}", state["doc_id"], mime_type)
            return {**state, "raw_text": "", "_pages": [], "node_timestamps": timestamps}

        logger.info(
            "doc_id={} | Extracted {} pages, {} chars",
            state["doc_id"],
            len(pages),
            len(raw_text),
        )
        return {
            **state,
            "raw_text": raw_text,
            "_pages": pages,
            "node_timestamps": timestamps,
        }

    except Exception as exc:
        logger.error("doc_id={} | Extraction Error: {}", state["doc_id"], exc)
        return {**state, "raw_text": "", "_pages": [], "node_timestamps": timestamps}


def _extract_pdf(doc_path: Path) -> tuple[list[str], str]:
    """Extract text from PDF using PyMuPDF with PaddleOCR fallback."""
    import fitz  # PyMuPDF

    pages: list[str] = []
    doc = fitz.open(str(doc_path))

    for page in doc:
        text = page.get_text("text")
        pages.append(text)

    # Check average character density to decide if OCR fallback is needed
    avg_density = sum(len(p) for p in pages) / max(len(pages), 1)
    if avg_density < settings.ocr_char_density_threshold:
        logger.info("Low char density ({:.1f} chars/page) — triggering PaddleOCR fallback", avg_density)
        pages = _ocr_fallback_pdf(doc_path, doc)

    doc.close()
    return pages, "\n".join(pages)


def _ocr_fallback_pdf(doc_path: Path, doc: Any) -> list[str]:
    """PaddleOCR CPU fallback for low-density (scanned) PDF pages."""
    import fitz
    import numpy as np
    from paddleocr import PaddleOCR

    ocr = PaddleOCR(use_angle_cls=True, lang="en", use_gpu=False, show_log=False)
    pages: list[str] = []

    for page in doc:
        mat = fitz.Matrix(2, 2)  # 2x zoom for better OCR quality
        clip = page.get_pixmap(matrix=mat)
        img_array = np.frombuffer(clip.samples, dtype=np.uint8).reshape(clip.h, clip.w, clip.n)

        import warnings

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            result = ocr.ocr(img_array, cls=True)
        if not result or not result[0]:
            pages.append("")
            continue

        # Filter lines by confidence
        lines = [
            line[1][0]
            for line in result[0]
            if line[1][1] >= settings.paddleocr_min_confidence
        ]
        pages.append("\n".join(lines))

    return pages


def _extract_docx(doc_path: Path) -> tuple[list[str], str]:
    """Extract text from DOCX files. Treats each paragraph as a segment."""
    from docx import Document

    doc = Document(str(doc_path))
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    raw_text = "\n".join(paragraphs)
    # DOCX has no native page concept — treat entire doc as single page
    return [raw_text], raw_text


def _extract_txt(doc_path: Path) -> tuple[list[str], str]:
    """Extract text from plain text files."""
    raw_text = doc_path.read_text(encoding="utf-8", errors="ignore")
    return [raw_text], raw_text
