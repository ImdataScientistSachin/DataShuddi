"""
DataShuddi API — Document Export Route Handler.
"""
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response

from src.agent.checkpoints import get_checkpointer
from src.utils.config import settings
from streamlit_app.ui_components import generate_sanitized_pdf

router = APIRouter(prefix="/api/v1", tags=["Export"])


@router.get(
    "/docs/{doc_id}/redacted",
    summary="Download Scrubbed or Visually Redacted Document",
    description="Retrieves the scrubbed clean text file (.txt) or generates a visual black-bar redacted PDF (.pdf) for download.",
)
async def download_redacted_doc(
    doc_id: str,
    format: str = Query("txt", description="Export format ('txt' | 'pdf')"),
) -> Response:
    """Download scrubbed text or redacted PDF binary for a given doc_id."""
    clean_dir = settings.raw_data_dir.parent / "clean"
    clean_txt_path = clean_dir / f"clean_{doc_id}.txt"

    if format.lower() == "pdf":
        # Search for original raw file matching doc_id
        raw_files = [f for f in settings.raw_data_dir.glob("*") if f.is_file() and doc_id in f.name]
        if not raw_files:
            raise HTTPException(status_code=404, detail=f"Original document file matching doc_id {doc_id} not found.")

        target_pdf = raw_files[0]
        if target_pdf.suffix.lower() != ".pdf":
            raise HTTPException(status_code=400, detail="Visual redaction PDF export is only supported for .pdf source files.")

        # Get checkpointer state for PII entities & HF candidates
        checkpointer = get_checkpointer()
        state_snapshot = checkpointer.get({"configurable": {"thread_id": doc_id}})
        if not state_snapshot or "channel_values" not in state_snapshot:
            raise HTTPException(status_code=404, detail="Document checkpointer state not found.")

        channel_values = cast(dict[str, Any], state_snapshot["channel_values"])
        pii_entities = channel_values.get("pii_entities", [])
        hf_candidates = channel_values.get("header_footer_candidates", [])

        temp_out = clean_dir / f"temp_redacted_{doc_id}.pdf"
        success = generate_sanitized_pdf(target_pdf, temp_out, pii_entities=pii_entities, hf_lines=hf_candidates)
        if not success or not temp_out.exists():
            raise HTTPException(status_code=500, detail="Failed to generate visually redacted PDF.")

        pdf_bytes = temp_out.read_bytes()
        try:
            temp_out.unlink()
        except Exception:
            pass

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=redacted_{doc_id}.pdf"},
        )

    # Default format: TXT
    if not clean_txt_path.exists():
        raise HTTPException(status_code=404, detail=f"Clean scrubbed text file for doc_id {doc_id} not found.")

    return FileResponse(
        path=clean_txt_path,
        media_type="text/plain",
        filename=f"clean_{doc_id}.txt",
    )
