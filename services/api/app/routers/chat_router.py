from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db, get_db_context
from app.models.schemas import ChatRequest, ChatResponse
from app.services.rag_chain import rag_query, rag_query_stream

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    result = await rag_query(
        query=req.query or "",
        db=db,
        temperature=req.temperature,
        doc_number=req.doc_number,
        conversation_id=req.conversation_id,
    )
    return ChatResponse(**result)


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    async def event_generator():
        async with get_db_context() as db:
            async for token in rag_query_stream(
                query=req.query or "",
                db=db,
                temperature=req.temperature,
                doc_number=req.doc_number,
                conversation_id=req.conversation_id,
            ):
                yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
