"""
DataShuddi API — Main FastAPI Application Entry Point.

Exposes RESTful OpenAPI endpoints for asynchronous document PII sanitization,
job status telemetry, visual PDF exports, and GDPR compliance erasures.
"""
import sys
import time
from pathlib import Path
from typing import Any

# Ensure root directory is on sys.path for direct script/uvicorn execution

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.api.routes import admin, export, health, jobs, sanitize
from src.utils.logging_hygiene import configure_logging

# Configure PII-scrubbing Loguru logging
configure_logging()

app = FastAPI(
    title="DataShuddi REST API",
    description=(
        "Enterprise-Grade, Self-Correcting, Local-First PII Scrubbing & Document Validation Microservice. "
        "Provides Zero-Leak PII redaction, page-split header/footer stripping, Pydantic v2 schema validation, "
        "and Qdrant vector database ingestion."
    ),
    version="3.2.0 API Edition",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable Cross-Origin Resource Sharing (CORS) for external clients & frontend dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next: Any) -> Any:
    """Log HTTP request execution latency without printing PII bodies."""
    start_time = time.time()
    response = await call_next(request)
    elapsed_ms = int((time.time() - start_time) * 1000)

    # Avoid cluttering logs with health check polling
    if not request.url.path.endswith("/health"):
        logger.info(
            "API {} {} | Status: {} | Latency: {} ms",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )
    return response


# Register API Routers
app.include_router(health.router)
app.include_router(sanitize.router)
app.include_router(jobs.router)
app.include_router(export.router)
app.include_router(admin.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.app:app", host="0.0.0.0", port=8000, reload=True)
