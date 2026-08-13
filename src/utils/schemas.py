"""
DataShuddi -- Pydantic v2 EnterpriseDoc Schema.

Defines the EnterpriseDoc model that every document must conform to before
being ingested or upserted into Qdrant.

Validation rules:
    - title: must not be empty string.
    - content: minimum 100 characters in length.
    - content: must not contain unmasked PII patterns post-anonymization.
    - quality_score: float in [0.0, 1.0].
"""
import re

from pydantic import BaseModel, Field, field_validator

# Residual PII detection patterns for post-anonymization validation check
RESIDUAL_PII_PATTERNS: list[str] = [
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",                # Unmasked Email
    r"\b\d{3}-\d{2}-\d{4}\b",                                              # Unmasked SSN
    r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b",      # Unmasked Credit Card (Visa/MasterCard/Amex)
]


class EnterpriseDoc(BaseModel):
    """Pydantic v2 schema for validated, scrubbed enterprise documents."""

    doc_id: str = Field(..., description="SHA-256 string hash of source document")
    title: str = Field(..., description="Document title or filename")
    content: str = Field(..., description="Masked, scrubbed text content")
    source_system: str = Field(default="local", description="Ingress source origin")
    quality_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Composite document quality score")

    @field_validator("title")
    @classmethod
    def validate_title_non_empty(cls, v: str) -> str:
        """Validate that title is non-empty."""
        if not v or not v.strip():
            raise ValueError("Document title must not be empty.")
        return v.strip()

    @field_validator("content")
    @classmethod
    def validate_content_length_and_residual_pii(cls, v: str) -> str:
        """Validate content minimum length (>=100 chars) and post-masking PII absence."""
        if len(v.strip()) < 100:
            raise ValueError(
                f"Document content length ({len(v.strip())} chars) is below minimum threshold of 100 chars."
            )

        for pattern in RESIDUAL_PII_PATTERNS:
            if re.search(pattern, v):
                raise ValueError(
                    f"Residual unmasked PII pattern matched post-anonymization: {pattern}"
                )

        return v
