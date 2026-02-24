FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY apps/core-api/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY . /app

WORKDIR /app/apps/core-api

RUN chmod +x /app/apps/core-api/entrypoint.prod.sh

# Default entrypoint is production-safe (respects $PORT, does bootstrap, optional seeding).
CMD ["/app/apps/core-api/entrypoint.prod.sh"]
