FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY apps/connector/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY . /app

WORKDIR /app/apps/connector

RUN chmod +x /app/apps/connector/entrypoint.prod.sh

CMD ["/app/apps/connector/entrypoint.prod.sh"]
