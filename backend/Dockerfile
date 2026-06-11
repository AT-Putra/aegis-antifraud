# Aegis backend — FastAPI scoring API (Python 3.13, ADR-001)
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Runtime libs: libgomp1 (OpenMP) dibutuhkan LightGBM.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Dependency layer (cache-friendly): copy metadata + package, install with dev extras
COPY pyproject.toml ./
COPY aegis ./aegis
COPY tests ./tests
# Editable install: paket di-link ke /app sehingga file non-Python (mis. *.sql migrasi)
# ter-resolve lewat Path(__file__) tanpa perlu konfigurasi packaging tambahan.
RUN pip install --upgrade pip && \
    pip install --retries 8 --timeout 120 -e ".[dev]"

EXPOSE 8000

# T-01: entrypoint minimal; router asli menyusul di T-12
CMD ["uvicorn", "aegis.main:app", "--host", "0.0.0.0", "--port", "8000"]
