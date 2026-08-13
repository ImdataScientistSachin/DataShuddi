"""
DataShuddi -- Document Hashing and ID Utilities.

Generates SHA-256 hashes from file contents for use as immutable doc_ids
and provides MIME type detection by file extension.
"""
import hashlib
from pathlib import Path

# Supported MIME type mappings by extension
EXTENSION_MIME_MAP: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".doc": "application/msword",
    ".txt": "text/plain",
}


def compute_doc_id(file_path: Path) -> str:
    """
    Compute SHA-256 hash of file contents for use as doc_id.

    This doc_id serves as the thread_id for PostgresSaver state checkpointer,
    ensuring pure node idempotency and crash recovery.

    Args:
        file_path: Path object pointing to the source document file.

    Returns:
        Hex string SHA-256 hash of the raw file bytes.

    Raises:
        FileNotFoundError: If the document file does not exist.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Source document not found: {file_path}")

    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def detect_mime_type(file_path: Path) -> str:
    """
    Detect MIME type of a document file by extension.

    Args:
        file_path: Path object pointing to the document file.

    Returns:
        MIME type string (e.g., "application/pdf" or "text/plain").
    """
    ext = file_path.suffix.lower()
    return EXTENSION_MIME_MAP.get(ext, "application/octet-stream")
