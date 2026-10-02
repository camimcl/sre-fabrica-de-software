FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app/backend

COPY pyproject.toml ./
COPY requirements.lock ./
COPY alembic.ini ./
COPY app ./app
COPY migrations ./migrations

RUN pip install --no-cache-dir --require-hashes -r requirements.lock

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
