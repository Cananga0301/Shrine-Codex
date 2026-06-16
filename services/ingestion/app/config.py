from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://legal_bot:legal_bot_pass@postgres:5432/legal_chatbot",
)
POSTGRES_URL = DATABASE_URL

EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://embedding:8001").rstrip("/")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "768"))

QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "law_documents")
QDRANT_RECREATE_ON_DIM_MISMATCH = os.getenv(
    "QDRANT_RECREATE_ON_DIM_MISMATCH", "true"
).lower() in ("1", "true", "yes", "on")
