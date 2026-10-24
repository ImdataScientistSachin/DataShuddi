"""
DataShuddi API — Compliance Admin Data Purge Route Handler.
"""
import json

from fastapi import APIRouter, Depends, Header, HTTPException, status
from loguru import logger

from src.api.schemas import GDPRPurgeRequest, GDPRPurgeResponse
from src.utils.config import settings

router = APIRouter(prefix="/api/v1/admin", tags=["Admin & Compliance"])


async def verify_admin_key(x_api_key: str | None = Header(None, alias="X-API-Key")) -> str:
    """Verify administrator API key for compliance management operations."""
    if settings.admin_api_key:
        if not x_api_key or x_api_key != settings.admin_api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing administrator API key (X-API-Key).",
            )
    return x_api_key or "dev_mode"


@router.post(
    "/purge",
    response_model=GDPRPurgeResponse,
    summary="Execute Complete GDPR User Data Erasure",
    description="Completely purges clean files, Qdrant vector points, and human review queue records matching the given doc_id.",
)
async def purge_document_data(
    body: GDPRPurgeRequest,
    _auth: str = Depends(verify_admin_key),
) -> GDPRPurgeResponse:
    """Purge all document data across filesystem, vectors, and review queues."""
    doc_id = body.doc_id
    files_deleted = 0
    vectors_deleted = False
    queue_purged = False

    logger.info("API GDPR Purge requested for doc_id: {}", doc_id)

    # 1. Clean files deletion
    clean_dir = settings.raw_data_dir.parent / "clean"
    if clean_dir.exists():
        for f in clean_dir.glob(f"*{doc_id}*"):
            try:
                f.unlink()
                files_deleted += 1
                logger.info("Deleted clean file: {}", f.name)
            except Exception as exc:
                logger.warning("Failed to delete file {}: {}", f.name, exc)

    # 2. Human review queue purge
    queue_file = settings.human_review_dir / "queue.jsonl"
    if queue_file.exists():
        try:
            lines = queue_file.read_text(encoding="utf-8").splitlines()
            retained = [
                line for line in lines
                if line.strip() and json.loads(line).get("doc_id") != doc_id
            ]
            if len(retained) < len(lines):
                queue_file.write_text("\n".join(retained) + "\n", encoding="utf-8")
                queue_purged = True
                logger.info("Purged doc_id {} from human review queue.", doc_id)
        except Exception as exc:
            logger.warning("Failed to purge human review queue: {}", exc)

    # 3. Qdrant vector points deletion
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=10,
        )
        client.delete(
            collection_name=settings.qdrant_collection_name,
            points_selector=Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            ),
        )
        vectors_deleted = True
        logger.info("Deleted Qdrant vector points for doc_id: {}", doc_id)
    except Exception as exc:
        logger.warning("Qdrant point deletion notice: {}", exc)

    return GDPRPurgeResponse(
        doc_id=doc_id,
        status="success",
        files_deleted=files_deleted,
        vectors_deleted=vectors_deleted,
        queue_purged=queue_purged,
    )
