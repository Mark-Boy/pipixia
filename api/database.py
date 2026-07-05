"""
SQLAlchemy 数据库配置
"""

import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import create_engine
from api.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def init_db():
    """同步初始化数据库表（在应用启动时调用）"""
    db_path = engine.url.database
    if db_path and db_path != ':memory:':
        sync_engine = create_engine(f'sqlite:///{os.path.abspath(db_path)}')
        Base.metadata.create_all(sync_engine)


async def get_db() -> AsyncSession:
    """依赖注入：获取数据库会话"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
