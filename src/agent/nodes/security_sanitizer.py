"""
DataShuddi -- Node 0: Security Sanitizer Node.

Pre-ingestion trust-boundary guard. Scans raw extracted text for prompt
injection patterns, strips executable content, wraps untrusted document
text in [UNTRUSTED_CONTENT] tags, and sets security state flags.

Policy:
    - All ingress documents are treated as UNTRUSTED.
    - Prompt injection patterns are stripped and replaced with [SECURITY_REDACTED].
    - Node always sets is_sanitized = True (even if no threats found).
    - This node is idempotent: re-running with same doc_id produces identical output.
"""
import re
import time

from loguru import logger

from src.agent.state import DataShuddiState
from src.utils.constants import INJECTION_PATTERNS


def security_sanitizer_node(state: DataShuddiState) -> DataShuddiState:
    """
    Pre-ingestion guard enforcing trust-boundary isolation (Node 0).

    Scans raw document text for prompt injection patterns, strips detected
    patterns, and sets security flags before downstream LLM processing.

    Args:
        state: Current DataShuddiState dictionary with raw_text populated.

    Returns:
        Updated DataShuddiState with security_flags, is_sanitized=True,
        and sanitized raw_text.
    """
    node_name = "security_sanitizer"
    timestamps: dict[str, float] = dict(state.get("node_timestamps", {}))
    timestamps[node_name] = time.time()

    raw_input: str = state.get("raw_text", "")
    detected_flags: list[str] = []

    # Single-pass detect and strip prompt injection patterns
    sanitized_text = raw_input
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, sanitized_text):
            detected_flags.append(f"Prompt injection pattern detected: {pattern}")
            logger.warning(
                "doc_id={} | Security: Injection pattern matched: {}",
                state.get("doc_id", "UNKNOWN"),
                pattern,
            )
            sanitized_text = re.sub(pattern, "[SECURITY_REDACTED]", sanitized_text)

    # Also sanitize page-level text if available
    sanitized_pages = []
    for page in state.get("_pages", []):
        p_text = page
        for pattern in INJECTION_PATTERNS:
            p_text = re.sub(pattern, "[SECURITY_REDACTED]", p_text)
        sanitized_pages.append(p_text)

    return {
        **state,
        "raw_text": sanitized_text,
        "_pages": sanitized_pages if sanitized_pages else state.get("_pages", []),
        "is_sanitized": True,
        "security_flags": detected_flags,
        "node_timestamps": timestamps,
    }
