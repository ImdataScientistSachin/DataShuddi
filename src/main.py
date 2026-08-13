"""
DataShuddi -- Canonical CLI Entry Point.

Processes an untrusted document through the 8-node DataShuddi LangGraph pipeline.
"""
import sys
import time
from pathlib import Path

# Ensure root directory and .venv site-packages are on sys.path for direct script invocation
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

venv_site_pkgs = ROOT_DIR / ".venv" / "Lib" / "site-packages"
if venv_site_pkgs.exists() and str(venv_site_pkgs) not in sys.path:
    sys.path.insert(0, str(venv_site_pkgs))

import click  # noqa: E402
from loguru import logger  # noqa: E402

from src.agent.graph import build_graph  # noqa: E402
from src.agent.state import create_initial_state  # noqa: E402
from src.utils.doc_utils import compute_doc_id, detect_mime_type  # noqa: E402
from src.utils.logging_hygiene import configure_logging  # noqa: E402


@click.command()
@click.option(
    "--file",
    "-f",
    "file_path",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to the untrusted document file (PDF, DOCX, TXT).",
)
@click.option(
    "--source",
    "-s",
    "source_system",
    default="local",
    help="Source system classification (local, confluence, drive, hr_docs, legal, medical).",
)
@click.option(
    "--no-checkpointer",
    is_flag=True,
    default=False,
    help="Disable PostgreSQL checkpointer for lightweight execution.",
)
def run_pipeline(file_path: Path, source_system: str, no_checkpointer: bool) -> None:
    """Run DataShuddi pipeline on a single document."""
    configure_logging()
    logger.info("Starting DataShuddi pipeline for document: {}", file_path)

    start_time = time.time()
    doc_id = compute_doc_id(file_path)
    mime_type = detect_mime_type(file_path)

    initial_state = create_initial_state(
        doc_id=doc_id,
        doc_path=str(file_path.resolve()),
        source_system=source_system,
        mime_type=mime_type,
    )

    graph = build_graph(use_checkpointer=not no_checkpointer)
    config = {"configurable": {"thread_id": doc_id}}

    try:
        final_state = graph.invoke(initial_state, config=config)
        elapsed_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "doc_id={} | Pipeline complete in {} ms | Passed: {} | PII Scrubbed: {}",
            doc_id,
            elapsed_ms,
            final_state.get("validation_passed", False),
            final_state.get("pii_count", 0),
        )

        if final_state.get("needs_human_review", False):
            logger.warning("doc_id={} | Document escalated to Human Review Queue.", doc_id)

    except Exception as exc:
        logger.error("doc_id={} | Pipeline execution failed: {}", doc_id, exc)
        sys.exit(1)


if __name__ == "__main__":
    run_pipeline()
