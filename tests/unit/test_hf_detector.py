"""
DataShuddi -- Unit Tests: Node 2 Header/Footer Detector.

Verifies page-split line frequency analysis and boilerplate removal.
Follows the AAA (Arrange, Act, Assert) testing pattern.
"""
import pytest

from src.agent.nodes.hf_detector import hf_detector_node
from src.agent.state import DataShuddiState


@pytest.fixture
def base_state() -> DataShuddiState:
    """Fixture providing baseline DataShuddiState for Node 2 tests."""
    return {
        "doc_id": "hash_hf_123",
        "doc_path": "./data/raw/multi_page.pdf",
        "source_system": "local",
        "mime_type": "application/pdf",
        "raw_text": "",
        "_pages": [],
        "cleaned_text": "",
        "masked_text": "",
        "header_footer_candidates": [],
        "pii_entities": [],
        "pii_count": 0,
        "validation_errors": [],
        "validation_passed": False,
        "retry_count": 0,
        "reflection_text": "",
        "reflector_confidence": 0.0,
        "needs_human_review": False,
        "hf_threshold": 0.30,
        "is_sanitized": True,
        "security_flags": [],
        "quality_score": 0.0,
        "node_timestamps": {},
        "processing_time_ms": 0,
        "_start_time": 0.0,
    }


class TestHFDetectorNode:
    """Unit tests for Node 2: Header/Footer Detector."""

    def test_repeated_footer_is_removed(self, base_state: DataShuddiState) -> None:
        """Arrange: 4 pages with identical footer line. Act: Run node. Assert: Footer line removed."""
        # Arrange
        state = base_state
        footer = "CONFIDENTIAL | ACME CORP 2024"
        p1 = f"Page 1 Content line.\n{footer}"
        p2 = f"Page 2 Content line.\n{footer}"
        p3 = f"Page 3 Content line.\n{footer}"
        p4 = f"Page 4 Content line.\n{footer}"

        state["_pages"] = [p1, p2, p3, p4]
        state["raw_text"] = "\n".join([p1, p2, p3, p4])
        state["hf_threshold"] = 0.30

        # Act
        result = hf_detector_node(state)

        # Assert
        assert footer not in result["cleaned_text"]
        assert footer in result["header_footer_candidates"]
        assert "Page 1 Content line." in result["cleaned_text"]
        assert "hf_detector" in result["node_timestamps"]

    def test_no_repeating_lines_leaves_text_unchanged(self, base_state: DataShuddiState) -> None:
        """Arrange: Unique content per page. Act: Run node. Assert: cleaned_text equals raw_text."""
        # Arrange
        state = base_state
        p1 = "Unique content line A."
        p2 = "Unique content line B."
        state["_pages"] = [p1, p2]
        state["raw_text"] = f"{p1}\n{p2}"

        # Act
        result = hf_detector_node(state)

        # Assert
        assert len(result["header_footer_candidates"]) == 0
        assert result["cleaned_text"] == state["raw_text"]

    def test_dynamic_threshold_adjustments(self, base_state: DataShuddiState) -> None:
        """Arrange: Line appearing on 2 of 5 pages (40% frequency). Act: Test threshold 0.30 vs 0.50. Assert: Removed at 0.30, kept at 0.50."""
        # Arrange
        line_to_flag = "REPEATING HEADER LINE ACME"
        p1 = f"{line_to_flag}\nContent P1"
        p2 = f"{line_to_flag}\nContent P2"
        p3 = "Content P3"
        p4 = "Content P4"
        p5 = "Content P5"
        pages = [p1, p2, p3, p4, p5]

        # Test threshold 0.30 (40% > 30% -> Flagged)
        state_30: DataShuddiState = {**base_state, "_pages": pages, "raw_text": "\n".join(pages), "hf_threshold": 0.30}
        res_30 = hf_detector_node(state_30)
        assert line_to_flag in res_30["header_footer_candidates"]
        assert line_to_flag not in res_30["cleaned_text"]

        # Test threshold 0.50 (40% <= 50% -> Kept)
        state_50: DataShuddiState = {**base_state, "_pages": pages, "raw_text": "\n".join(pages), "hf_threshold": 0.50}
        res_50 = hf_detector_node(state_50)
        assert line_to_flag not in res_50["header_footer_candidates"]
        assert line_to_flag in res_50["cleaned_text"]

    def test_short_lines_ignored_from_hf_removal(self, base_state: DataShuddiState) -> None:
        """Arrange: Short line (<= 3 chars) repeating across pages. Act: Run node. Assert: Not removed as boilerplate."""
        # Arrange
        short_line = "ABC"
        pages = [f"{short_line}\nPage 1 text", f"{short_line}\nPage 2 text", f"{short_line}\nPage 3 text"]
        state: DataShuddiState = {**base_state, "_pages": pages, "raw_text": "\n".join(pages), "hf_threshold": 0.30}

        # Act
        result = hf_detector_node(state)

        # Assert
        assert short_line not in result["header_footer_candidates"]
        assert short_line in result["cleaned_text"]

    def test_empty_pages_returns_raw_text(self, base_state: DataShuddiState) -> None:
        """Arrange: Empty _pages. Act: Run node. Assert: Returns raw_text without crashing."""
        # Arrange
        state = base_state
        state["_pages"] = []
        state["raw_text"] = "Fallback raw content."

        # Act
        result = hf_detector_node(state)

        # Assert
        assert result["cleaned_text"] == "Fallback raw content."
        assert result["header_footer_candidates"] == []
