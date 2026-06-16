from __future__ import annotations

from typing import List

import numpy as np

from app.clients.embedding_client import embed_texts_via_service, embedding_dimension


def get_embedding_dimension() -> int:
    return embedding_dimension()


def embed_texts(texts: List[str], batch_size: int | None = None) -> np.ndarray:
    if not texts:
        return np.array([], dtype=np.float32)
    cleaned = [(text.strip() if isinstance(text, str) else "") or " " for text in texts]
    return np.array(embed_texts_via_service(cleaned), dtype=np.float32)


def embed_query(query: str) -> List[float]:
    return embed_texts([(query or "").strip() or " "], batch_size=1)[0].tolist()


def warmup() -> None:
    embedding_dimension()
