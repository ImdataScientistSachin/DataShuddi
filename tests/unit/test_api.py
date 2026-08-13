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
