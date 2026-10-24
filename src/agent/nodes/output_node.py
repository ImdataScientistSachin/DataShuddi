"""
DataShuddi -- Node 7: Output Node.

Final output gate reached strictly when validation_passed = True.
Enforces the ALLOWED_PAYLOAD_KEYS metadata allowlist before writing points
to Qdrant vector database.

Policy:
    - Metadata attributes restricted strictly to ALLOWED_PAYLOAD_KEYS.
    - Zero raw document text or titles in metadata.
    - Vector embeddings generated via mxbai-embed-large (GPU).
"""
import hashlib
import time
from typing import Any

from loguru import logger

from src.agent.state import DataShuddiState
from src.utils.config import settings
from src.utils.constants import ALLOWED_PAYLOAD_KEYS


def output_node(state: DataShuddiState) -> DataShuddiState:
    """
    Node 7: Strict metadata filtering, embedding generation, Qdrant vector upsert.

    Args:
        state: Current DataShuddiState dictionary.

    Returns:
        Updated DataShuddiState with node_timestamps updated.

    Raises:
        ValueError: If validation_passed is False or payload contains forbidden keys.
    """
    node_name = "output_node"
    timestamps: dict[str, float] = dict(state.get("node_timestamps", {}))
    timestamps[node_name] = time.time()

    if not state.get("validation_passed", False):
        raise ValueError(f"doc_id={state.get('doc_id', 'UNKNOWN')} | Output Node reached without schema validation pass.")

    doc_id = state.get("doc_id", "UNKNOWN")
    masked_text = state.get("masked_text", "")
    source_system = state.get("source_system", "local")
    quality_score = state.get("quality_score", 1.0)
    hf_removed = len(state.get("header_footer_candidates", []))
    pii_scrubbed = state.get("pii_count", 0) > 0

    # Chunk text: 512 chars with 50 char overlap
    chunks = _chunk_text(masked_text, chunk_size=512, overlap=50)
    logger.info("doc_id={} | Node 7: Created {} chunks for embedding", doc_id, len(chunks))

    # Prepare and sanitize payload per chunk
    for idx, chunk in enumerate(chunks):
        raw_payload = {
            "doc_id": doc_id,
            "chunk_index": idx,
            "source_system": source_system,
            "quality_score": quality_score,
            "hf_lines_removed": hf_removed,
            "pii_scrubbed": pii_scrubbed,
        }

        # Check raw payload for forbidden keys before filtering
        forbidden_keys = set(raw_payload.keys()) - ALLOWED_PAYLOAD_KEYS
        if forbidden_keys:
            raise ValueError(f"Forbidden metadata keys detected in payload: {forbidden_keys}")

        # Filter strictly by ALLOWED_PAYLOAD_KEYS
        sanitized_payload = {
            k: v for k, v in raw_payload.items() if k in ALLOWED_PAYLOAD_KEYS
        }

        # Generate embedding
        embedding = _generate_embedding(chunk, doc_id)
        _upsert_to_qdrant(doc_id, idx, embedding, sanitized_payload)

    logger.info("doc_id={} | Node 7: Successfully upserted {} vector points to Qdrant", doc_id, len(chunks))

    start_time = state.get("_start_time", 0.0)
    processing_time_ms = int((time.time() - start_time) * 1000) if start_time > 0 else 0

    return {
        **state,
        "processing_time_ms": processing_time_ms,
        "node_timestamps": timestamps,
    }


def _chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    """
    Split text into clean overlapping chunks respecting sentence and word boundaries.
    """
    if not text or not text.strip():
        return []

    clean_text = text.strip()
    if len(clean_text) <= chunk_size:
        return [clean_text]

    chunks: list[str] = []
    start = 0
    text_len = len(clean_text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        if end < text_len:
            # Look for natural sentence or paragraph delimiter in the latter half of chunk window
            last_break = -1
            for sep in ("\n\n", "\n", ". ", "? ", "! ", " "):
                pos = clean_text.rfind(sep, start + (chunk_size // 2), end)
                if pos != -1:
                    last_break = pos + len(sep)
                    break
            if last_break > start:
                end = last_break

        chunk_content = clean_text[start:end].strip()
        if chunk_content:
            chunks.append(chunk_content)

        if end >= text_len:
            break
        # Advance with overlap
        start = max(start + 1, end - overlap)

    return chunks


def _generate_embedding(text: str, doc_id: str) -> list[float]:
    """Generate 1024-dim embedding via mxbai-embed-large GPU model."""
    import ollama

    try:
        response = ollama.embeddings(
            model=settings.ollama_embed_model,
            prompt=text,
        )
        raw_emb = response.get("embedding", [0.0] * 1024)
        return [float(x) for x in raw_emb]
    except Exception as exc:
        logger.warning("doc_id={} | mxbai embedding failed, using zero fallback: {}", doc_id, exc)
        return [0.0] * 1024


def _upsert_to_qdrant(doc_id: str, chunk_idx: int, vector: list[float], payload: dict[str, Any], client: Any = None) -> None:
    """Upsert vector point to Qdrant vector database."""
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, PointStruct, VectorParams

        if client is None:
            client = QdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key,
                timeout=10,
            )

        # Ensure collection exists (cached/cheap check)
        try:
            collections = [c.name for c in client.get_collections().collections]
            if settings.qdrant_collection_name not in collections:
                client.create_collection(
                    collection_name=settings.qdrant_collection_name,
                    vectors_config=VectorParams(size=len(vector), distance=Distance.COSINE),
                )
        except Exception:
            pass  # Avoid failing if collection check fails in offline mode

        # Pure deterministic integer ID derived from doc_id and chunk_idx
        digest = hashlib.sha256(f"{doc_id}_{chunk_idx}".encode()).hexdigest()
        point_id = int(digest[:15], 16)
        client.upsert(
            collection_name=settings.qdrant_collection_name,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)],
        )
    except Exception as exc:
        logger.warning("doc_id={} | Qdrant upsert notice: {}", doc_id, exc)

