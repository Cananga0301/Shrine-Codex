from __future__ import annotations

import logging

from app.config import OPENAI_API_KEY

log = logging.getLogger(__name__)

_VALIDATE_SYSTEM = (
    "Bạn kiểm tra câu trả lời pháp lý có bám sát ngữ cảnh không. "
    "Luôn trả về JSON hợp lệ, không markdown."
)

_VALIDATE_TEMPLATE = """\
CÂU HỎI:
{query}

NGỮ CẢNH:
{context}

CÂU TRẢ LỜI:
{answer}

Trả về JSON:
{{"is_valid": true/false, "confidence": 0.0-1.0, "issues": []}}
"""


async def validate_answer(query: str, context: str, answer: str) -> dict:
    if not OPENAI_API_KEY or not context or not answer:
        return {"is_valid": True, "confidence": 0.5, "issues": []}
    try:
        from app.services.llm_client import generate_json_object

        return await generate_json_object(
            _VALIDATE_TEMPLATE.format(
                query=query,
                context=context[:3000],
                answer=answer[:2000],
            ),
            system=_VALIDATE_SYSTEM,
            temperature=0.0,
            max_tokens=300,
        )
    except Exception as exc:
        log.warning("Answer validation failed; allowing answer through: %s", exc)
        return {"is_valid": True, "confidence": 0.5, "issues": []}


def get_fallback_answer() -> str:
    return "Không đủ thông tin để trả lời chính xác dựa trên tài liệu hiện có."
