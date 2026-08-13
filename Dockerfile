# ─── DataShuddi Production Multi-Stage Dockerfile ─────────────────────────────
# Stage 1: Build virtual environment dependencies
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Final lightweight runtime image
FROM python:3.12-slim AS runner

WORKDIR /app

# Install runtime system dependencies for PaddleOCR & PyMuPDF
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Download spaCy model into runtime environment
RUN python -m spacy download en_core_web_lg

COPY . .

EXPOSE 8000 8501

# Default command: Start Uvicorn FastAPI server on Port 8000
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
