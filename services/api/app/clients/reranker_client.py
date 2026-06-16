from __future__ import annotations

from typing import Any, Dict, List

import httpx

from app.config import RERANKER_SERVICE_URL

_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0))
    return _client


async def rerank(query: str, candidates: List[Dict[str, Any]], top_k: int, text_key: str = "text_chunk") -> List[Dict[str, Any]]:
    resp = await _get_client().post(
        f"{RERANKER_SERVICE_URL}/rerank",
        json={"query": query, "candidates": candidates, "top_k": top_k, "text_key": text_key},
    )
    resp.raise_for_status()
    return resp.json()["results"]


async def health() -> dict:
    resp = await _get_client().get(f"{RERANKER_SERVICE_URL}/health")
    resp.raise_for_status()
    return resp.json()
