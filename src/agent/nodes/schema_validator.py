"""
DataShuddi -- Node 5: Schema Validator Node.

Validates the masked document against the Pydantic v2 EnterpriseDoc model.
Calculates composite quality_score and sets validation_passed flag.

Policy:
    - Documents failing validation NEVER reach Node 7 or Qdrant.
    - Validation error messages log error types only -- zero raw text in logs.
"""
import time
from pathlib import Path

from loguru import logger
from pydantic import ValidationError

from src.agent.state import DataShuddiState
from src.utils.schemas import EnterpriseDoc


def schema_validator_node(state: DataShuddiState) -> DataShuddiState:
    """
    Node 5: Pydantic v2 EnterpriseDoc validation & composite quality scoring.

    Args:
        state: Current DataShuddiState with masked_text populated.

    Returns:
        Updated DataShuddiState with validation_passed, validation_errors,
        and quality_score populated.
    """
    node_name = "schema_validator"
    timestamps: dict[str, float] = dict(state.get("node_timestamps", {}))
    timestamps[node_name] = time.time()

    masked_text: str = state.get("masked_text", "")
    doc_path = Path(state.get("doc_path", "unknown_document.pdf"))
    title = doc_path.name or state.get("doc_id", "unnamed_document")

    # Calculate composite quality score
    quality_score = _calculate_quality_score(
        masked_text=masked_text,
        hf_removed=len(state.get("header_footer_candidates", [])),
        pii_count=state.get("pii_count", 0),
    )

    validation_errors: list[str] = []
    validation_passed = False

    try:
        EnterpriseDoc(
            doc_id=state.get("doc_id", "unknown_hash"),
            title=title,
            content=masked_text,
            source_system=state.get("source_system", "local"),
            quality_score=quality_score,
        )
        validation_passed = True
        logger.info(
            "doc_id={} | Node 5: Schema validation PASSED (quality={:.2f})",
            state.get("doc_id", "UNKNOWN"),
            quality_score,
        )

    except ValidationError as exc:
        validation_passed = False
        for err in exc.errors():
            msg = f"Validation Error ({err.get('type', 'value_error')}): {err.get('msg', '')}"
            validation_errors.append(msg)
            logger.warning(
                "doc_id={} | Node 5: Schema validation FAILED -- {}",
                state.get("doc_id", "UNKNOWN"),
                msg,
            )

    return {
        **state,
        "validation_passed": validation_passed,
        "validation_errors": validation_errors,
        "quality_score": quality_score,
        "node_timestamps": timestamps,
    }


def _calculate_quality_score(masked_text: str, hf_removed: int, pii_count: int) -> float:
    """
    Calculate composite quality score in range [0.0, 1.0].

    High content length and clean sanitization yield 1.0. Short content is penalized.
    """
    content_len = len(masked_text.strip())
    if content_len < 100:
        content_score = content_len / 100.0
    else:
        content_score = 1.0

    # Clean processing completeness score
    cleanliness_score = 1.0

    composite = (0.7 * content_score) + (0.3 * cleanliness_score)
    return round(min(1.0, max(0.0, composite)), 2)
