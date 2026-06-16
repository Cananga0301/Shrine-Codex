from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.services import conversation_repository as repo

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


class CreateConversationRequest(BaseModel):
    title: str | None = None


@router.get("")
async def list_conversations(db: AsyncSession = Depends(get_db)):
    return {"conversations": await repo.list_conversations(db)}


@router.post("")
async def create_conversation(req: CreateConversationRequest, db: AsyncSession = Depends(get_db)):
    return await repo.create_conversation(db, title=req.title)


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    detail = await repo.get_conversation_detail_dict(db, conversation_id)
    if not detail:
        raise HTTPException(404, "Conversation not found")
    return detail


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    if not await repo.delete_conversation(db, conversation_id):
        raise HTTPException(404, "Conversation not found")
    return {"status": "ok", "deleted_id": conversation_id}
