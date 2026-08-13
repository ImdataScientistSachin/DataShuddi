"""
DataShuddi — Node 2: Header/Footer Detector Node.

Deterministic line frequency analysis to identify and remove repeating
boilerplate lines (headers/footers) across all pages of a document.

Algorithm:
    1. Extract top-3 and bottom-3 lines from each page.
    2. Count how many pages each candidate line appears on.
    3. Lines appearing on > hf_threshold fraction of pages are flagged.
    4. Flagged lines are removed from all page text.

The detection threshold (hf_threshold) is loaded dynamically from the
LangGraph Store namespace ("doc_cleaning", source_system) to support
self-correction by the Reflector node (Node 6).
"""
import time
from collections import Counter

from loguru import logger

from src.agent.state import DataShuddiState

# Number of lines to inspect at top and bottom of each page
TOP_BOTTOM_LINES: int = 3


def hf_detector_node(state: DataShuddiState) -> DataShuddiState:
    """
    Node 2: Header/footer line frequency detector and remover.

    Uses deterministic page-split line frequency analysis to identify
    repeating boilerplate and removes it from cleaned_text.

    Args:
        state: DataShuddiState with _pages populated by Node 1.

    Returns:
        Updated DataShuddiState with cleaned_text and header_footer_candidates set.
    """
    node_name = "hf_detector"
    timestamps: dict[str, float] = dict(state.get("node_timestamps", {}))
    timestamps[node_name] = time.time()

    pages: list[str] = state.get("_pages", [])
    threshold: float = state.get("hf_threshold", 0.30)

    if not pages or len(pages) < 2:
        logger.info("doc_id={} | Single-page document ({}) -- skipping page H/F frequency removal", state.get("doc_id", "UNKNOWN"), len(pages))
        return {**state, "cleaned_text": state.get("raw_text", ""), "header_footer_candidates": [], "node_timestamps": timestamps}

    # Build candidate pool: top-3 + bottom-3 lines per page
    candidate_counter: Counter[str] = Counter()
    for page_text in pages:
        lines = [line.strip() for line in page_text.splitlines() if line.strip()]
        top_lines = lines[:TOP_BOTTOM_LINES]
        bottom_lines = lines[-TOP_BOTTOM_LINES:] if len(lines) > TOP_BOTTOM_LINES else []
        for line in top_lines + bottom_lines:
            candidate_counter[line] += 1

    # Flag lines that appear on > threshold fraction of all pages
    total_pages = len(pages)
    flagged_lines: list[str] = [
        line
        for line, count in candidate_counter.items()
        if count > 1 and (count / total_pages) > threshold and len(line) > 3
    ]

    if flagged_lines:
        logger.info(
            "doc_id={} | H/F removed {} boilerplate lines (threshold={:.2f})",
            state["doc_id"],
            len(flagged_lines),
            threshold,
        )

    # Remove flagged lines from raw text to produce cleaned_text
    raw_text: str = state.get("raw_text", "")
    cleaned_lines = [
        line for line in raw_text.splitlines()
        if line.strip() not in flagged_lines
    ]
    cleaned_text = "\n".join(cleaned_lines)

    return {
        **state,
        "cleaned_text": cleaned_text,
        "header_footer_candidates": flagged_lines,
        "node_timestamps": timestamps,
    }
