"""
DataShuddi -- Loguru PII-Scrubbing Middleware.

Configures a Loguru log patcher that strips sensitive document fields from ALL
log records before they are written to stdout or transmitted to LangSmith.

Fields stripped from log records:
    - raw_text
    - masked_text
    - cleaned_text
    - _pages
    - pii_entities (raw entity strings)
"""
import sys
from typing import Any

from loguru import logger

# Sensitive state keys that must never appear in log output
SENSITIVE_KEYS: set[str] = {"raw_text", "masked_text", "cleaned_text", "_pages"}


def scrub_pii_from_record(record: Any) -> None:
    """
    Loguru patcher function to strip sensitive attributes from extra parameters.

    Args:
        record: Loguru record dictionary to patch in-place.
    """
    extra = record.get("extra", {})
    if not extra:
        return

    for key in list(extra.keys()):
        if key in SENSITIVE_KEYS:
            extra[key] = "[REDACTED_FROM_LOG]"
        elif key == "pii_entities" and isinstance(extra[key], list):
            # Scrub raw text values from entity list, keeping only types and counts
            scrubbed_entities = []
            for ent in extra[key]:
                if isinstance(ent, dict):
                    scrubbed_entities.append({
                        "type": ent.get("type", "UNKNOWN"),
                        "score": ent.get("score", 0.0),
                    })
            extra[key] = scrubbed_entities


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configure Loguru logger with PII scrubbing patcher.

    Args:
        log_level: Log level string ("DEBUG", "INFO", "WARNING", "ERROR").
    """
    logger.remove()  # Remove default handler
    logger.configure(patcher=scrub_pii_from_record)
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:7}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )
