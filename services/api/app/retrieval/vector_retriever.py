from __future__ import annotations

import logging
from typing import Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http.models import FieldCondition, Filter, MatchValue

from app.clients.embedding_client import embed_query
from app.config import QDRANT_API_KEY, QDRANT_COLLECTION, QDRANT_HOST, QDRANT_PORT

log = logging.getLogger(__name__)

_client: QdrantClient | None = None


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        kwargs: Dict = {"host": QDRANT_HOST, "port": QDRANT_PORT, "timeout": 30}
        if QDRANT_API_KEY:
            kwargs["api_key"] = QDRANT_API_KEY
        _client = QdrantClient(**kwargs)
    return _client


async def vector_search(
    query: str,
    top_k: int = 20,
    doc_number: Optional[str] = None,
    document_id: Optional[int] = None,
) -> List[Dict]:
    query_vector = await embed_query(query)
    conditions = []
    if doc_number:
        conditions.append(FieldCondition(key="doc_number", match=MatchValue(value=doc_number)))
    if document_id is not None:
        conditions.append(FieldCondition(key="document_id", match=MatchValue(value=document_id)))
    query_filter = Filter(must=conditions) if conditions else None
    results = _get_client().query_points(
        collection_name=QDRANT_COLLECTION,
        query=query_vector,
        limit=top_k,
        query_filter=query_filter,
        with_payload=True,
    )
    return [{"id": str(hit.id), "score": hit.score, **(hit.payload or {})} for hit in results.points]
