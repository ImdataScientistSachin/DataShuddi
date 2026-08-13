"""
DataShuddi -- Node 6: Reflector Node (Self-Correction Loop).

Runs on validation failure paths from Node 5.
Uses qwen2.5-coder:14b (CPU mode) to critique why validation failed and
proposes dynamic threshold adjustments to the header/footer detector (Node 2).

Self-correction policy (blueprint-mandated):
    - Confidence Gate: Only updates threshold if reflector_confidence >= 0.70.
    - Max Delta Cap: Threshold adjustment capped at +-0.05 per retry iteration.
    - Human Escalation: Escalates to human review queue if retry_count >= 3 or pii_count > 50.
"""
import json
import time
from typing import Any

from loguru import logger

from src.agent.state import DataShuddiState
from src.utils.config import settings

# Prompt template for Qwen14b Reflector critique
REFLECTOR_PROMPT_TEMPLATE = """You are a senior data pipeline diagnostic agent. A document failed schema validation.

Document ID: {doc_id}
Validation Errors: {validation_errors}
Current H/F Threshold: {current_threshold}
Detected PII Count: {pii_count}

Analyze why validation failed and recommend an updated H/F detection threshold (range 0.10 to 0.50).
Current threshold delta MUST NOT exceed 0.05.

Return ONLY valid JSON in this exact format:
{{
    "critique": "Explanation of failure cause",
    "recommended_threshold": 0.35,
    "confidence": 0.85
}}"""


def reflector_node(state: DataShuddiState) -> DataShuddiState:
    """
    Node 6: Qwen14b CPU Reflector with confidence gate & threshold adjustment.

    Args:
        state: Current DataShuddiState with validation_errors populated.

    Returns:
        Updated DataShuddiState with hf_threshold, reflection_text,
        reflector_confidence, retry_count, and needs_human_review.
    """
    node_name = "reflector"
    timestamps: dict[str, float] = dict(state.get("node_timestamps", {}))
    timestamps[node_name] = time.time()

    retry_count = state.get("retry_count", 0) + 1
    pii_count = state.get("pii_count", 0)
    current_threshold = state.get("hf_threshold", settings.hf_threshold_default)

    # Check human escalation triggers
    if retry_count >= settings.max_retry_count or pii_count > settings.pii_escalation_threshold:
        logger.warning(
            "doc_id={} | Escalating to Human Review Queue (retry={}, pii_count={})",
            state.get("doc_id", "UNKNOWN"),
            retry_count,
            pii_count,
        )
        _write_to_human_review_queue(state)
        return {
            **state,
            "retry_count": retry_count,
            "needs_human_review": True,
            "node_timestamps": timestamps,
        }

    # Run Qwen14b CPU critique
    critique, recommended_threshold, confidence = _run_qwen_reflection(
        doc_id=state.get("doc_id", "UNKNOWN"),
        validation_errors=state.get("validation_errors", []),
        current_threshold=current_threshold,
        pii_count=pii_count,
    )

    # Enforce Confidence Gate (confidence >= 0.70)
    new_threshold = current_threshold
    if confidence >= settings.reflector_confidence_gate:
        delta = recommended_threshold - current_threshold
        capped_delta = max(-settings.reflector_max_delta, min(settings.reflector_max_delta, delta))
        raw_new_threshold = round(current_threshold + capped_delta, 2)
        new_threshold = max(0.10, min(0.50, raw_new_threshold))

        logger.info(
            "doc_id={} | Reflector adjusted H/F threshold: {:.2f} -> {:.2f} (conf={:.2f})",
            state.get("doc_id", "UNKNOWN"),
            current_threshold,
            new_threshold,
            confidence,
        )
    else:
        logger.warning(
            "doc_id={} | Reflector confidence ({:.2f}) below gate ({:.2f}) -- threshold unchanged",
            state.get("doc_id", "UNKNOWN"),
            confidence,
            settings.reflector_confidence_gate,
        )

    return {
        **state,
        "retry_count": retry_count,
        "reflection_text": critique,
        "reflector_confidence": confidence,
        "hf_threshold": new_threshold,
        "needs_human_review": False,
        "node_timestamps": timestamps,
    }


def _run_qwen_reflection(
    doc_id: str,
    validation_errors: list[str],
    current_threshold: float,
    pii_count: int,
) -> tuple[str, float, float]:
    """Run Qwen2.5-coder:14b CPU via Ollama for critique JSON."""
    import ollama

    prompt = REFLECTOR_PROMPT_TEMPLATE.format(
        doc_id=doc_id,
        validation_errors="; ".join(validation_errors),
        current_threshold=current_threshold,
        pii_count=pii_count,
    )

    try:
        response = ollama.chat(
            model=settings.ollama_reflector_model,
            messages=[{"role": "user", "content": prompt}],
            format="json",
        )
        parsed: dict[str, Any] = json.loads(response["message"]["content"])
        critique = str(parsed.get("critique", "Validation failure critique"))
        recommended = float(parsed.get("recommended_threshold", current_threshold))
        confidence = float(parsed.get("confidence", 0.5))
        return critique, recommended, confidence
    except Exception as exc:
        logger.warning("doc_id={} | Qwen14b Reflector failed: {}", doc_id, exc)
        return "Reflector fallback critique", current_threshold, 0.5


def _write_to_human_review_queue(state: DataShuddiState) -> None:
    """Write failed document metadata to human review queue (queue.jsonl)."""
    queue_dir = settings.human_review_dir
    queue_dir.mkdir(parents=True, exist_ok=True)
    queue_file = queue_dir / "queue.jsonl"

    record = {
        "doc_id": state.get("doc_id", "UNKNOWN"),
        "doc_path": state.get("doc_path", ""),
        "source_system": state.get("source_system", "local"),
        "validation_errors": state.get("validation_errors", []),
        "retry_count": state.get("retry_count", 0),
        "pii_count": state.get("pii_count", 0),
        "timestamp": time.time(),
    }

    with open(queue_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
