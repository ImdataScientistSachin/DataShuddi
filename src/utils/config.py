"""
DataShuddi — Application Settings (pydantic-settings).

Loads all configuration from environment variables (via .env file).
Provides a single `settings` singleton used across all nodes and utilities.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """DataShuddi application settings loaded from environment variables."""

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "datashuddi"
    postgres_user: str = "datashuddi_user"
    postgres_password: str = "datashuddi_pass"
    postgres_url: str = "postgresql://datashuddi_user:datashuddi_pass@localhost:5432/datashuddi"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection_name: str = "datashuddi_docs"
    qdrant_api_key: str | None = None

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    ollama_pii_model: str = "qwen2.5-coder:3b"
    ollama_reflector_model: str = "qwen2.5-coder:14b"
    ollama_embed_model: str = "mxbai-embed-large"

    # LangSmith Observability
    langchain_tracing_v2: bool = False
    langchain_api_key: str | None = None
    langchain_project: str = "datashuddi-local"

    # Pipeline Configuration
    ocr_char_density_threshold: int = 50
    paddleocr_min_confidence: float = 0.70
    hf_threshold_default: float = 0.30
    max_retry_count: int = 3
    pii_escalation_threshold: int = 50
    reflector_confidence_gate: float = 0.70
    reflector_max_delta: float = 0.05

    # Data Paths
    raw_data_dir: Path = Path("./data/raw")
    human_review_dir: Path = Path("./data/human_review")
    test_fixtures_dir: Path = Path("./tests/fixtures")
    qdrant_storage_dir: Path = Path("./data/qdrant_storage")
    postgres_data_dir: Path = Path("./data/postgres_data")

    # Logging
    log_level: str = "INFO"
    enable_langsmith_tracing: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
