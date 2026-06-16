from __future__ import annotations

import logging
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import (
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_DEVICE,
    EMBEDDING_FALLBACK_MODEL,
    EMBEDDING_MAX_LENGTH,
    EMBEDDING_MODEL,
    HF_TOKEN,
)

log = logging.getLogger(__name__)

_model = None
_effective_model_name = ""
_truncation_encode_cache: dict[int, bool] = {}


def _encode_truncation_supported(model) -> bool:
    mid = id(model)
    if mid in _truncation_encode_cache:
        return _truncation_encode_cache[mid]
    supported = True
    get_model_kwargs = getattr(model, "get_model_kwargs", None)
    if callable(get_model_kwargs):
        try:
            allowed = get_model_kwargs()
        except Exception:
            allowed = None
        if allowed is not None:
            supported = bool(allowed) and "truncation" in allowed
    _truncation_encode_cache[mid] = supported
    return supported


def _apply_safe_max_seq_length(model) -> None:
    cap = int(EMBEDDING_MAX_LENGTH)
    try:
        cfg = getattr(getattr(model[0], "auto_model", None), "config", None)
        max_pos = getattr(cfg, "max_position_embeddings", None)
        if max_pos:
            model.max_seq_length = min(cap, max(8, int(max_pos) - 2))
            return
    except Exception as exc:
        log.warning("Could not inspect embedding max sequence length: %s", exc)
    model.max_seq_length = cap


def _load_sentence_transformer(model_name: str):
    kwargs = {}
    if HF_TOKEN:
        kwargs["token"] = HF_TOKEN
    return SentenceTransformer(model_name, device=EMBEDDING_DEVICE, **kwargs)


def get_model():
    global _model, _effective_model_name
    if _model is None:
        try:
            _model = _load_sentence_transformer(EMBEDDING_MODEL)
            _effective_model_name = EMBEDDING_MODEL
        except Exception as exc:
            log.warning(
                "Primary embedding model '%s' failed (%s); loading fallback '%s'.",
                EMBEDDING_MODEL,
                exc,
                EMBEDDING_FALLBACK_MODEL,
            )
            _model = _load_sentence_transformer(EMBEDDING_FALLBACK_MODEL)
            _effective_model_name = EMBEDDING_FALLBACK_MODEL
        _apply_safe_max_seq_length(_model)
        log.info(
            "Loaded embedding model '%s' on %s (dim=%s).",
            _effective_model_name,
            EMBEDDING_DEVICE,
            _model.get_sentence_embedding_dimension(),
        )
    return _model


def model_info() -> dict:
    model = get_model()
    return {
        "model": _effective_model_name,
        "device": EMBEDDING_DEVICE,
        "dimension": int(model.get_sentence_embedding_dimension()),
    }


def embed_texts(texts: List[str], batch_size: int | None = None) -> np.ndarray:
    if not texts:
        return np.array([], dtype=np.float32)
    model = get_model()
    cleaned = [(text.strip() if isinstance(text, str) else "") or " " for text in texts]
    kwargs = {
        "batch_size": batch_size or EMBEDDING_BATCH_SIZE,
        "show_progress_bar": len(cleaned) > 100,
        "normalize_embeddings": True,
        "convert_to_numpy": True,
    }
    if _encode_truncation_supported(model):
        try:
            vectors = model.encode(cleaned, truncation=True, **kwargs)
        except TypeError:
            vectors = model.encode(cleaned, **kwargs)
    else:
        vectors = model.encode(cleaned, **kwargs)
    return vectors.astype(np.float32)


def embed_query(query: str) -> List[float]:
    return embed_texts([(query or "").strip() or " "], batch_size=1)[0].tolist()


def warmup() -> None:
    get_model()
