FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl libgomp1 && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir torch==2.3.1+cpu --index-url https://download.pytorch.org/whl/cpu
COPY services/reranker/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
COPY services/reranker ./services/reranker
ENV PYTHONPATH=/app/services/reranker
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
