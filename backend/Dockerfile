# Aegis backend — FastAPI scoring API (Python 3.13, ADR-001)
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependency layer (cache-friendly): copy metadata + package, install with dev extras
COPY pyproject.toml ./
COPY aegis ./aegis
COPY tests ./tests
RUN pip install --upgrade pip && pip install ".[dev]"

EXPOSE 8000

# T-01: entrypoint minimal; router asli menyusul di T-12
CMD ["uvicorn", "aegis.main:app", "--host", "0.0.0.0", "--port", "8000"]
