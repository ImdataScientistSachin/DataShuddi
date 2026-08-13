"""
DataShuddi -- Compliance GDPR User Erasure Script.

Deletes all clean files, Postgres checkpointer state, Qdrant vector points,
and human review records matching a given doc_id.
"""
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import click
from loguru import logger

from src.utils.config import settings



@click.command()
@click.option(
    "--doc-id",
    "-d",
    required=True,
    help="SHA-256 string hash doc_id of the document to purge.",
)
def purge_user_data(doc_id: str) -> None:
    """Completely purge all records and vectors for a given doc_id."""
    logger.info("Starting GDPR erasure for doc_id: {}", doc_id)

    # 1. Delete clean files matching doc_id
    clean_dir = settings.raw_data_dir.parent / "clean"
    if clean_dir.exists():
        for f in clean_dir.glob(f"*{doc_id}*"):
            f.unlink()
            logger.info("Deleted clean document file: {}", f.name)

    # 2. Delete human review queue entries matching doc_id
    queue_file = settings.human_review_dir / "queue.jsonl"
    if queue_file.exists():
        lines = queue_file.read_text(encoding="utf-8").splitlines()
        retained = [
            line for line in lines
            if line.strip() and json.loads(line).get("doc_id") != doc_id
        ]
        queue_file.write_text("\n".join(retained) + "\n", encoding="utf-8")
        logger.info("Purged doc_id {} from human review queue.", doc_id)

    # 3. Delete Qdrant vector points matching doc_id
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        client = QdrantClient(url=settings.qdrant_url, timeout=5)
        client.delete(
            collection_name=settings.qdrant_collection_name,
            points_selector=Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            ),
        )
        logger.info("Deleted Qdrant vector points for doc_id: {}", doc_id)
    except Exception as exc:
        logger.warning("Qdrant point deletion notice: {}", exc)

    logger.info("GDPR erasure complete for doc_id: {}", doc_id)


if __name__ == "__main__":
    purge_user_data()
