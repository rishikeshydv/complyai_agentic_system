FROM python:3.11-slim

WORKDIR /app

COPY apps/core-api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY . /app

WORKDIR /app/apps/core-api

CMD ["sh", "-c", "python -m core.utils.wait_for_db && python -m core.db.bootstrap && celery -A core.celery_app:celery_app worker --loglevel=info -Q celery --concurrency=${CELERY_WORKER_CONCURRENCY:-2}"]
