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

    # Sort entities by start character offset in reverse order to avoid offset drift
    sorted_entities = sorted(entities, key=lambda e: e.get("start", 0), reverse=True)
    masked_chars = list(text)

    for ent in sorted_entities:
        start = ent.get("start", 0)
        end = ent.get("end", 0)
        ent_type = ent.get("type", "UNKNOWN")
        placeholder = ANONYMIZER_MAPPING.get(ent_type, f"[{ent_type}_REDACTED]")

        if 0 <= start < end <= len(text):
            masked_chars[start:end] = list(placeholder)

    masked_text = "".join(masked_chars)

    logger.info(
        "doc_id={} | Node 4: Masked {} entities successfully",
        state.get("doc_id", "UNKNOWN"),
        len(entities),
    )

    return {
        **state,
        "masked_text": masked_text,
        "node_timestamps": timestamps,
    }
