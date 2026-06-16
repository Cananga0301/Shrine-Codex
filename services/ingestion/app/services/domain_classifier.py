from __future__ import annotations


def classify_document_law_intents(title: str | None, snippet: str | None) -> list[str]:
    """Core-only build: keep a stable schema field without loading domain classifiers."""
    text = f"{title or ''} {snippet or ''}".lower()
    if "thư viện" in text:
        return ["thu_vien"]
    if "văn hóa" in text or "di sản" in text:
        return ["van_hoa"]
    return ["chung"]
