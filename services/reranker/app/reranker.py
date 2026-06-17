from __future__ import annotations

import logging
from typing import Dict, List, Tuple

from app.config import (
    COHERE_API_KEY,
    COHERE_RERANK_MODEL,
    RERANKER_BACKEND,
    RERANKER_BATCH_SIZE,
    RERANKER_DEVICE,
    RERANKER_MODEL,
)

log = logging.getLogger(__name__)

_local_model = None
_cohere_client = None


def _get_local_model():
    global _local_model
    if _local_model is None:
        from sentence_transformers import CrossEncoder
        _local_model = CrossEncoder(RERANKER_MODEL, device=RERANKER_DEVICE)
        log.info("Loaded reranker '%s' via CrossEncoder on %s.", RERANKER_MODEL, RERANKER_DEVICE)
    return _local_model


def _get_cohere_client():
    global _cohere_client
    if _cohere_client is None:
        import cohere
        _cohere_client = cohere.Client(api_key=COHERE_API_KEY)
        log.info("Cohere reranker client ready, model=%s.", COHERE_RERANK_MODEL)
    return _cohere_client


def warmup() -> None:
    if RERANKER_BACKEND == "cohere":
        _get_cohere_client()
        return
    model = _get_local_model()
    model.predict([("kiểm tra", "kiểm tra")], show_progress_bar=False, batch_size=1)


def rerank(query: str, candidates: List[Dict], top_k: int = 5, text_key: str = "text_chunk") -> List[Dict]:
    if not candidates:
        return []
    if RERANKER_BACKEND == "cohere":
        return _rerank_cohere(query, candidates, top_k, text_key)
    return _rerank_local(query, candidates, top_k, text_key)


def _rerank_local(query: str, candidates: List[Dict], top_k: int, text_key: str) -> List[Dict]:
    pairs: List[Tuple[str, str]] = [(query, str(item.get(text_key, ""))) for item in candidates]
    scores = _get_local_model().predict(pairs, show_progress_bar=False, batch_size=RERANKER_BATCH_SIZE)
    out = []
    for item, score in zip(candidates, scores):
        enriched = dict(item)
        enriched["rerank_score"] = float(score)
        out.append(enriched)
    out.sort(key=lambda x: x["rerank_score"], reverse=True)
    return out[:top_k]


def _rerank_cohere(query: str, candidates: List[Dict], top_k: int, text_key: str) -> List[Dict]:
    documents = [str(item.get(text_key, "")) for item in candidates]
    response = _get_cohere_client().rerank(
        model=COHERE_RERANK_MODEL,
        query=query,
        documents=documents,
        top_n=top_k,
    )
    out = []
    for result in response.results:
        enriched = dict(candidates[result.index])
        enriched["rerank_score"] = float(result.relevance_score)
        out.append(enriched)
    return out
