.PHONY: help bootstrap lint typecheck test test-unit test-gate docker-up docker-down run dashboard

help:
	@echo "DataShuddi Development Commands:"
	@echo "  make bootstrap   - Run environment setup and validator script"
	@echo "  make lint        - Run ruff linter check"
	@echo "  make typecheck   - Run mypy strict type checker"
	@echo "  make test        - Run all pytest test suites"
	@echo "  make test-unit   - Run unit tests only"
	@echo "  make test-gate   - Run CI/CD release gate evaluation test"
	@echo "  make docker-up   - Start PostgreSQL and Qdrant containers"
	@echo "  make docker-down - Stop docker containers"
	@echo "  make dashboard   - Launch Streamlit dashboard"

PYTHON ?= .venv/Scripts/python.exe

bootstrap:
	$(PYTHON) scripts/bootstrap_dev_env.py

lint:
	$(PYTHON) -m ruff check src/ tests/

typecheck:
	$(PYTHON) -m mypy src/

test:
	$(PYTHON) -m pytest

test-unit:
	$(PYTHON) -m pytest tests/unit/ -v

test-gate:
	$(PYTHON) -m pytest tests/test_release_gate.py -v

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

dashboard:
	$(PYTHON) -m streamlit run streamlit_app/app.py
