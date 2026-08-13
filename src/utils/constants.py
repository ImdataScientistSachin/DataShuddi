"""
DataShuddi -- System Constants and Policy Allowlists.

Central repository for payload allowlists, security regex patterns,
Presidio entity definitions, and domain risk classifications.
"""
from typing import Final

# Strict Qdrant vector metadata payload allowlist (Blueprint-mandated)
# Zero raw text, unscrubbed titles, author names, or emails allowed in metadata.
ALLOWED_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset({
    "doc_id",           # SHA-256 string hash
    "chunk_index",      # Integer chunk index
    "source_system",    # String ("local" | "confluence" | "drive")
    "quality_score",    # Float (0.0 - 1.0)
    "hf_lines_removed", # Integer count
    "pii_scrubbed",     # Boolean flag
})

# Prompt injection patterns to detect and strip in Node 0 (Security Sanitizer)
INJECTION_PATTERNS: Final[list[str]] = [
    r"(?i)ignore\s+(all\s+)?previous\s+instructions",
    r"(?i)you\s+are\s+now\s+a",
    r"(?i)system\s+prompt",
    r"(?i)override\s+safety\s+guidelines",
    r"(?i)output\s+the\s+following\s+secret",
    r"(?i)disregard\s+(your\s+)?instructions",
    r"(?i)act\s+as\s+(if\s+you\s+are|a)",
    r"(?i)jailbreak",
    r"(?i)DAN\s+mode",
]

# Source systems classified as high-risk domains for contextual PII (Node 3 Layer 2)
HIGH_RISK_DOMAINS: Final[set[str]] = {"hr_docs", "hr_salary", "hr_contracts", "legal", "medical"}

# Presidio entity types to detect in Node 3 Layer 1
PRESIDIO_ENTITIES: Final[list[str]] = [
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "US_SSN",
    "CREDIT_CARD",
    "PERSON",
    "IP_ADDRESS",
    "URL",
    "IBAN_CODE",
]

# Safe anonymization placeholder mapping for Node 4 (PII Masker)
ANONYMIZER_MAPPING: Final[dict[str, str]] = {
    "EMAIL_ADDRESS": "[EMAIL_REDACTED]",
    "PHONE_NUMBER": "[PHONE_REDACTED]",
    "US_SSN": "[SSN_REDACTED]",
    "CREDIT_CARD": "[CREDIT_CARD_REDACTED]",
    "PERSON": "[PERSON_REDACTED]",
    "IP_ADDRESS": "[IP_REDACTED]",
    "URL": "[URL_REDACTED]",
    "IBAN_CODE": "[IBAN_REDACTED]",
}
