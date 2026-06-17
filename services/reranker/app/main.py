from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.config import COHERE_RERANK_MODEL, RERANKER_BACKEND, RERANKER_DEVICE, RERANKER_MODEL
from app.reranker import rerank, warmup

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
log = logging.getLogger(__name__)


class RerankRequest(BaseModel):
    query: str
    candidates: List[Dict[str, Any]] = Field(default_factory=list)
    top_k: int = 5
    text_key: str = "text_chunk"


@asynccontextmanager
async def lifespan(app: FastAPI):
    warmup()
    log.info("Reranker service startup complete.")
    yield


app = FastAPI(title="Shrine-Codex Reranker Service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health():
    if RERANKER_BACKEND == "cohere":
        return {"status": "ok", "backend": "cohere", "model": COHERE_RERANK_MODEL}
    return {"status": "ok", "backend": "local", "model": RERANKER_MODEL, "device": RERANKER_DEVICE}


@app.post("/rerank")
async def rerank_endpoint(req: RerankRequest):
    return {"results": rerank(req.query, req.candidates, req.top_k, req.text_key)}
