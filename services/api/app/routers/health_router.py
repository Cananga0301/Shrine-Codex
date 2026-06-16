from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from app.clients import embedding_client, reranker_client
from app.database.session import async_engine

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health():
    postgres = False
    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("select 1"))
        postgres = True
    except Exception:
        postgres = False
    embedding = {}
    reranker = {}
    try:
        embedding = await embedding_client.health()
    except Exception:
        embedding = {"status": "down"}
    try:
        reranker = await reranker_client.health()
    except Exception:
        reranker = {"status": "down"}
    return {
        "status": "ok" if postgres and embedding.get("status") == "ok" and reranker.get("status") == "ok" else "degraded",
        "postgres": postgres,
        "embedding": embedding,
        "reranker": reranker,
    }


@router.get("/intent/index-stats")
async def intent_index_stats():
    return {"total_prototypes": 0, "intents_covered": 0}


@router.get("/gpu")
async def gpu_status():
    return {
        "available": False,
        "in_use": False,
        "device_name": "Docker CPU",
        "embedding_device": "cpu",
        "reranker_device": "cpu",
    }
