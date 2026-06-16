from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database.session import close_db
from app.routers.chat_router import router as chat_router
from app.routers.conversation_router import router as conversation_router
from app.routers.document_router import router as document_router
from app.routers.health_router import router as health_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("API startup complete.")
    yield
    await close_db()


app = FastAPI(
    title="Shrine-Codex API",
    version="1.0.0",
    description="Portable service-split Vietnamese legal RAG chatbot.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(document_router)
app.include_router(conversation_router)
