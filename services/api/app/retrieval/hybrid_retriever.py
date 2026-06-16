from __future__ import annotations

import logging
from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.reranker_client import rerank
from app.config import RERANK_TOP_K, RETRIEVAL_TOP_K
from app.retrieval.keyword_retriever import keyword_search
from app.retrieval.vector_retriever import vector_search

log = logging.getLogger(__name__)


def _dedupe_key(item: Dict) -> str:
    return f"{item.get('document_id')}:{item.get('article_id')}:{hash(item.get('text_chunk', ''))}"


def _reciprocal_rank_fusion(*result_lists: List[Dict], k: int = 60) -> List[Dict]:
    scores: Dict[str, float] = {}
    items: Dict[str, Dict] = {}
    for result_list in result_lists:
        for rank, item in enumerate(result_list):
            key = _dedupe_key(item)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            if key not in items or item.get("score", 0) > items[key].get("score", 0):
                items[key] = dict(item)
    out = []
    for key in sorted(scores, key=scores.get, reverse=True):
        item = items[key]
        item["rrf_score"] = scores[key]
        out.append(item)
    return out


async def hybrid_search(
    query: str,
    db: AsyncSession,
    top_k: int | None = None,
    retrieval_k: int | None = None,
    doc_number: Optional[str] = None,
    document_id: Optional[int] = None,
) -> List[Dict]:
    fetch_k = retrieval_k or RETRIEVAL_TOP_K
    final_k = top_k or RERANK_TOP_K
    vector_results = await vector_search(query, top_k=fetch_k, doc_number=doc_number, document_id=document_id)
    keyword_results = await keyword_search(query, db=db, top_k=fetch_k, doc_number=doc_number)
    merged = _reciprocal_rank_fusion(vector_results, keyword_results)
    if not merged:
        log.warning("No retrieval results for %.80r", query)
        return []
    return await rerank(query, merged, top_k=final_k, text_key="text_chunk")
