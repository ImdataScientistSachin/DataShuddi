"""
DataShuddi API — Job Status Route Handler.
"""
from typing import Any, cast

from fastapi import APIRouter, HTTPException
from loguru import logger

from src.agent.checkpoints import get_checkpointer
from src.api.schemas import JobStatusResponse

router = APIRouter(prefix="/api/v1", tags=["Jobs"])


@router.get(
    "/jobs/{doc_id}",
    response_model=JobStatusResponse,
    summary="Get Document Processing Job Status",
    description="Fetches real-time thread checkpointer state, execution timestamps, quality score, and validation status for a document.",
)
async def get_job_status(doc_id: str) -> JobStatusResponse:
    """Retrieve job telemetry and state for a given doc_id."""
    try:
        checkpointer = get_checkpointer()
        config = {"configurable": {"thread_id": doc_id}}

        # Get latest checkpoint state
        state_snapshot = checkpointer.get(config)
        if not state_snapshot or "channel_values" not in state_snapshot:
            return JobStatusResponse(
                doc_id=doc_id,
                status="not_found",
                validation_passed=False,
                needs_human_review=False,
                pii_count=0,
                quality_score=0.0,
                processing_time_ms=0,
            )

        channel_values = cast(dict[str, Any], state_snapshot["channel_values"])
        val_passed = channel_values.get("validation_passed", False)
        needs_review = channel_values.get("needs_human_review", False)

        if needs_review:
            status_str = "human_review"
        elif val_passed:
            status_str = "completed"
        else:
            status_str = "failed"

        return JobStatusResponse(
            doc_id=doc_id,
            status=status_str,
            validation_passed=val_passed,
            needs_human_review=needs_review,
            pii_count=channel_values.get("pii_count", 0),
            quality_score=channel_values.get("quality_score", 0.0),
            node_timestamps=channel_values.get("node_timestamps", {}),
            processing_time_ms=channel_values.get("processing_time_ms", 0),
            validation_errors=channel_values.get("validation_errors", []),
            security_flags=channel_values.get("security_flags", []),
        )
    except Exception as exc:
        logger.error("Failed to fetch job status for doc_id {}: {}", doc_id, exc)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve job status: {exc}") from exc
