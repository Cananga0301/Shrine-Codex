from __future__ import annotations

import json
import logging
import time
from typing import AsyncGenerator, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis_cache import cache_answer, get_cached_answer
from app.config import NO_INFO_MESSAGE, RAG_PROMPT_TEMPLATE, RERANK_TOP_K, SYSTEM_PROMPT
from app.retrieval.hybrid_retriever import hybrid_search
from app.services import conversation_repository as conv_repo
from app.services.answer_validator import get_fallback_answer, validate_answer
from app.services.llm_client import generate, generate_stream

log = logging.getLogger(__name__)


def _source_citation(item: Dict) -> str:
    doc = item.get("doc_number") or item.get("document_title") or "Tài liệu"
    article = item.get("article_number")
    clause = item.get("clause_number")
    bits = [str(doc)]
    if article:
        bits.append(f"Điều {article}")
    if clause:
        bits.append(f"Khoản/Điểm {clause}")
    return " - ".join(bits)


def _format_context(passages: List[Dict]) -> str:
    blocks: List[str] = []
    for idx, item in enumerate(passages, 1):
        header = _source_citation(item)
        title = item.get("article_title") or ""
        text = (item.get("text_chunk") or "").strip()
        blocks.append(f"[{idx}] {header}\n{title}\n{text}")
    return "\n\n".join(blocks)


def _sources(passages: List[Dict]) -> List[Dict]:
    out: List[Dict] = []
    seen = set()
    for item in passages:
        key = (item.get("document_id"), item.get("article_id"), item.get("clause_id"), item.get("text_chunk"))
        if key in seen:
            continue
        seen.add(key)
        snippet = (item.get("text_chunk") or "").strip()
        out.append(
            {
                "citation": _source_citation(item),
                "document_title": item.get("document_title") or "",
                "article_number": item.get("article_number"),
                "article_title": item.get("article_title"),
                "snippet": snippet[:600],
                "document_id": item.get("document_id"),
                "article_id": item.get("article_id"),
                "clause_id": item.get("clause_id"),
                "doc_number": item.get("doc_number") or "",
                "score": float(item.get("rerank_score", item.get("score", 0.0)) or 0.0),
            }
        )
    return out


async def _ensure_conversation(db: AsyncSession, conversation_id: Optional[str], query: str) -> str:
    if conversation_id and await conv_repo.conversation_exists(db, conversation_id):
        return conversation_id
    conv = await conv_repo.create_conversation(db, title=query[:80])
    return str(conv["id"])


async def rag_query(
    query: str,
    db: AsyncSession,
    temperature: float = 0.5,
    doc_number: Optional[str] = None,
    conversation_id: Optional[str] = None,
) -> Dict:
    started = time.perf_counter()
    q = (query or "").strip()
    if not q:
        return {"answer": "Vui lòng nhập câu hỏi.", "sources": [], "confidence_score": 0.0}

    cached = await get_cached_answer(q)
    if cached and not conversation_id and not doc_number:
        return cached

    cid = await _ensure_conversation(db, conversation_id, q)
    await conv_repo.add_message(db, cid, "user", q)

    passages = await hybrid_search(q, db=db, top_k=RERANK_TOP_K, doc_number=doc_number)
    if not passages:
        result = {"answer": NO_INFO_MESSAGE, "sources": [], "confidence_score": 0.0, "conversation_id": cid, "retried": False}
        await conv_repo.add_message(db, cid, "assistant", result["answer"])
        return result

    context = _format_context(passages)
    prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=q)
    answer = await generate(prompt, system=SYSTEM_PROMPT, temperature=temperature)
    validation = await validate_answer(q, context, answer)
    retried = False
    confidence = float(validation.get("confidence", 0.5) or 0.5)
    if validation and validation.get("is_valid") is False:
        retried = True
        answer = get_fallback_answer()
        confidence = min(confidence, 0.3)

    result = {
        "answer": answer,
        "sources": _sources(passages),
        "confidence_score": confidence,
        "conversation_id": cid,
        "retried": retried,
    }
    await conv_repo.add_message(db, cid, "assistant", answer)
    if not doc_number:
        await cache_answer(q, result)
    log.info("RAG query completed in %.2fs", time.perf_counter() - started)
    return result


async def rag_query_stream(
    query: str,
    db: AsyncSession,
    temperature: float = 0.5,
    doc_number: Optional[str] = None,
    conversation_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    q = (query or "").strip()
    cid = await _ensure_conversation(db, conversation_id, q)
    await conv_repo.add_message(db, cid, "user", q)

    passages = await hybrid_search(q, db=db, top_k=RERANK_TOP_K, doc_number=doc_number)
    if not passages:
        answer = NO_INFO_MESSAGE
        yield answer
        await conv_repo.add_message(db, cid, "assistant", answer)
        yield json.dumps({"type": "sources", "data": []}, ensure_ascii=False)
        yield json.dumps({"type": "meta", "conversation_id": cid, "confidence_score": 0.0, "retried": False}, ensure_ascii=False)
        return

    context = _format_context(passages)
    prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=q)
    chunks: List[str] = []
    async for token in generate_stream(prompt, system=SYSTEM_PROMPT, temperature=temperature):
        chunks.append(token)
        yield token

    answer = "".join(chunks)
    validation = await validate_answer(q, context, answer)
    retried = False
    confidence = float(validation.get("confidence", 0.5) or 0.5)
    if validation and validation.get("is_valid") is False:
        retried = True
        answer = get_fallback_answer()
        confidence = min(confidence, 0.3)
        yield json.dumps(
            {"type": "text_finalize", "text": answer, "confidence_score": confidence, "retried": retried},
            ensure_ascii=False,
        )
    await conv_repo.add_message(db, cid, "assistant", answer)
    src = _sources(passages)
    yield json.dumps({"type": "sources", "data": src}, ensure_ascii=False)
    yield json.dumps(
        {"type": "meta", "conversation_id": cid, "confidence_score": confidence, "retried": retried},
        ensure_ascii=False,
    )
