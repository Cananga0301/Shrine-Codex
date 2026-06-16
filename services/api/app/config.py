from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

POSTGRES_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://legal_bot:legal_bot_pass@postgres:5432/legal_chatbot",
)

QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "law_documents")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
REDIS_CACHE_TTL = int(os.getenv("REDIS_CACHE_TTL", "3600"))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gemini-2.5-flash-lite")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL") or None
DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.5"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))

EMBEDDING_SERVICE_URL = os.getenv("EMBEDDING_SERVICE_URL", "http://embedding:8001").rstrip("/")
RERANKER_SERVICE_URL = os.getenv("RERANKER_SERVICE_URL", "http://reranker:8002").rstrip("/")
INGESTION_SERVICE_URL = os.getenv("INGESTION_SERVICE_URL", "http://ingestion:8003").rstrip("/")

RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "20"))
RERANK_TOP_K = int(os.getenv("RERANK_TOP_K", "5"))
ANSWER_VALIDATION_THRESHOLD = float(os.getenv("ANSWER_VALIDATION_THRESHOLD", "0.40"))

NO_INFO_MESSAGE = "Không tìm thấy nội dung phù hợp trong cơ sở dữ liệu pháp luật."

SYSTEM_PROMPT = """
Bạn là trợ lý pháp lý hành chính Việt Nam.

Quy tắc:
- Chỉ dùng ngữ cảnh được cung cấp.
- Không bịa đặt số hiệu văn bản, Điều/Khoản/Điểm.
- Trả lời tiếng Việt, giọng hành chính rõ ràng.
- Khi có căn cứ trong ngữ cảnh, phải nêu nội dung điều/khoản liên quan và trích dẫn nguồn.
"""

RAG_PROMPT_TEMPLATE = """
NGỮ CẢNH PHÁP LÝ:
{context}

CÂU HỎI:
{question}

YÊU CẦU:
1. Trả lời trực tiếp, dựa sát vào ngữ cảnh.
2. Nếu có Điều/Khoản/Điểm, nêu nội dung liên quan.
3. Cuối câu trả lời có mục "Căn cứ pháp lý" liệt kê số hiệu văn bản và Điều/Khoản nếu có.
4. Nếu ngữ cảnh không đủ thông tin, nói rõ là không tìm thấy trong tài liệu đã nạp.
"""
