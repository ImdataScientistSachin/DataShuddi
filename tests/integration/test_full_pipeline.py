"""
DataShuddi -- Integration Tests: Full 8-Node StateGraph Pipeline.

Verifies end-to-end processing of clean and dirty documents through the
StateGraph with mocked Ollama/Qdrant calls.
Follows the AAA (Arrange, Act, Assert) testing pattern.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.agent.graph import build_graph
from src.agent.state import create_initial_state


@pytest.fixture
def clean_doc_file(tmp_path: Path) -> Path:
    """Fixture creating a temporary clean text document."""
    f = tmp_path / "clean_report.txt"
    f.write_text(
        "Acme Corporation Annual Financial & Operational Performance Report.\n"
        "All business units achieved target operational milestones during the fiscal year.\n"
        "Detailed financial breakdowns indicate 14% year-over-year revenue growth across regions.",
        encoding="utf-8",
    )
    return f


class TestFullPipelineIntegration:
    """End-to-end integration tests for DataShuddi StateGraph."""

    @patch("src.agent.nodes.output_node._upsert_to_qdrant")
    @patch("src.agent.nodes.output_node._generate_embedding")
    @patch("src.agent.nodes.pii_detector._run_qwen_contextual")
    def test_full_pipeline_clean_document(
        self,
        mock_qwen: MagicMock,
        mock_embed: MagicMock,
        mock_upsert: MagicMock,
        clean_doc_file: Path,
    ) -> None:
        """Arrange: Clean document. Act: Invoke compiled graph. Assert: Passes validation and reaches output node."""
        # Arrange
        mock_qwen.return_value = []
        mock_embed.return_value = [0.1] * 1024
        graph = build_graph(use_checkpointer=False)

        initial_state = create_initial_state(
            doc_id="integration_test_hash_001",
            doc_path=str(clean_doc_file),
            source_system="local",
            mime_type="text/plain",
        )

        # Act
        final_state = graph.invoke(initial_state)

        # Assert
        assert final_state["is_sanitized"] is True
        assert final_state["validation_passed"] is True
        assert "security_sanitizer" in final_state["node_timestamps"]
        assert "output_node" in final_state["node_timestamps"]
        mock_upsert.assert_called_once()
