"""Baseline schema for Shrine-Codex.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-06-17
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION immutable_unaccent(text)
        RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT AS
        $$SELECT unaccent('unaccent', $1)$$
        """
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("doc_number", sa.String(length=255), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("document_type", sa.String(length=50), nullable=True),
        sa.Column("issuer", sa.Text(), nullable=True),
        sa.Column("issued_date", sa.Date(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("law_intents", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_doc_number", "documents", ["doc_number"])
    op.create_index("ix_documents_document_type", "documents", ["document_type"])
    op.create_index("idx_doc_number_type", "documents", ["doc_number", "document_type"])
    op.create_index("idx_doc_issuer", "documents", ["issuer"])
    op.create_index("idx_doc_effective_date", "documents", ["effective_date"])

    op.create_table(
        "chapters",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("chapter_number", sa.String(length=20), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chapters_document_id", "chapters", ["document_id"])
    op.create_index("idx_chapter_doc_order", "chapters", ["document_id", "sort_order"])

    op.create_table(
        "sections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=False),
        sa.Column("section_number", sa.String(length=20), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sections_chapter_id", "sections", ["chapter_id"])
    op.create_index("idx_section_chapter_order", "sections", ["chapter_id", "sort_order"])

    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("chapter_id", sa.Integer(), nullable=True),
        sa.Column("section_id", sa.Integer(), nullable=True),
        sa.Column("article_number", sa.String(length=20), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["chapter_id"], ["chapters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["section_id"], ["sections.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_articles_document_id", "articles", ["document_id"])
    op.create_index("ix_articles_chapter_id", "articles", ["chapter_id"])
    op.create_index("ix_articles_section_id", "articles", ["section_id"])
    op.create_index("idx_article_doc_num", "articles", ["document_id", "article_number"])
    op.create_index("idx_article_chapter", "articles", ["chapter_id"])
    op.create_index("idx_article_section", "articles", ["section_id"])
    op.execute(
        """
        ALTER TABLE articles ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (
          setweight(to_tsvector('simple', immutable_unaccent(coalesce(title,''))), 'A') ||
          setweight(to_tsvector('simple', immutable_unaccent(coalesce(content,''))), 'B')
        ) STORED
        """
    )
    op.execute(
        "CREATE INDEX idx_articles_search_vector ON articles USING GIN(search_vector)"
    )

    op.create_table(
        "clauses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=False),
        sa.Column("clause_number", sa.String(length=20), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clauses_article_id", "clauses", ["article_id"])

    op.create_table(
        "vector_chunks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("article_id", sa.Integer(), nullable=True),
        sa.Column("clause_id", sa.Integer(), nullable=True),
        sa.Column("vector_id", sa.String(length=64), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("chunk_type", sa.String(length=20), server_default="clause", nullable=True),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["clause_id"], ["clauses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("vector_id"),
    )
    op.create_index("ix_vector_chunks_document_id", "vector_chunks", ["document_id"])
    op.create_index("idx_vchunk_vector_id", "vector_chunks", ["vector_id"])
    op.create_index("idx_vchunk_doc_article", "vector_chunks", ["document_id", "article_id"])
    op.create_index("idx_vchunk_type", "vector_chunks", ["chunk_type"])

    op.create_table(
        "chat_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_query", sa.Text(), nullable=False),
        sa.Column("chatbot_answer", sa.Text(), nullable=True),
        sa.Column("documents_used", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_chatlog_created", "chat_logs", ["created_at"])

    op.create_table(
        "chat_conversations",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("context_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_chat_conv_updated", "chat_conversations", ["updated_at"])

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("conversation_id", sa.String(length=32), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["conversation_id"], ["chat_conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_messages_conversation_id", "chat_messages", ["conversation_id"])
    op.create_index("idx_chat_msg_conv_id", "chat_messages", ["conversation_id", "id"])


def downgrade() -> None:
    op.drop_table("chat_messages")
    op.drop_table("chat_conversations")
    op.drop_table("chat_logs")
    op.drop_table("vector_chunks")
    op.drop_table("clauses")
    op.execute("DROP INDEX IF EXISTS idx_articles_search_vector")
    op.execute("ALTER TABLE articles DROP COLUMN IF EXISTS search_vector")
    op.drop_table("articles")
    op.drop_table("sections")
    op.drop_table("chapters")
    op.drop_table("documents")
    op.execute("DROP FUNCTION IF EXISTS immutable_unaccent(text)")
