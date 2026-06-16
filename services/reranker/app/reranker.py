from __future__ import annotations

import logging
from typing import Dict, List, Tuple

from sentence_transformers import CrossEncoder

from app.config import RERANKER_BATCH_SIZE, RERANKER_DEVICE, RERANKER_MODEL

log = logging.getLogger(__name__)

_model: CrossEncoder | None = None


def get_model() -> CrossEncoder:
    global _model
    if _model is None:
        _model = CrossEncoder(RERANKER_MODEL, device=RERANKER_DEVICE)
        log.info("Loaded reranker '%s' via CrossEncoder on %s.", RERANKER_MODEL, RERANKER_DEVICE)
    return _model


def warmup() -> None:
    model = get_model()
    model.predict([("kiểm tra", "kiểm tra")], show_progress_bar=False, batch_size=1)


def rerank(query: str, candidates: List[Dict], top_k: int = 5, text_key: str = "text_chunk") -> List[Dict]:
    if not candidates:
        return []
    pairs: List[Tuple[str, str]] = [(query, str(item.get(text_key, ""))) for item in candidates]
    scores = get_model().predict(pairs, show_progress_bar=False, batch_size=RERANKER_BATCH_SIZE)
    out: List[Dict] = []
    for item, score in zip(candidates, scores):
        enriched = dict(item)
        enriched["rerank_score"] = float(score)
        out.append(enriched)
    out.sort(key=lambda item: item["rerank_score"], reverse=True)
    return out[:top_k]
