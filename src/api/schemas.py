"""
DataShuddi API — Pydantic v2 Schema Definitions.

Data contracts for REST API request/response payloads.
"""
from pydantic import BaseModel, Field


class SanitizeResponse(BaseModel):
    """Response returned upon submitting a document for sanitization."""

    doc_id: str = Field(..., description="SHA-256 string hash unique document identifier")
    doc_name: str = Field(..., description="Original filename of the submitted document")
    source_system: str = Field(..., description="Source system domain classification")
    mime_type: str = Field(..., description="Detected MIME type")
    status: str = Field(..., description="Job execution status ('processing' | 'completed' | 'failed' | 'human_review')")
    message: str = Field(..., description="Human-readable status summary")


class JobStatusResponse(BaseModel):
    """Detailed job status and telemetry response."""

    doc_id: str = Field(..., description="SHA-256 string hash unique document identifier")
    status: str = Field(..., description="Job execution status ('completed' | 'failed' | 'human_review' | 'not_found')")
    validation_passed: bool = Field(False, description="True if document passed schema validation")
    needs_human_review: bool = Field(False, description="True if escalated to human review queue")
    pii_count: int = Field(0, description="Total count of scrubbed PII entities")
    quality_score: float = Field(0.0, description="Composite quality score [0.0, 1.0]")
    node_timestamps: dict[str, float] = Field(default_factory=dict, description="Execution timestamps per node")
    processing_time_ms: int = Field(0, description="Total pipeline processing duration in milliseconds")
    validation_errors: list[str] = Field(default_factory=list, description="Validation failure messages if any")
    security_flags: list[str] = Field(default_factory=list, description="Triggered security flags if any")


class GDPRPurgeRequest(BaseModel):
    """Request payload for GDPR Article 17 user data erasure."""

    doc_id: str = Field(..., description="SHA-256 string hash doc_id of the document to purge")


class GDPRPurgeResponse(BaseModel):
    """Response returned after executing GDPR data erasure."""

    doc_id: str = Field(..., description="SHA-256 doc_id purged")
    status: str = Field("success", description="Purge operation status")
    files_deleted: int = Field(0, description="Count of clean/temp files deleted")
    vectors_deleted: bool = Field(False, description="True if Qdrant points were deleted")
    queue_purged: bool = Field(False, description="True if human review queue was updated")


class HealthCheckResponse(BaseModel):
    """Multi-service infrastructure health status response."""

    status: str = Field("ok", description="Overall API health status ('ok' | 'degraded')")
    postgres_online: bool = Field(False, description="PostgreSQL checkpointer connectivity status")
    qdrant_online: bool = Field(False, description="Qdrant vector engine connectivity status")
    ollama_online: bool = Field(False, description="Ollama model server connectivity status")
    timestamp: float = Field(..., description="Unix timestamp of health check")
