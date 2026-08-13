"""
DataShuddi API — Document Sanitization Submission Route Handler.
"""
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from loguru import logger

from src.agent.graph import build_graph
from src.agent.state import DataShuddiState, create_initial_state
from src.api.schemas import SanitizeResponse
from src.utils.config import settings
from src.utils.doc_utils import compute_doc_id, detect_mime_type

router = APIRouter(prefix="/api/v1", tags=["Sanitization"])


def _run_graph_in_background(initial_state: DataShuddiState, doc_id: str) -> None:
    """Execute LangGraph pipeline in a background worker task."""
    try:
        graph = build_graph(use_checkpointer=True)
        config = {"configurable": {"thread_id": doc_id}}
        graph.invoke(initial_state, config=config)
        logger.info("Background graph execution complete for doc_id: {}", doc_id)
    except Exception as exc:
        logger.error("Background graph execution failed for doc_id {}: {}", doc_id, exc)


@router.post(
    "/sanitize",
    response_model=SanitizeResponse,
    status_code=202,
    summary="Submit Document for PII Sanitization",
    description="Uploads an untrusted document (.pdf, .docx, .txt), computes SHA-256 doc_id, and dispatches background 8-node LangGraph processing.",
)
async def submit_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Document file to upload (.pdf, .docx, .txt)"),  # noqa: B008
    source_system: str = Form("local", description="Source system domain ('local' | 'confluence' | 'drive' | 'hr_docs' | 'legal' | 'medical')"),  # noqa: B008
) -> SanitizeResponse:
    """Accept document upload and start background sanitization pipeline."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a valid filename.")

    # Save uploaded file to raw data directory
    raw_dir: Path = settings.raw_data_dir
    raw_dir.mkdir(parents=True, exist_ok=True)
    target_path = raw_dir / file.filename

    contents = await file.read()
    target_path.write_bytes(contents)

    doc_id = compute_doc_id(target_path)
    mime_type = detect_mime_type(target_path)

    initial_state = create_initial_state(
        doc_id=doc_id,
        doc_path=str(target_path.resolve()),
        source_system=source_system,
        mime_type=mime_type,
        hf_threshold=settings.hf_threshold_default,
    )

    # Dispatch non-blocking background graph execution
    background_tasks.add_task(_run_graph_in_background, initial_state, doc_id)

    return SanitizeResponse(
        doc_id=doc_id,
        doc_name=file.filename,
        source_system=source_system,
        mime_type=mime_type,
        status="processing",
        message="Document submitted successfully and background sanitization pipeline started.",
    )
