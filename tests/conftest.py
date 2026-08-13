"""
DataShuddi -- Pytest Fixtures & Environment Setup.
"""
import pytest

from src.utils.logging_hygiene import configure_logging


@pytest.fixture(scope="session", autouse=True)
def setup_logging() -> None:
    """Configure PII-scrubbed Loguru logging for all test sessions."""
    configure_logging(log_level="WARNING")
