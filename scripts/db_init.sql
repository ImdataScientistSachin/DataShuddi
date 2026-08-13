-- DataShuddi Database Initialization Script for PostgreSQL 16
-- Used by docker-compose to initialize the checkpointer database.
-- Note: The 'datashuddi' database is auto-created by POSTGRES_DB env var.

-- Enable UUID extension (required by LangGraph checkpoint-postgres)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Schema for LangGraph PostgresSaver checkpointer & store tables
-- Note: LangGraph checkpoint-postgres package manages its own migrations,
-- but having extensions pre-installed ensures smooth initialization.
