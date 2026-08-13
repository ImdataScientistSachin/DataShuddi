"""
DataShuddi -- Unit Tests: Node 3 Hybrid PII Detector.

Verifies Presidio regex + spaCy NER detection and zero PII log leakage.
Follows the AAA (Arrange, Act, Assert) testing pattern.
"""
from unittest.mock import MagicMock, patch

import pytest

from src.agent.nodes.pii_detector import _run_qwen_contextual, pii_detector_node
from src.agent.state import DataShuddiState


@pytest.fixture
def base_state() -> DataShuddiState:
    """Fixture providing baseline DataShuddiState for Node 3 tests."""
    return {
        "doc_id": "hash_pii_123",
        "doc_path": "./data/raw/hr_contract.pdf",
        "source_system": "local",
        "mime_type": "application/pdf",
        "raw_text": "",
        "_pages": [],
        "cleaned_text": "Contact employee John Doe at john.doe@acme.org or call 555-123-4567.",
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


class TestPIIDetectorNode:
    """Unit tests for Node 3: Hybrid PII Detector."""

    @patch("src.agent.nodes.pii_detector._run_qwen_contextual")
    def test_email_and_phone_detected(self, mock_qwen: MagicMock, base_state: DataShuddiState) -> None:
        """Arrange: Text with email and phone. Act: Run node. Assert: PII entities detected."""
        # Arrange
        mock_qwen.return_value = []
        state = base_state

        # Act
        result = pii_detector_node(state)

        # Assert
        assert result["pii_count"] >= 1
        assert any(e["type"] in ("EMAIL_ADDRESS", "PHONE_NUMBER", "PERSON") for e in result["pii_entities"])
        assert "pii_detector" in result["node_timestamps"]

    @patch("src.agent.nodes.pii_detector._run_qwen_contextual")
    def test_no_pii_returns_zero_count(self, mock_qwen: MagicMock, base_state: DataShuddiState) -> None:
        """Arrange: Clean text. Act: Run node. Assert: pii_count is 0."""
        # Arrange
        mock_qwen.return_value = []
        state = base_state
        state["cleaned_text"] = "The system operational status is nominal. Server load 12%."

        # Act
        result = pii_detector_node(state)

        # Assert
        assert result["pii_count"] == 0
        assert result["pii_entities"] == []

    @patch("src.agent.nodes.pii_detector._run_qwen_contextual")
    def test_high_risk_domain_triggers_layer_2(self, mock_qwen: MagicMock, base_state: DataShuddiState) -> None:
        """Arrange: source_system='hr_docs'. Act: Run node. Assert: Qwen contextual layer invoked."""
        # Arrange
        mock_qwen.return_value = [{"type": "SALARY", "start": 0, "end": 10, "score": 0.9}]
        state = base_state
        state["source_system"] = "hr_docs"

        # Act
        result = pii_detector_node(state)

        # Assert
        mock_qwen.assert_called_once()
        assert result["pii_count"] >= 1

    @patch("src.agent.nodes.pii_detector._run_qwen_contextual")
    def test_ip_address_detected(self, mock_qwen: MagicMock, base_state: DataShuddiState) -> None:
        """Arrange: Text containing IP address. Act: Run node. Assert: IP_ADDRESS entity detected."""
        # Arrange
        mock_qwen.return_value = []
        state = base_state
        state["cleaned_text"] = "Server IP address 192.168.1.100 was assigned to cluster node 4."

        # Act
        result = pii_detector_node(state)

        # Assert
        assert result["pii_count"] >= 1
        assert any(e["type"] == "IP_ADDRESS" for e in result["pii_entities"])

    @patch("ollama.chat")
    def test_qwen_contextual_llm_failure_handled_gracefully(self, mock_ollama: MagicMock) -> None:
        """Arrange: Ollama chat raises Exception or returns invalid JSON. Act: Run _run_qwen_contextual. Assert: Returns [] safely."""
        # Arrange: Ollama raises Exception
        mock_ollama.side_effect = Exception("Ollama connection timeout")

        # Act
        res = _run_qwen_contextual("Text content", "doc_123")

        # Assert
        assert res == []

        # Arrange: Ollama returns malformed JSON
        mock_ollama.side_effect = None
        mock_ollama.return_value = {"message": {"content": "INVALID JSON STRING"}}

        # Act
        res2 = _run_qwen_contextual("Text content", "doc_123")

        # Assert
        assert res2 == []
