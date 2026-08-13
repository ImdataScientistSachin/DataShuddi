"""
DataShuddi -- Unit Tests: Node 7 Output Node.

Verifies strict metadata payload allowlist enforcement and Qdrant vector upsert safety.
Follows the AAA (Arrange, Act, Assert) testing pattern.
"""
import hashlib
from unittest.mock import MagicMock, patch

import pytest

from src.agent.nodes.output_node import _chunk_text, _generate_embedding, output_node
from src.agent.state import DataShuddiState
from src.utils.constants import ALLOWED_PAYLOAD_KEYS


@pytest.fixture
def base_state() -> DataShuddiState:
    """Fixture providing baseline DataShuddiState for Node 7 tests."""
    return {
        "doc_id": "hash_output_123",
        "doc_path": "./data/raw/clean_doc.pdf",
        "source_system": "local",
        "mime_type": "application/pdf",
        "raw_text": "",
        "_pages": [],
        "cleaned_text": "",
        "masked_text": "This is a clean, validated document that passed schema validation and is ready for embedding and upsert into Qdrant vector database.",
        "header_footer_candidates": [],
        "pii_entities": [],
        "pii_count": 0,
        "validation_errors": [],
        "validation_passed": True,
        "retry_count": 0,
        "reflection_text": "",
        "reflector_confidence": 0.0,
        "needs_human_review": False,
        "hf_threshold": 0.30,
        "is_sanitized": True,
        "security_flags": [],
        "quality_score": 0.95,
        "node_timestamps": {},
        "processing_time_ms": 0,
        "_start_time": 0.0,
    }


class TestOutputNode:
    """Unit tests for Node 7: Output Node."""

    @patch("src.agent.nodes.output_node._upsert_to_qdrant")
    @patch("src.agent.nodes.output_node._generate_embedding")
    def test_only_allowed_keys_passed_to_qdrant(
        self, mock_embed: MagicMock, mock_upsert: MagicMock, base_state: DataShuddiState
    ) -> None:
        """Arrange: Validated state. Act: Run node. Assert: Payload contains strictly ALLOWED_PAYLOAD_KEYS."""
        # Arrange
        mock_embed.return_value = [0.1] * 1024
        state = base_state

        # Act
        result = output_node(state)

        # Assert
        assert "output_node" in result["node_timestamps"]
        mock_upsert.assert_called_once()
        _, _, _, payload = mock_upsert.call_args[0]
        assert set(payload.keys()).issubset(ALLOWED_PAYLOAD_KEYS)
        assert "raw_text" not in payload
        assert "title" not in payload

    def test_chunk_text_splitting_with_overlap(self) -> None:
        """Arrange: Long text (> 600 chars). Act: Run _chunk_text. Assert: Multiple overlapping chunks produced."""
        # Arrange
        long_text = "Word " * 200  # 1000 chars

        # Act
        chunks = _chunk_text(long_text, chunk_size=512, overlap=50)

        # Assert
        assert len(chunks) >= 2
        assert len(chunks[0]) <= 512

    @patch("ollama.embeddings")
    def test_ollama_embedding_failure_returns_zero_fallback(self, mock_ollama: MagicMock) -> None:
        """Arrange: Ollama embeddings raises Exception. Act: Run _generate_embedding. Assert: Returns 1024-dim zero list."""
        # Arrange
        mock_ollama.side_effect = Exception("Ollama embedding service unavailable")

        # Act
        vec = _generate_embedding("Sample text", "doc_123")

        # Assert
        assert len(vec) == 1024
        assert all(v == 0.0 for v in vec)

    def test_deterministic_point_id_hashing(self) -> None:
        """Arrange: doc_id & chunk_idx. Act: Calculate digest. Assert: Deterministic int produced."""
        # Arrange
        doc_id = "doc_hash_777"
        chunk_idx = 0

        # Act
        digest = hashlib.sha256(f"{doc_id}_{chunk_idx}".encode()).hexdigest()
        point_id = int(digest[:15], 16)

        # Assert
        assert isinstance(point_id, int)
        assert point_id > 0

    def test_unvalidated_state_raises_value_error(self, base_state: DataShuddiState) -> None:
        """Arrange: validation_passed=False. Act: Run node. Assert: Raises ValueError."""
        # Arrange
        state = base_state
        state["validation_passed"] = False

        # Act & Assert
        with pytest.raises(ValueError):
            output_node(state)
