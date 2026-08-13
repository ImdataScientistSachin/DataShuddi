"""
DataShuddi -- Unit Tests: Document Utilities (doc_utils.py).

Verifies SHA-256 document hashing, file existence checks, and MIME type detection.
Follows the AAA (Arrange, Act, Assert) testing pattern.
"""
from pathlib import Path

import pytest

from src.utils.doc_utils import compute_doc_id, detect_mime_type


class TestDocUtils:
    """Unit tests for src.utils.doc_utils."""

    def test_compute_doc_id_returns_sha256_hash(self, tmp_path: Path) -> None:
        """Arrange: Valid text file. Act: Compute doc_id. Assert: Returns 64-char SHA-256 hex string."""
        # Arrange
        f = tmp_path / "test_doc.txt"
        f.write_text("Hello World DataShuddi Document Hashing Content", encoding="utf-8")

        # Act
        doc_id = compute_doc_id(f)

        # Assert
        assert isinstance(doc_id, str)
        assert len(doc_id) == 64
        assert all(c in "0123456789abcdef" for c in doc_id)

    def test_compute_doc_id_is_idempotent(self, tmp_path: Path) -> None:
        """Arrange: Valid file. Act: Compute doc_id twice. Assert: Identical hash returned."""
        # Arrange
        f = tmp_path / "repeat_test.txt"
        f.write_text("Repeatable content for hashing test.", encoding="utf-8")

        # Act
        hash1 = compute_doc_id(f)
        hash2 = compute_doc_id(f)

        # Assert
        assert hash1 == hash2

    def test_compute_doc_id_nonexistent_file_raises_error(self) -> None:
        """Arrange: Nonexistent file path. Act & Assert: Raises FileNotFoundError."""
        # Arrange
        nonexistent = Path("./nonexistent_file_987654321.txt")

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            compute_doc_id(nonexistent)

    @pytest.mark.parametrize(
        "ext, expected_mime",
        [
            (".pdf", "application/pdf"),
            (".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            (".doc", "application/msword"),
            (".txt", "text/plain"),
            (".unknown", "application/octet-stream"),
            ("", "application/octet-stream"),
        ],
    )
    def test_detect_mime_type_mappings(self, ext: str, expected_mime: str) -> None:
        """Arrange: Path with given extension. Act: Detect MIME. Assert: Correct MIME returned."""
        # Arrange
        p = Path(f"sample_file{ext}")

        # Act
        mime = detect_mime_type(p)

        # Assert
        assert mime == expected_mime
