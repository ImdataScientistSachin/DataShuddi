"""
DataShuddi -- Unit Tests: Node 4 PII Masker.

Verifies token replacement with safe placeholders ([EMAIL_REDACTED], etc.).
Follows the AAA (Arrange, Act, Assert) testing pattern.
"""
import pytest

from src.agent.nodes.pii_masker import pii_masker_node
from src.agent.state import DataShuddiState


@pytest.fixture
def base_state() -> DataShuddiState:
    """Fixture providing baseline DataShuddiState for Node 4 tests."""
    return {
        "doc_id": "hash_mask_123",
        "doc_path": "./data/raw/contract.pdf",
        "source_system": "local",
        "mime_type": "application/pdf",
        "raw_text": "",
        "_pages": [],
        "cleaned_text": "Contact user@example.com for info.",
        "masked_text": "",
        "header_footer_candidates": [],
        "pii_entities": [
            {"type": "EMAIL_ADDRESS", "start": 8, "end": 24, "score": 0.99}
        ],
        "pii_count": 1,
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


class TestPIIMaskerNode:
    """Unit tests for Node 4: PII Masker."""

    def test_email_replaced_with_placeholder(self, base_state: DataShuddiState) -> None:
        """Arrange: Text with email entity. Act: Run node. Assert: [EMAIL_REDACTED] in masked_text."""
        # Arrange
        state = base_state

        # Act
        result = pii_masker_node(state)

        # Assert
        assert "[EMAIL_REDACTED]" in result["masked_text"]
        assert "user@example.com" not in result["masked_text"]
        assert "pii_masker" in result["node_timestamps"]

    def test_multiple_out_of_order_entities_masked_correctly(self, base_state: DataShuddiState) -> None:
        """Arrange: Text with multiple entities out of order by start index. Act: Run node. Assert: Both masked correctly without offset drift."""
        # Arrange
        state = base_state
        state["cleaned_text"] = "User Alice with email alice@acme.com lives in Springfield."
        state["pii_entities"] = [
            {"type": "EMAIL_ADDRESS", "start": 17, "end": 31, "score": 0.99},  # alice@acme.com
            {"type": "PERSON", "start": 5, "end": 10, "score": 0.95},          # Alice
        ]

        # Act
        result = pii_masker_node(state)

        # Assert
        assert "Alice" not in result["masked_text"]
        assert "alice@acme.com" not in result["masked_text"]
        assert "[PERSON_REDACTED]" in result["masked_text"]
        assert "[EMAIL_REDACTED]" in result["masked_text"]

    def test_custom_or_unknown_entity_type_uses_fallback(self, base_state: DataShuddiState) -> None:
        """Arrange: Custom contextual entity type 'SALARY'. Act: Run node. Assert: [SALARY_REDACTED] placeholder used."""
        # Arrange
        state = base_state
        state["cleaned_text"] = "Executive salary: $185,000 yearly."
        state["pii_entities"] = [
            {"type": "SALARY", "start": 18, "end": 26, "score": 0.90}  # $185,000
        ]

        # Act
        result = pii_masker_node(state)

        # Assert
        assert "$185,000" not in result["masked_text"]
        assert "[SALARY_REDACTED]" in result["masked_text"]

    def test_no_entities_leaves_text_unchanged(self, base_state: DataShuddiState) -> None:
        """Arrange: Zero PII entities. Act: Run node. Assert: masked_text equals cleaned_text."""
        # Arrange
        state = base_state
        state["pii_entities"] = []
        state["cleaned_text"] = "Clean enterprise report."

        # Act
        result = pii_masker_node(state)

        # Assert
        assert result["masked_text"] == "Clean enterprise report."

    def test_empty_text_handled_safely(self, base_state: DataShuddiState) -> None:
        """Arrange: Empty cleaned_text. Act: Run node. Assert: Returns empty masked_text."""
        # Arrange
        state = base_state
        state["cleaned_text"] = ""
        state["pii_entities"] = []

        # Act
        result = pii_masker_node(state)

        # Assert
        assert result["masked_text"] == ""
