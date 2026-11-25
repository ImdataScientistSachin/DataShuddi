"""
DataShuddi — Unit Tests for FastAPI Microservice Endpoints.
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.app import app

client = TestClient(app)


@pytest.mark.unit
def test_health_endpoint() -> None:
    """Test GET /health infrastructure status endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "postgres_online" in data
    assert "qdrant_online" in data
    assert "ollama_online" in data
    assert "timestamp" in data


from unittest.mock import patch


@pytest.mark.unit
def test_sanitize_submission_endpoint(tmp_path: Path) -> None:
    """Test POST /api/v1/sanitize document submission endpoint."""
    sample_file = tmp_path / "api_test_doc.txt"
    sample_file.write_text("API test document content for DataShuddi testing. Contact test@example.com.", encoding="utf-8")

    with patch("src.api.routes.sanitize._run_graph_in_background") as mock_bg:
        with open(sample_file, "rb") as f:
            response = client.post(
                "/api/v1/sanitize",
                files={"file": ("api_test_doc.txt", f, "text/plain")},
                data={"source_system": "local"},
            )

    assert response.status_code == 202
    data = response.json()
    assert "doc_id" in data
    assert data["doc_name"] == "api_test_doc.txt"
    assert data["source_system"] == "local"
    assert data["status"] == "processing"
    mock_bg.assert_called_once()



@pytest.mark.unit
def test_job_status_endpoint() -> None:
    """Test GET /api/v1/jobs/{doc_id} job status endpoint."""
    dummy_doc_id = "0000000000000000000000000000000000000000000000000000000000000000"
    response = client.get(f"/api/v1/jobs/{dummy_doc_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["doc_id"] == dummy_doc_id
    assert data["status"] in ["not_found", "completed", "failed", "human_review"]


@pytest.mark.unit
def test_gdpr_purge_endpoint() -> None:
    """Test POST /api/v1/admin/purge compliance data erasure endpoint."""
    dummy_doc_id = "nonexistent_doc_id_12345"
    response = client.post("/api/v1/admin/purge", json={"doc_id": dummy_doc_id})
    assert response.status_code == 200
    data = response.json()
    assert data["doc_id"] == dummy_doc_id
    assert data["status"] == "success"


@pytest.mark.unit
def test_sanitize_unsupported_extension_rejected(tmp_path: Path) -> None:
    """Test POST /api/v1/sanitize rejects disallowed file types like .exe."""
    sample_file = tmp_path / "malicious.exe"
    sample_file.write_bytes(b"MZ\x90\x00")

    with open(sample_file, "rb") as f:
        response = client.post(
            "/api/v1/sanitize",
            files={"file": ("malicious.exe", f, "application/x-msdownload")},
            data={"source_system": "local"},
        )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


@pytest.mark.unit
def test_admin_purge_requires_key_when_configured() -> None:
    """Test POST /api/v1/admin/purge enforces X-API-Key when settings.admin_api_key is set."""
    from src.utils.config import settings
    original_key = settings.admin_api_key
    try:
        settings.admin_api_key = "secret_admin_token_999"
        # Request without key -> 401
        res_unauth = client.post("/api/v1/admin/purge", json={"doc_id": "test_id"})
        assert res_unauth.status_code == 401

        # Request with valid key -> 200
        res_auth = client.post(
            "/api/v1/admin/purge",
            headers={"X-API-Key": "secret_admin_token_999"},
            json={"doc_id": "test_id"},
        )
        assert res_auth.status_code == 200
    finally:
        settings.admin_api_key = original_key

