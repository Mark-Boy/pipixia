"""
数据库初始化脚本
"""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from api.database import async_session, engine, Base
from api.models import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def init_db():
    """创建所有表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ 数据库表创建成功")


async def create_admin(username: str = "admin", password: str = "admin123", email: str = "admin@pipixia.com"):
    """创建管理员账号"""
    async with async_session() as session:
        # 检查是否已存在
        existing = await session.execute(
            User.__table__.select().where(User.username == username)
        )
        if existing.first():
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


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "create-admin":
        username = sys.argv[2] if len(sys.argv) > 2 else "admin"
        password = sys.argv[3] if len(sys.argv) > 3 else "admin123"
        asyncio.run(create_admin(username, password))
    else:
        asyncio.run(init_db())
        asyncio.run(create_admin())
