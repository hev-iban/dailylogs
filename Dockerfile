FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Layout mirrors the repo: /app/backend and /app/frontend are siblings, and
# uploads resolves to /app/uploads (models.PROJECT_ROOT / "uploads").
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY frontend/ frontend/

# Create uploads owned by the app user so a fresh named volume mounted here
# inherits that ownership and stays writable.
RUN useradd --system --no-create-home app \
    && mkdir uploads \
    && chown app:app uploads
USER app

WORKDIR /app/backend
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
