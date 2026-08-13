"""
DataShuddi API — Health Check Route Handler.
"""
import time

import httpx
import psycopg
from fastapi import APIRouter

from src.api.schemas import HealthCheckResponse
from src.utils.config import settings

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Multi-Service Infrastructure Health Check",
    description="Inspects real-time connectivity status for PostgreSQL checkpointer, Qdrant vector engine, and Ollama LLM server.",
)
async def check_health() -> HealthCheckResponse:
    """Return health status across all infrastructure services."""
    postgres_online = False
    qdrant_online = False
    ollama_online = False

    # 1. Check PostgreSQL connection
    try:
        with psycopg.connect(settings.postgres_url, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                res = cur.fetchone()
                if res and res[0] == 1:
                    postgres_online = True
    except Exception:
        postgres_online = False

    # 2. Check Qdrant REST API endpoint
    try:
        headers = {"api-key": settings.qdrant_api_key} if settings.qdrant_api_key else {}
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.qdrant_url}/", headers=headers)
            if resp.status_code == 200:
                qdrant_online = True
    except Exception:
        qdrant_online = False

    # 3. Check Ollama LLM Server endpoint
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            if resp.status_code == 200:
                ollama_online = True
    except Exception:
        ollama_online = False

    overall_status = "ok" if (postgres_online and qdrant_online and ollama_online) else "degraded"

    return HealthCheckResponse(
        status=overall_status,
        postgres_online=postgres_online,
        qdrant_online=qdrant_online,
        ollama_online=ollama_online,
        timestamp=time.time(),
    )
