"""
DataShuddi -- Unit Tests: Loguru PII-Scrubbing Middleware (logging_hygiene.py).

Verifies zero PII leakage in Loguru records, extra parameters, and telemetry traces.
Follows the AAA (Arrange, Act, Assert) testing pattern.
"""
from typing import Any

from src.utils.logging_hygiene import scrub_pii_from_record


class TestLoggingHygiene:
    """Unit tests for Loguru PII scrubbing patcher."""

    def test_sensitive_keys_are_redacted_from_log_record(self) -> None:
        """Arrange: Record extra containing raw_text & cleaned_text. Act: Patch record. Assert: Redacted."""
        # Arrange
        record: dict[str, Any] = {
            "message": "Processing doc",
            "extra": {
                "doc_id": "sha256_hash_123",
                "raw_text": "Sensitive PII John Smith SSN 123-45-6789",
                "cleaned_text": "Cleaned text with john@acme.com",
                "masked_text": "Masked text",
                "_pages": ["Page 1 raw text"],
                "source_system": "local",
            },
        }

        # Act
        scrub_pii_from_record(record)

        # Assert
        extra = record["extra"]
        assert extra["raw_text"] == "[REDACTED_FROM_LOG]"
        assert extra["cleaned_text"] == "[REDACTED_FROM_LOG]"
        assert extra["masked_text"] == "[REDACTED_FROM_LOG]"
        assert extra["_pages"] == "[REDACTED_FROM_LOG]"
        assert extra["doc_id"] == "sha256_hash_123"
        assert extra["source_system"] == "local"

    def test_pii_entities_raw_text_is_scrubbed_from_extra(self) -> None:
        """Arrange: pii_entities in record extra. Act: Patch record. Assert: Raw text stripped."""
        # Arrange
        record: dict[str, Any] = {
            "message": "Entities detected",
            "extra": {
                "pii_entities": [
                    {"type": "EMAIL_ADDRESS", "start": 0, "end": 15, "score": 0.99, "text": "raw_john@acme.com"},
                    {"type": "US_SSN", "start": 20, "end": 31, "score": 0.95, "text": "123-45-6789"},
                ]
            },
        }

        # Act
        scrub_pii_from_record(record)

        # Assert
        scrubbed = record["extra"]["pii_entities"]
        assert len(scrubbed) == 2
        for entity in scrubbed:
            assert "text" not in entity
            assert "type" in entity
            assert "score" in entity

    def test_record_without_extra_handled_safely(self) -> None:
        """Arrange: Record with empty extra dict. Act: Patch record. Assert: Execution completes without error."""
        # Arrange
        record: dict[str, Any] = {"message": "Standard log", "extra": {}}

        # Act
        scrub_pii_from_record(record)

        # Assert
        assert record["extra"] == {}
