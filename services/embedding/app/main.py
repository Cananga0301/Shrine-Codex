from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.embedding import embed_query, embed_texts, model_info, warmup

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
log = logging.getLogger(__name__)


class EmbedRequest(BaseModel):
    texts: List[str] = Field(default_factory=list)


class EmbedQueryRequest(BaseModel):
    query: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    warmup()
    log.info("Embedding service startup complete.")
    yield


app = FastAPI(title="Shrine-Codex Embedding Service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", **model_info()}


@app.post("/embed")
async def embed(req: EmbedRequest):
    vectors = embed_texts(req.texts)
    return {"vectors": vectors.tolist(), "count": len(req.texts), **model_info()}


@app.post("/embed_query")
async def embed_one(req: EmbedQueryRequest):
    return {"vector": embed_query(req.query), **model_info()}
