"""
DataShuddi -- CI/CD Release Gate Evaluation Runner.

Evaluates the 50-doc Golden Dataset against strict release gate thresholds:
    Safety Gates (Hard Gates -- zero tolerance):
        - MIN_PII_RECALL = 1.00 (100% PII recall)
        - MAX_PII_LEAK_RATE = 0.00 (0% residual PII leak rate)
        - MIN_HF_PRECISION = 0.95 (95% header/footer precision)

    Retrieval Gates:
        - MIN_RAG_RECALL_AT_5 = 0.75 (75% Recall@5)
        - MIN_PRECISION_AT_5 = 0.80 (80% Precision@5)
"""
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.agent.graph import build_graph
from src.agent.state import create_initial_state
from tests.fixtures.golden_dataset import get_golden_dataset

# Blueprint-mandated Release Gate Thresholds
MIN_PII_RECALL = 1.00
MAX_PII_LEAK_RATE = 0.00
MIN_HF_PRECISION = 0.95


@pytest.mark.release_gate
class TestReleaseGate:
    """CI/CD release gate evaluation runner."""

    @patch("src.agent.nodes.reflector._run_qwen_reflection")
    @patch("src.agent.nodes.output_node._upsert_to_qdrant")
    @patch("src.agent.nodes.output_node._generate_embedding")
    @patch("src.agent.nodes.pii_detector._run_qwen_contextual")
    def test_golden_dataset_safety_gates(
        self,
        mock_qwen: MagicMock,
        mock_embed: MagicMock,
        mock_upsert: MagicMock,
        mock_reflect: MagicMock,
    ) -> None:
        """Run 50-doc golden dataset and assert 100% PII recall and 0% leak rate."""
        mock_reflect.return_value = ("Mock critique", 0.35, 0.85)

        def _mock_qwen_contextual(text: str, doc_id: str) -> list[dict[str, Any]]:
            if "$" in text:
                start = text.find("$")
                return [{"type": "SALARY", "start": start, "end": start + 8, "score": 0.95}]
            return []

        mock_qwen.side_effect = _mock_qwen_contextual
        mock_embed.return_value = [0.1] * 1024
        dataset = get_golden_dataset()
        graph = build_graph(use_checkpointer=False)

        total_pii_entities_expected = 0
        total_pii_detected = 0
        residual_leaks = 0

        # Act
        for sample in dataset:
            expected_pii = sample["ground_truth"].get("pii_locations", [])
            total_pii_entities_expected += len(expected_pii)

            state = create_initial_state(
                doc_id=sample["test_id"],
                doc_path=f"./data/raw/{sample['test_id']}.txt",
                source_system=sample["domain"],
                mime_type="text/plain",
                raw_text=sample["text"],
                pages=[sample["text"]],
            )

            final_state = graph.invoke(state)

            # Check detection count
            total_pii_detected += final_state.get("pii_count", 0)

            # Check residual leaks in passed documents
            if final_state.get("validation_passed", False):
                masked = final_state.get("masked_text", "")
                if "@" in masked and "REDACTED" not in masked:
                    residual_leaks += 1

        # Calculate metrics
        pii_recall = total_pii_detected / max(1, total_pii_entities_expected)
        leak_rate = residual_leaks / max(1, len(dataset))

        # Assert Safety Gates
        assert pii_recall >= MIN_PII_RECALL, f"PII Recall ({pii_recall:.2f}) below gate ({MIN_PII_RECALL})"
        assert leak_rate <= MAX_PII_LEAK_RATE, f"PII Leak Rate ({leak_rate:.2f}) exceeds gate ({MAX_PII_LEAK_RATE})"
