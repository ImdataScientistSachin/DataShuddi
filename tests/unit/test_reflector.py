"""
DataShuddi -- Unit Tests: Node 6 Reflector.

Verifies confidence gate, max delta cap, and human review escalation rules.
Follows the AAA (Arrange, Act, Assert) testing pattern.
"""
from unittest.mock import MagicMock, patch

import pytest

from src.agent.nodes.reflector import _run_qwen_reflection, reflector_node
from src.agent.state import DataShuddiState


@pytest.fixture
def base_state() -> DataShuddiState:
    """Fixture providing baseline DataShuddiState for Node 6 tests."""
    return {
        "doc_id": "hash_reflect_123",
        "doc_path": "./data/raw/failed_doc.pdf",
        "source_system": "local",
        "mime_type": "application/pdf",
        "raw_text": "",
        "_pages": [],
        "cleaned_text": "",
        "masked_text": "",
        "header_footer_candidates": [],
        "pii_entities": [],
        "pii_count": 5,
        "validation_errors": ["Content length 50 chars below min 100"],
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


class TestReflectorNode:
    """Unit tests for Node 6: Reflector."""

    @patch("src.agent.nodes.reflector._run_qwen_reflection")
    def test_high_confidence_updates_threshold_capped(
        self, mock_reflect: MagicMock, base_state: DataShuddiState
    ) -> None:
        """Arrange: High confidence critique with large delta. Act: Run node. Assert: Delta capped at 0.05."""
        # Arrange
        mock_reflect.return_value = ("Increase threshold to remove footers", 0.45, 0.85)
        state = base_state
        state["hf_threshold"] = 0.30

        # Act
        result = reflector_node(state)

        # Assert
        assert result["retry_count"] == 1
        assert result["needs_human_review"] is False
        assert result["hf_threshold"] == 0.35  # Capped at +0.05 max delta
        assert "reflector" in result["node_timestamps"]

    @patch("src.agent.nodes.reflector._run_qwen_reflection")
    def test_confidence_gate_boundary_exact_070(
        self, mock_reflect: MagicMock, base_state: DataShuddiState
    ) -> None:
        """Arrange: Confidence 0.69 (blocked) vs 0.70 (passed). Act: Run node. Assert: Only 0.70 updates threshold."""
        # 0.69 -> Blocked
        mock_reflect.return_value = ("Critique", 0.35, 0.69)
        res_69 = reflector_node(base_state)
        assert res_69["hf_threshold"] == 0.30

        # 0.70 -> Passed
        mock_reflect.return_value = ("Critique", 0.35, 0.70)
        res_70 = reflector_node(base_state)
        assert res_70["hf_threshold"] == 0.35

    @patch("src.agent.nodes.reflector._run_qwen_reflection")
    def test_low_confidence_leaves_threshold_unchanged(
        self, mock_reflect: MagicMock, base_state: DataShuddiState
    ) -> None:
        """Arrange: Low confidence critique (< 0.70). Act: Run node. Assert: Threshold unchanged."""
        # Arrange
        mock_reflect.return_value = ("Uncertain critique", 0.45, 0.50)
        state = base_state
        state["hf_threshold"] = 0.30

        # Act
        result = reflector_node(state)

        # Assert
        assert result["hf_threshold"] == 0.30  # Confidence gate blocked update

    @patch("src.agent.nodes.reflector._write_to_human_review_queue")
    def test_max_retry_escalates_to_human_review(
        self, mock_queue: MagicMock, base_state: DataShuddiState
    ) -> None:
        """Arrange: retry_count = 2 (will reach 3). Act: Run node. Assert: Escalated to human review."""
        # Arrange
        state = base_state
        state["retry_count"] = 2  # Increments to 3 >= max_retry_count

        # Act
        result = reflector_node(state)

        # Assert
        assert result["needs_human_review"] is True
        mock_queue.assert_called_once()

    @patch("src.agent.nodes.reflector._write_to_human_review_queue")
    def test_high_pii_count_escalates_to_human_review(
        self, mock_queue: MagicMock, base_state: DataShuddiState
    ) -> None:
        """Arrange: pii_count > 50. Act: Run node. Assert: Escalated to human review."""
        # Arrange
        state = base_state
        state["pii_count"] = 60

        # Act
        result = reflector_node(state)

        # Assert
        assert result["needs_human_review"] is True
        mock_queue.assert_called_once()

    @patch("ollama.chat")
    def test_ollama_qwen_reflection_failure_uses_fallback(self, mock_ollama: MagicMock) -> None:
        """Arrange: Ollama chat raises Exception. Act: Run _run_qwen_reflection. Assert: Fallback returned."""
        # Arrange
        mock_ollama.side_effect = Exception("Model unreachable")

        # Act
        critique, recommended, confidence = _run_qwen_reflection("doc_99", ["Error"], 0.30, 5)

        # Assert
        assert "fallback" in critique.lower()
        assert recommended == 0.30
        assert confidence == 0.5

    @patch("src.agent.nodes.reflector._run_qwen_reflection")
    def test_reflector_calls_trimmer_and_passes_evidence(
        self, mock_reflect: MagicMock, base_state: DataShuddiState
    ) -> None:
        """Arrange: State with multi-line masked text. Act: Run node. Assert: Evidence passed to _run_qwen_reflection."""
        mock_reflect.return_value = ("Critique", 0.35, 0.80)
        state = base_state
        state["masked_text"] = ("Standard contract paragraph.\n" * 20) + "Residual pattern US_SSN at offset 50.\n"
        state["validation_errors"] = ["Residual pattern US_SSN"]

        reflector_node(state)

        mock_reflect.assert_called_once()
        _, kwargs = mock_reflect.call_args
        assert "evidence" in kwargs
        assert "Residual pattern US_SSN" in kwargs["evidence"]
