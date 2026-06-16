from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "keepitreal/vietnamese-sbert")
EMBEDDING_FALLBACK_MODEL = os.getenv(
    "EMBEDDING_FALLBACK_MODEL",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
)
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))
EMBEDDING_MAX_LENGTH = int(os.getenv("EMBEDDING_MAX_LENGTH", "512"))
HF_TOKEN = os.getenv("HF_TOKEN") or None
