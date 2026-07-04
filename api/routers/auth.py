"""
认证路由 — JWT Login / Register / Refresh / Logout
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.database import async_session
from api.schemas.user import UserCreate, UserLogin, UserResponse, Token
from api.models.user import User
from api.services.auth import (
    create_access_token,
    create_refresh_token,
    verify_password,
    get_password_hash,
    decode_token,
)

router = APIRouter(prefix="/auth", tags=["Auth"])

# Token Cookie 配置
TOKEN_COOKIE_NAME = "refresh_token"
TOKEN_PATH = "/api/v1"


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(user_data: UserCreate, response: Response = None):
    """用户注册（创建用户 + 颁发 Token）"""
    async with async_session() as db:
        # 检查用户名是否已存在
        existing = await db.execute(
            select(User).where(User.username == user_data.username)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="用户名已存在",
            )

        # 检查邮箱是否已注册
        existing_email = await db.execute(
            select(User).where(User.email == user_data.email)
        )
        if existing_email.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="邮箱已被注册",
            )

        # 创建用户
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            role=user_data.role,
            is_active=True,
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

    return UserResponse.model_validate(new_user)


@router.post("/login", response_model=Token)
async def login(login_data: UserLogin, response: Response = None):
    """用户登录"""
    async with async_session() as db:
        result = await db.execute(
            select(User).where(User.email == login_data.email)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(login_data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="邮箱或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="账号已禁用",
            )

        # 更新最后登录时间
        user.last_login_at = datetime.now(timezone.utc)
        await db.commit()

    # 生成 Token
    access_token = create_access_token(
        user_id=str(user.id), role=user.role
    )
    refresh_token = create_refresh_token(user_id=str(user.id))

    # 设置 Cookie（HttpOnly + Secure + SameSite）
    response.set_cookie(
        key=TOKEN_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=True,  # 生产环境启用
        samesite="lax",
        max_age=604800,  # 7d
        path=TOKEN_PATH,
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    response: Response = None,
):
    """刷新 Token（Token Rotation）"""
    old_token = credentials.credentials
    payload = decode_token(old_token)

    # 验证是 refresh token
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 Token 类型",
        )

    # 验证用户仍然存在且活跃
    user_id = payload.get("sub")
    async with async_session() as db:
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户不存在或已禁用",
            )

    # 生成新 Token
    new_access = create_access_token(
        user_id=str(user.id), role=user.role
    )
    new_refresh = create_refresh_token(user_id=str(user.id))

    response.set_cookie(
        key=TOKEN_COOKIE_NAME,
        value=new_refresh,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=604800,
        path=TOKEN_PATH,
    )

    return Token(
        access_token=new_access,
        refresh_token=new_refresh,
        token_type="bearer",
    )


@router.post("/logout")
async def logout(response: Response):
    """用户登出（清除 Cookie）"""
    response.set_cookie(
        key=TOKEN_COOKIE_NAME,
        value="",
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=0,
        path=TOKEN_PATH,
    )
    return {"message": "登出成功"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
):
    """获取当前用户信息"""
    token = credentials.credentials
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 Token 类型",
        )

    user_id = payload.get("sub")
    async with async_session() as db:
        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户不存在或已禁用",
        )

    return UserResponse.model_validate(user)
