from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import delete as sa_delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis_cache import invalidate_all_query_cache
from app.clients.ingestion_client import proxy_upload
from app.database.models import Article, Document, VectorChunk
from app.database.session import get_db
from app.models.schemas import DocumentDetailResponse, DocumentInfo, DocumentListResponse, UploadResponse
from app.retrieval.vector_retriever import _get_client
from app.config import QDRANT_COLLECTION
from qdrant_client.http.models import FieldCondition, Filter, FilterSelector, MatchValue

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["documents"])


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    issuer: str = Form(default=""),
    issued_date: Optional[str] = Form(default=None),
    effective_date: Optional[str] = Form(default=None),
    title: Optional[str] = Form(default=None),
):
    try:
        result = await proxy_upload(file, issuer, issued_date, effective_date, title)
        await invalidate_all_query_cache()
        return UploadResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        detail = str(exc)
        response = getattr(exc, "response", None)
        if response is not None:
            try:
                detail = response.json().get("detail", detail)
            except Exception:
                detail = response.text or detail
        raise HTTPException(500, f"Ingestion failed: {detail}") from exc


@router.post("/upload-folder")
async def upload_folder(
    files: list[UploadFile] = File(...),
    issuer: str = Form(default=""),
):
    if not files:
        raise HTTPException(400, "Không có file nào được tải lên")

    results: list[dict] = []
    success_count = 0
    skipped_count = 0
    for file in files:
        name = file.filename or "upload.docx"
        if not name.lower().endswith(".docx"):
            skipped_count += 1
            results.append(
                {
                    "file_name": name,
                    "dataset_id": None,
                    "total_chunks": 0,
                    "total_chars": 0,
                    "success": False,
                    "error": "Chỉ hỗ trợ file .docx trong bản Docker",
                }
            )
            continue
        try:
            data = await proxy_upload(file, issuer=issuer)
            success_count += 1
            results.append(
                {
                    "file_name": name,
                    "dataset_id": str(data.get("document_id")),
                    "total_chunks": int(data.get("chunks", 0)),
                    "total_chars": 0,
                    "success": True,
                    "error": None,
                }
            )
        except Exception as exc:
            detail = str(exc)
            response = getattr(exc, "response", None)
            if response is not None:
                try:
                    detail = response.json().get("detail", detail)
                except Exception:
                    detail = response.text or detail
            results.append(
                {
                    "file_name": name,
                    "dataset_id": None,
                    "total_chunks": 0,
                    "total_chars": 0,
                    "success": False,
                    "error": detail,
                }
            )

    await invalidate_all_query_cache()
    fail_count = len(files) - success_count - skipped_count
    return {
        "total_files": len(files),
        "success_count": success_count,
        "fail_count": fail_count,
        "results": results,
        "message": f"Đã xử lý {len(files)} file: {success_count} thành công, {fail_count} thất bại",
    }


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)):
    stmt = select(Document).order_by(Document.created_at.desc()).offset(skip).limit(limit)
    count_stmt = select(func.count()).select_from(Document)
    docs = (await db.execute(stmt)).scalars().all()
    total = (await db.execute(count_stmt)).scalar() or 0
    return DocumentListResponse(documents=[DocumentInfo.model_validate(d) for d in docs], total=total)


@router.get("/documents/{doc_id}", response_model=DocumentDetailResponse)
async def get_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    doc = (await db.execute(select(Document).where(Document.id == doc_id))).scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found")
    articles_count = (await db.execute(select(func.count()).select_from(Article).where(Article.document_id == doc_id))).scalar() or 0
    chunks_count = (await db.execute(select(func.count()).select_from(VectorChunk).where(VectorChunk.document_id == doc_id))).scalar() or 0
    return DocumentDetailResponse(
        id=doc.id,
        doc_number=doc.doc_number,
        title=doc.title,
        document_type=doc.document_type,
        issuer=doc.issuer,
        issued_date=doc.issued_date,
        effective_date=doc.effective_date,
        file_path=doc.file_path,
        created_at=doc.created_at,
        articles_count=articles_count,
        chunks_count=chunks_count,
    )


@router.get("/datasets")
async def list_datasets(db: AsyncSession = Depends(get_db)):
    try:
        docs = (await db.execute(select(Document).order_by(Document.created_at.desc()))).scalars().all()
    except asyncio.CancelledError:
        return {"datasets": []}
    datasets = []
    for doc in docs:
        datasets.append(
            {
                "dataset_id": doc.id,
                "file_name": Path(doc.file_path).name if doc.file_path else doc.doc_number,
                "doc_number": doc.doc_number,
                "title": doc.title,
                "document_type": doc.document_type,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
            }
        )
    return {"datasets": datasets}


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(dataset_id: int, db: AsyncSession = Depends(get_db)):
    doc = (await db.execute(select(Document).where(Document.id == dataset_id))).scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Dataset not found")
    try:
        _get_client().delete(
            collection_name=QDRANT_COLLECTION,
            points_selector=FilterSelector(
                filter=Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=dataset_id))])
            ),
        )
    except Exception as exc:
        log.warning("Failed to delete Qdrant vectors for doc %s: %s", dataset_id, exc)
    await db.execute(sa_delete(Document).where(Document.id == dataset_id))
    await invalidate_all_query_cache()
    return {"status": "ok", "deleted_id": dataset_id}
