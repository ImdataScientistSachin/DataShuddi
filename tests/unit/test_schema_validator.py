"""
DataShuddi -- Unit Tests: Node 5 Schema Validator.

Verifies Pydantic v2 EnterpriseDoc schema validation and quality scoring.
Follows the AAA (Arrange, Act, Assert) testing pattern.
"""
import pytest

from src.agent.nodes.schema_validator import schema_validator_node
from src.agent.state import DataShuddiState


@pytest.fixture
def base_state() -> DataShuddiState:
    """Fixture providing baseline DataShuddiState for Node 5 tests."""
    return {
        "doc_id": "hash_schema_123",
        "doc_path": "./data/raw/annual_report.pdf",
        "source_system": "local",
        "mime_type": "application/pdf",
        "raw_text": "",
        "_pages": [],
        "cleaned_text": "",
        "masked_text": "This is a long enterprise document content that spans more than one hundred characters to pass length validation cleanly.",
        "header_footer_candidates": ["CONFIDENTIAL FOOTER"],
        "pii_entities": [{"type": "EMAIL_ADDRESS", "start": 0, "end": 10, "score": 0.9}],
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


class TestSchemaValidatorNode:
    """Unit tests for Node 5: Schema Validator."""

    def test_valid_doc_passes_validation(self, base_state: DataShuddiState) -> None:
        """Arrange: Valid masked_text >= 100 chars. Act: Run node. Assert: validation_passed=True."""
        # Arrange
        state = base_state

        # Act
        result = schema_validator_node(state)

        # Assert
        assert result["validation_passed"] is True
        assert len(result["validation_errors"]) == 0
        assert 0.0 <= result["quality_score"] <= 1.0
        assert "schema_validator" in result["node_timestamps"]

    def test_exact_100_char_boundary_passes_validation(self, base_state: DataShuddiState) -> None:
        """Arrange: Text exactly 99 vs 100 chars. Act: Run node. Assert: 99 fails, 100 passes."""
        # 99 chars
        state_99: DataShuddiState = {**base_state, "masked_text": "A" * 99}
        res_99 = schema_validator_node(state_99)
        assert res_99["validation_passed"] is False

        # 100 chars
        state_100: DataShuddiState = {**base_state, "masked_text": "A" * 100}
        res_100 = schema_validator_node(state_100)
        assert res_100["validation_passed"] is True

    def test_short_content_fails_validation(self, base_state: DataShuddiState) -> None:
        """Arrange: masked_text < 100 chars. Act: Run node. Assert: validation_passed=False."""
        # Arrange
        state = base_state
        state["masked_text"] = "Short content."

        # Act
        result = schema_validator_node(state)

        # Assert
        assert result["validation_passed"] is False
        assert len(result["validation_errors"]) >= 1

    def test_residual_email_fails_validation(self, base_state: DataShuddiState) -> None:
        """Arrange: Unmasked email in masked_text. Act: Run node. Assert: validation_passed=False."""
        # Arrange
        state = base_state
        state["masked_text"] = (
            "This is a long enterprise document content that spans more than one hundred characters "
            "but still contains an unmasked email user@domain.org post-anonymization."
        )

        # Act
        result = schema_validator_node(state)

        # Assert
        assert result["validation_passed"] is False
        assert any("Residual" in err for err in result["validation_errors"])

    def test_residual_ssn_fails_validation(self, base_state: DataShuddiState) -> None:
        """Arrange: Unmasked SSN pattern in masked_text. Act: Run node. Assert: validation_passed=False."""
        # Arrange
        state = base_state
        state["masked_text"] = (
            "This is a long enterprise document content that spans more than one hundred characters "
            "and contains an unmasked SSN pattern 987-65-4321 post-anonymization."
        )

        # Act
        result = schema_validator_node(state)

        # Assert
        assert result["validation_passed"] is False
        assert any("Residual" in err for err in result["validation_errors"])
