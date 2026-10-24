"""
DataShuddi -- Node 4: PII Masker Node.

Applies Presidio Anonymizer and string substitution to replace all detected
PII entities in cleaned_text with safe placeholder tokens, producing masked_text.

Placeholder mapping (blueprint-mandated):
    EMAIL_ADDRESS  -> [EMAIL_REDACTED]
    PHONE_NUMBER   -> [PHONE_REDACTED]
    US_SSN         -> [SSN_REDACTED]
    CREDIT_CARD    -> [CREDIT_CARD_REDACTED]
    PERSON         -> [PERSON_REDACTED]
    IP_ADDRESS     -> [IP_REDACTED]
    URL            -> [URL_REDACTED]
    IBAN_CODE      -> [IBAN_REDACTED]

Policy:
    - masked_text is the ONLY text passed downstream to Node 5+.
    - Raw unmasked text is NEVER logged or saved to metadata.
    - Idempotent: re-running with already masked text produces identical output.
"""
import time
from typing import Any

from loguru import logger

from src.agent.state import DataShuddiState
from src.utils.constants import ANONYMIZER_MAPPING


def _resolve_overlapping_entities(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Resolve overlapping PII entity spans by prioritizing higher score and wider span.

    Guarantees non-overlapping intervals so string replacements never corrupt adjacent tokens.
    """
    if not entities:
        return []

    # Sort entities by priority: specific types > score > span length
    priority_types = {"EMAIL_ADDRESS": 3, "US_SSN": 3, "CREDIT_CARD": 3, "PHONE_NUMBER": 2, "PERSON": 2}
    sorted_by_priority = sorted(
        entities,
        key=lambda e: (
            priority_types.get(e.get("type", ""), 1),
            e.get("score", 0.0),
            e.get("end", 0) - e.get("start", 0),
        ),
        reverse=True,
    )

    non_overlapping: list[dict[str, Any]] = []

    for candidate in sorted_by_priority:
        c_start = candidate.get("start", 0)
        c_end = candidate.get("end", 0)
        if c_start >= c_end:
            continue

        # Check for overlap against already selected entities
        overlaps = any(
            not (c_end <= selected.get("start", 0) or c_start >= selected.get("end", 0))
            for selected in non_overlapping
        )
        if not overlaps:
            non_overlapping.append(candidate)

    return sorted(non_overlapping, key=lambda e: e.get("start", 0))


def pii_masker_node(state: DataShuddiState) -> DataShuddiState:
    """
    Node 4: Apply Presidio Anonymizer and token substitution to produce masked_text.

    Args:
        state: Current DataShuddiState with cleaned_text and pii_entities set.

    Returns:
        Updated DataShuddiState with masked_text populated.
    """
    node_name = "pii_masker"
    timestamps: dict[str, float] = dict(state.get("node_timestamps", {}))
    timestamps[node_name] = time.time()

    text: str = state.get("cleaned_text", "")
    entities: list[dict[str, Any]] = state.get("pii_entities", [])

    if not entities or not text:
        logger.info("doc_id={} | Node 4: Zero entities to mask", state.get("doc_id", "UNKNOWN"))
        return {
            **state,
            "masked_text": text,
            "node_timestamps": timestamps,
        }

    # Resolve overlapping spans (e.g. EMAIL containing URL domain)
    resolved_entities = _resolve_overlapping_entities(entities)

    # Sort entities in descending order of start offset to prevent position drift
    sorted_entities = sorted(resolved_entities, key=lambda e: e.get("start", 0), reverse=True)
    masked_text = text

    for ent in sorted_entities:
        start = ent.get("start", 0)
        end = ent.get("end", 0)
        ent_type = ent.get("type", "UNKNOWN")
        placeholder = ANONYMIZER_MAPPING.get(ent_type, f"[{ent_type}_REDACTED]")

        if 0 <= start < end <= len(masked_text):
            masked_text = masked_text[:start] + placeholder + masked_text[end:]

    logger.info(
        "doc_id={} | Node 4: Masked {} entities successfully",
        state.get("doc_id", "UNKNOWN"),
        len(resolved_entities),
    )

    return {
        **state,
        "masked_text": masked_text,
        "node_timestamps": timestamps,
    }

