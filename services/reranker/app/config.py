from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

RERANKER_MODEL = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
RERANKER_DEVICE = os.getenv("RERANKER_DEVICE", "cpu")
RERANKER_BATCH_SIZE = int(os.getenv("RERANKER_BATCH_SIZE", "16"))
