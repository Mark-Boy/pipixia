"""
数据库初始化脚本

注意: 表结构由 Alembic 管理，不再需要手动创建表。
只需执行: make migrate
"""

import asyncio
import sys
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from api.database import async_session, engine, Base
from api.models import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def check_tables_exist():
    """检查数据库表是否已创建（通过 Alembic 迁移）"""
    async with engine.begin() as conn:
        result = await conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')"
        ))
        exists = result.scalar()
    if exists:
        print("✅ 数据库表已存在（通过 Alembic 迁移创建）")
        return True
    else:
        print("❌ 数据库表不存在")
        print("💡 请先运行: make migrate")
        return False


async def create_admin(username: str = "admin", password: str = "admin123", email: str = "admin@pipixia.com"):
    """创建管理员账号"""
    async with async_session() as session:
        # 检查是否已存在
        existing = await session.execute(
            select(User).where(User.username == username)
        )
        user = existing.scalar_one_or_none()
        if user:
            print(f"⚠️ 用户 {username} 已存在")
            return

        user = User(
            username=username,
            email=email,
            password_hash=pwd_context.hash(password),
            role="admin",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        print(f"✅ 管理员账号创建成功: {username}")


async def show_db_info():
    """显示数据库基本信息"""
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """))
        tables = [row[0] for row in result.fetchall()]
        print(f"📊 数据库中的表: {', '.join(tables)}")

        for table in tables:
            result = await conn.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
            count = result.scalar()
            print(f"  {table}: {count} 条记录")


async def main():
    if len(sys.argv) > 1 and sys.argv[1] == "create-admin":
        username = sys.argv[2] if len(sys.argv) > 2 else "admin"
        password = sys.argv[3] if len(sys.argv) > 3 else "admin123"
        exists = await check_tables_exist()
        if exists:
            await create_admin(username, password)
        return

    if len(sys.argv) > 1 and sys.argv[1] == "info":
        exists = await check_tables_exist()
        if exists:
            await show_db_info()
        return

    # 默认：只显示信息
    exists = await check_tables_exist()
    if exists:
        await show_db_info()


if __name__ == "__main__":
    asyncio.run(main())
