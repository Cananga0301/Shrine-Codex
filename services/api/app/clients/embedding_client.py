from __future__ import annotations

import httpx

from app.config import EMBEDDING_SERVICE_URL

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))
    return _client


async def embed_query(query: str) -> list[float]:
    resp = await _get_client().post(f"{EMBEDDING_SERVICE_URL}/embed_query", json={"query": query})
    resp.raise_for_status()
    return resp.json()["vector"]


async def health() -> dict:
    resp = await _get_client().get(f"{EMBEDDING_SERVICE_URL}/health")
    resp.raise_for_status()
    return resp.json()
