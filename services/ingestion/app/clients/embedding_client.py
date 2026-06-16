from __future__ import annotations

from typing import List

import httpx

from app.config import EMBEDDING_SERVICE_URL

_client: httpx.Client | None = None


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(timeout=httpx.Timeout(300.0, connect=10.0))
    return _client


def embed_texts_via_service(texts: List[str]) -> List[List[float]]:
    resp = _get_client().post(f"{EMBEDDING_SERVICE_URL}/embed", json={"texts": texts})
    resp.raise_for_status()
    return resp.json()["vectors"]


def embedding_dimension() -> int:
    resp = _get_client().get(f"{EMBEDDING_SERVICE_URL}/health")
    resp.raise_for_status()
    return int(resp.json()["dimension"])
