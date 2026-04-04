FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies for WeasyPrint and PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps (copy full source for editable install)
COPY pyproject.toml .
COPY djafatt/ djafatt/
COPY apps/ apps/
COPY manage.py .
RUN pip install --no-cache-dir -e ".[dev]"

COPY . .

# Non-root user for production
RUN useradd -r -u 1001 -m appuser
USER appuser

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
