from __future__ import annotations

import logging
import shutil
import uuid
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import STORAGE_DIR
from app.database.session import close_db, get_db
from app.pipeline.embedding import warmup as warmup_embedding_client
from app.pipeline.ingestor import ingest_document
from app.pipeline.vector_store import ensure_collection

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
log = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = (".docx",)
_DATE_FORM_IGNORE = frozenset({"", "string", "null", "none", "undefined", "n/a", "na", "-"})


def _parse_optional_date_form(value: Optional[str], field: str) -> Optional[date]:
    if value is None:
        return None
    s = value.strip()
    if not s or s.lower() in _DATE_FORM_IGNORE:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError as exc:
        raise HTTPException(400, f"{field} không hợp lệ (dùng YYYY-MM-DD): {s!r}") from exc


def _safe_filename(raw_filename: str) -> str:
    if not raw_filename:
        return "unknown.docx"
    name = PurePosixPath(raw_filename).name or PureWindowsPath(raw_filename).name
    return (name or raw_filename)[:150]


@asynccontextmanager
async def lifespan(app: FastAPI):
    warmup_embedding_client()
    ensure_collection()
    log.info("Ingestion service startup complete.")
    yield
    await close_db()


app = FastAPI(title="Shrine-Codex Ingestion Service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/ingest")
async def ingest(
    file: UploadFile = File(...),
    issuer: str = Form(default=""),
    issued_date: Optional[str] = Form(default=None),
    effective_date: Optional[str] = Form(default=None),
    title: Optional[str] = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    safe_name = _safe_filename(file.filename or "")
    if not safe_name.lower().endswith(ALLOWED_EXTENSIONS):
        raise HTTPException(400, "Chỉ hỗ trợ file .docx trong bản Docker")

    upload_dir = STORAGE_DIR / uuid.uuid4().hex[:12]
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / safe_name
    file_path.write_bytes(await file.read())

    try:
        return await ingest_document(
            file_path=file_path,
            db=db,
            issuer=issuer,
            issued_date=_parse_optional_date_form(issued_date, "issued_date"),
            effective_date=_parse_optional_date_form(effective_date, "effective_date"),
            title_override=title,
        )
    except ValueError as exc:
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        shutil.rmtree(upload_dir, ignore_errors=True)
        log.exception("Ingestion failed for %s", safe_name)
        raise HTTPException(500, f"Ingestion failed: {exc}") from exc
