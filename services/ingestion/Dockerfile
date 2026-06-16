FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY services/ingestion/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY shared ./shared
COPY scripts ./scripts
COPY services/ingestion ./services/ingestion
RUN chmod +x ./scripts/entrypoint.sh
ENV PYTHONPATH=/app:/app/services/ingestion
ENTRYPOINT ["./scripts/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
