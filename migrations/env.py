"""
Alembic 配置 — 支持异步 PostgreSQL 迁移

用法:
    alembic history          # 查看迁移历史（不需要数据库连接）
    alembic heads            # 查看当前头节点
    alembic check            # 检查迁移是否缺失
    alembic upgrade head     # 执行迁移到最新版本
    alembic downgrade -1     # 回退一次迁移
"""

import sys
import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import pool
from alembic import context

from api.database import Base
from api.config import get_settings

settings = get_settings()

# Alembic Config 对象
config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# 日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 要迁移的模型的 Base
target_metadata = Base.metadata


def run_migrations_offline(url: str = "") -> None:
    """Run migrations in 'offline' mode.

    用于: alembic history, alembic heads 等不需要数据库连接的命令
    """
    ctx_url = url or config.get_main_option("sqlalchemy.url")
    context.configure(
        url=ctx_url,
        target_metadata=target_metadata,
        literal_binds=False,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """实际执行迁移的回调函数"""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode with async engine.

    用于: alembic upgrade, alembic downgrade 等需要数据库连接的命令
    """
    connectable = create_async_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def _is_no_db_command() -> bool:
    """判断当前是否为不需要数据库连接的命令。

    alembic 命令行通过 sys.argv 传入子命令，
    history / heads 等不需要连接数据库。
    """
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    no_db_commands = {"history", "heads"}
    return cmd in no_db_commands


if _is_no_db_command():
    # 不需要数据库连接的命令：纯离线模式
    run_migrations_offline()
elif context.is_offline_mode():
    # alembic --offline 显式参数
    run_migrations_offline()
else:
    # 需要数据库连接的命令：online 异步模式
    asyncio.run(run_migrations_online())
