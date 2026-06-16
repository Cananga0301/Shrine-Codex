from __future__ import annotations

from typing import Optional

import httpx
from fastapi import UploadFile

from app.config import INGESTION_SERVICE_URL


async def proxy_upload(
    file: UploadFile,
    issuer: str = "",
    issued_date: Optional[str] = None,
    effective_date: Optional[str] = None,
    title: Optional[str] = None,
) -> dict:
    content = await file.read()
    data = {
        "issuer": issuer or "",
        "issued_date": issued_date or "",
        "effective_date": effective_date or "",
        "title": title or "",
    }
    files = {
        "file": (
            file.filename or "upload.docx",
            content,
            file.content_type or "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=10.0)) as client:
        resp = await client.post(f"{INGESTION_SERVICE_URL}/ingest", data=data, files=files)
        resp.raise_for_status()
        return resp.json()
