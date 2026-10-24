"""
DataShuddi -- Human Feedback Reprocessing Script.

Reads human feedback resolutions from data/human_review/queue.jsonl,
applies updated thresholds to Store, and re-invokes the pipeline.
"""
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import click
from loguru import logger

from src.agent.graph import build_graph
from src.agent.state import DataShuddiState
from src.utils.config import settings
from src.utils.doc_utils import compute_doc_id, detect_mime_type


@click.command()
@click.option(
    "--queue-file",
    default=str(settings.human_review_dir / "queue.jsonl"),
    help="Path to the human review queue file.",
)
def reprocess_human_feedback(queue_file: str) -> None:
    """Reprocess escalated documents with updated human feedback."""
    qpath = Path(queue_file)
    if not qpath.exists():
        logger.info("Human review queue file {} does not exist. Nothing to reprocess.", qpath)
        return

    lines = [line.strip() for line in qpath.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        logger.info("Human review queue is empty.")
        return

    graph = build_graph(use_checkpointer=True)
    reprocessed_count = 0

    for line in lines:
        item = json.loads(line)
        doc_path = Path(item["doc_path"])

        if not doc_path.exists():
            logger.warning("Document file {} no longer exists. Skipping.", doc_path)
            continue

        doc_id = compute_doc_id(doc_path)
        mime_type = detect_mime_type(doc_path)

        state: DataShuddiState = {
            "doc_id": doc_id,
            "doc_path": str(doc_path.resolve()),
            "source_system": item.get("source_system", "local"),
            "mime_type": mime_type,
            "raw_text": "",
            "_pages": [],
            "cleaned_text": "",
            "masked_text": "",
            "header_footer_candidates": [],
            "pii_entities": [],
            "pii_count": 0,
            "validation_errors": [],
            "validation_passed": False,
            "retry_count": 0,
            "reflection_text": "Human review reprocess",
            "reflector_confidence": 1.0,
            "needs_human_review": False,
            "hf_threshold": 0.25,  # Human adjusted threshold
            "is_sanitized": False,
            "security_flags": [],
            "quality_score": 0.0,
            "node_timestamps": {},
            "processing_time_ms": 0,
            "_start_time": 0.0,
        }

        try:
            graph.invoke(state, config={"configurable": {"thread_id": doc_id}})
            reprocessed_count += 1
            logger.info("Reprocessed document: {}", doc_id)
        except Exception as exc:
            logger.error("Failed to reprocess document {}: {}", doc_id, exc)

    logger.info("Reprocessing complete. Total reprocessed: {}", reprocessed_count)


if __name__ == "__main__":
    reprocess_human_feedback()
