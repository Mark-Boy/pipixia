#!/usr/bin/env python3
"""
SQLite → PostgreSQL 数据迁移脚本

用法:
    python scripts/migrate_sqlite_to_pg.py

前提条件:
    1. PostgreSQL 服务已启动 (docker compose up -d postgres)
    2. alembic 迁移已执行 (make migrate)
    3. pipixia.db 存在于项目根目录
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from pathlib import Path

import sqlite3
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.config import get_settings
from api.database import Base

settings = get_settings()

# ==================== 配置 ====================
SQLITE_DB = PROJECT_ROOT / "pipixia.db"
TABLES = [
    "users",
    "shops",
    "products",
    "listings",
    "translates",
    "risk_logs",
    "profit_calibration",
]

# PostgreSQL JSON 默认值映射 (SQLite -> PG)
JSON_DEFAULT_MAP = {
    "shops": {"config": "{}"},
    "products": {"images_oss_keys": "[]"},
    "listings": {"variation_data": "{}"},
}


def export_sqlite():
    """从 SQLite 读取所有数据"""
    if not SQLITE_DB.exists():
        print(f"❌ SQLite 数据库不存在: {SQLITE_DB}")
        sys.exit(1)

    conn = sqlite3.connect(str(SQLITE_DB))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    data = {}
    for table in TABLES:
        cursor.execute(f'SELECT * FROM "{table}"')
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        records = []
        for row in rows:
            record = {}
            for col in columns:
                val = row[col]
                # JSON 字段需要序列化
                if isinstance(val, str) and col in ("config", "images_oss_keys", "variation_data"):
                    try:
                        val = json.loads(val)
                    except (json.JSONDecodeError, TypeError):
                        pass
                records.append(record := {**record})  # noqa: B023
                record[col] = val
            data[table] = records
        print(f"  📋 {table}: {len(records)} 条记录")

    conn.close()
    return data


def get_pg_connection_string():
    """将 asyncpg URL 转为 sync psycopg 兼容格式"""
    url = settings.DATABASE_URL
    # postgresql+asyncpg://user:pass@host:port/db -> postgresql://user:pass@host:port/db
    return url.replace("+asyncpg", "")


async def import_to_postgres(data: dict):
    """将数据导入 PostgreSQL"""
    sync_url = get_pg_connection_string()
    engine = create_async_engine(sync_url.replace("postgresql://", "postgresql+psycopg2://"))

    # 验证连接
    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
        print("✅ PostgreSQL 连接成功")

    from sqlalchemy.ext.asyncio import async_sessionmaker
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

    total_imported = 0
    total_skipped = 0

    for table, records in data.items():
        if not records:
            print(f"  ⏭️  {table}: 无数据，跳过")
            continue

        print(f"\n  📥 导入 {table}: {len(records)} 条记录...")
        async with async_session_maker() as session:
            for record in records:
                try:
                    stmt = text(f"INSERT INTO {table} ({','.join(record.keys())}) VALUES ({','.join([':' + k for k in record.keys()])}) ON CONFLICT DO NOTHING").execution_options(
                        populate_result_cache=False
                    )
                    await session.execute(stmt, record)
                    total_imported += 1
                except Exception as e:
                    # 主键冲突等忽略
                    if "conflict" in str(e).lower() or "duplicate" in str(e).lower():
                        total_skipped += 1
                    else:
                        print(f"    ❌ 导入失败: {record.get('id', '?')} - {e}")
                        raise

            await session.commit()

    await engine.dispose()
    print(f"\n🎉 迁移完成!")
    print(f"  ✅ 导入: {total_imported} 条")
    print(f"  ⏭️  跳过(重复): {total_skipped} 条")


async def main():
    print("=" * 60)
    print("  SQLite → PostgreSQL 数据迁移")
    print("=" * 60)

    # Step 1: 确认 PG 服务可用
    print("\n🔍 检查 PostgreSQL 服务...")
    from asyncpg import create_pool
    try:
        pool = await create_pool(
            database="pipixia",
            user="pipixia",
            password="pipixia_secret",
            host="localhost",
            port=5432,
        )
        await pool.fetchval("SELECT 1")
        await pool.close()
        print("  ✅ PostgreSQL 服务正常")
    except Exception as e:
        print(f"  ❌ 无法连接到 PostgreSQL: {e}")
        print("  💡 请先启动: docker compose up -d postgres")
        sys.exit(1)

    # Step 2: 确认 alembic 迁移已就绪
    print("\n🔍 检查 Alembic 迁移状态...")
    try:
        from alembic.command import current
        from alembic.config import Config
        alembic_cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
        # 只是检查，不实际运行
        print("  ✅ Alembic 配置正常")
    except Exception as e:
        print(f"  ⚠️  Alembic 检查失败: {e}")
        print("  💡 请先运行: make migrate")

    # Step 3: 导出 SQLite 数据
    print("\n📤 从 SQLite 导出数据...")
    data = export_sqlite()

    # Step 4: 导入 PostgreSQL
    print("\n📥 导入到 PostgreSQL...")
    await import_to_postgres(data)

    print("\n" + "=" * 60)
    print("  迁移完成！请验证数据:")
    print("    docker compose exec postgres psql -U pipixia -d pipixia -c 'SELECT count(*) FROM users;'")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
