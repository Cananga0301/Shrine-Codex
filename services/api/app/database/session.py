from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import POSTGRES_URL

log = logging.getLogger(__name__)

async_engine = create_async_engine(
    POSTGRES_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)

_session_factory = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except asyncio.CancelledError:
            await session.rollback()
            raise
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except asyncio.CancelledError:
            await session.rollback()
            raise
        except Exception:
            await session.rollback()
            raise


async def close_db() -> None:
    await async_engine.dispose()
    log.info("PostgreSQL connection pool disposed.")
