"""
DataShuddi -- Checkpointer and Store Connection Helper.

Provides initialization functions for PostgresSaver thread checkpointer
and LangGraph Store versioned threshold persistence.
"""
from typing import Any

from loguru import logger

from src.utils.config import settings


def get_checkpointer() -> Any:
    """
    Initialize PostgresSaver checkpointer if PostgreSQL is available,
    otherwise return MemorySaver fallback.

    Returns:
        Checkpointer instance for LangGraph graph compilation.
    """
    pool = None
    try:
        from typing import cast

        import psycopg
        from langgraph.checkpoint.postgres import PostgresSaver
        from psycopg_pool import ConnectionPool

        # Quick probe to avoid 30-second pool acquisition hangs when DB is offline
        with psycopg.connect(settings.postgres_url, connect_timeout=1) as conn:
            conn.execute("SELECT 1")

        pool = ConnectionPool(conninfo=settings.postgres_url, max_size=10, timeout=1.0, kwargs={"autocommit": True})
        checkpointer = PostgresSaver(cast(Any, pool))
        checkpointer.setup()
        logger.info("PostgresSaver checkpointer initialized successfully.")

        return checkpointer
    except Exception as exc:
        if pool is not None:
            try:
                pool.close()
            except Exception:
                pass
        logger.warning("PostgreSQL checkpointer offline: {} -- using MemorySaver fallback", exc)
        from langgraph.checkpoint.memory import MemorySaver

        return MemorySaver()


def get_store() -> Any:
    """
    Initialize LangGraph Store instance for versioned hf_threshold persistence.

    Returns:
        InMemoryStore instance. TODO: Migrate to PostgresStore for production persistence.
    """
    from langgraph.store.memory import InMemoryStore
    return InMemoryStore()
