"""
认证路由
"""

from fastapi import APIRouter, Depends, HTTPException, status
from api.schemas.user import UserCreate, UserLogin, UserResponse, Token

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    """用户注册"""
    # TODO: 实现注册逻辑
    raise NotImplementedError("注册功能待实现")


@router.post("/login", response_model=Token)
async def login(user_data: UserLogin):
    """用户登录"""
    # TODO: 实现登录逻辑
    raise NotImplementedError("登录功能待实现")


@router.post("/refresh", response_model=Token)
async def refresh_token():
    """刷新 Token"""
    # TODO: 实现刷新逻辑
    raise NotImplementedError("刷新 Token 功能待实现")
