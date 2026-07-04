"""
店铺管理路由 — CRUD + Token 加密存储
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from api.database import async_session
from api.schemas.shop import ShopCreate, ShopUpdate, ShopResponse
from api.models.shop import Shop
from api.services.crypto import encrypt_aes256, decrypt_aes256

router = APIRouter(prefix="/shops", tags=["Shops"])


def parse_token(credentials_str: Optional[str]) -> HTTPAuthorizationCredentials:
    """解析 Token 字符串"""
    if not credentials_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少认证 Token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    scheme, _, token = credentials_str.partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 格式错误",
        )
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


@router.get("", response_model=List[ShopResponse])
async def get_shops(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    active: Optional[bool] = Query(None),
    credentials_str: Optional[str] = Query(None),
):
    """店铺列表（支持按状态筛选）"""
    token = parse_token(credentials_str)
    
    async with async_session() as db:
        # 从 token 获取用户 ID（简化：通过 decode_token）
        from api.services.auth import decode_token
        payload = decode_token(token.credentials)
        user_id = int(payload["sub"])

        query = select(Shop).where(Shop.user_id == user_id)
        if active is not None:
            query = query.where(Shop.is_active == active)

        # 获取总数
        count_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar()

        # 分页查询
        query = query.order_by(Shop.created_at.desc())
        query = query.offset((page - 1) * size).limit(size)
        result = await db.execute(query)
        shops = result.scalars().all()

    return [ShopResponse.model_validate(s) for s in shops]


@router.post("", response_model=ShopResponse, status_code=201)
async def create_shop(
    data: ShopCreate,
    credentials_str: Optional[str] = Query(None),
):
    """添加店铺（Token 加密存储）"""
    token = parse_token(credentials_str)
    
    async with async_session() as db:
        from api.services.auth import decode_token
        payload = decode_token(token.credentials)
        user_id = int(payload["sub"])

        # 检查该用户下是否已有同名店铺
        existing = await db.execute(
            select(Shop).where(
                Shop.user_id == user_id,
                Shop.shop_name == data.shop_name,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="店铺名已存在",
            )

        # 加密 Token
        encrypted_token = encrypt_aes256(data.shop_token)

        new_shop = Shop(
            user_id=user_id,
            shop_name=data.shop_name,
            platform=data.platform or "shopee_th",
            shop_token_encrypted=encrypted_token,
            config=data.config or {},
            is_active=True,
        )
        db.add(new_shop)
        await db.commit()
        await db.refresh(new_shop)

    return ShopResponse.model_validate(new_shop)


@router.get("/{shop_id}", response_model=ShopResponse)
async def get_shop(
    shop_id: int,
    credentials_str: Optional[str] = Query(None),
):
    """获取店铺详情"""
    token = parse_token(credentials_str)
    
    async with async_session() as db:
        from api.services.auth import decode_token
        payload = decode_token(token.credentials)
        user_id = int(payload["sub"])

        result = await db.execute(
            select(Shop).where(
                Shop.id == shop_id,
                Shop.user_id == user_id,
            )
        )
        shop = result.scalar_one_or_none()

        if not shop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="店铺不存在",
            )

    return ShopResponse.model_validate(shop)


@router.put("/{shop_id}", response_model=ShopResponse)
async def update_shop(
    shop_id: int,
    data: ShopUpdate,
    credentials_str: Optional[str] = Query(None),
):
    """更新店铺"""
    token = parse_token(credentials_str)
    
    async with async_session() as db:
        from api.services.auth import decode_token
        payload = decode_token(token.credentials)
        user_id = int(payload["sub"])

        result = await db.execute(
            select(Shop).where(
                Shop.id == shop_id,
                Shop.user_id == user_id,
            )
        )
        shop = result.scalar_one_or_none()

        if not shop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="店铺不存在",
            )

        # 更新字段
        if data.shop_name is not None:
            shop.shop_name = data.shop_name
        if data.shop_token is not None:
            shop.shop_token_encrypted = encrypt_aes256(data.shop_token)
        if data.platform is not None:
            shop.platform = data.platform
        if data.config is not None:
            shop.config = data.config
        if data.is_active is not None:
            shop.is_active = data.is_active

        await db.commit()
        await db.refresh(shop)

    return ShopResponse.model_validate(shop)


@router.delete("/{shop_id}")
async def delete_shop(
    shop_id: int,
    credentials_str: Optional[str] = Query(None),
):
    """删除店铺（软删除）"""
    token = parse_token(credentials_str)
    
    async with async_session() as db:
        from api.services.auth import decode_token
        payload = decode_token(token.credentials)
        user_id = int(payload["sub"])

        result = await db.execute(
            select(Shop).where(
                Shop.id == shop_id,
                Shop.user_id == user_id,
            )
        )
        shop = result.scalar_one_or_none()

        if not shop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="店铺不存在",
            )

        # 软删除
        shop.is_active = False
        await db.commit()

    return {"message": "店铺已删除"}


@router.get("/{shop_id}/token")
async def get_shop_token(
    shop_id: int,
    credentials_str: Optional[str] = Query(None),
):
    """获取店铺 Token（解密后返回）"""
    token = parse_token(credentials_str)
    
    async with async_session() as db:
        from api.services.auth import decode_token
        payload = decode_token(token.credentials)
        user_id = int(payload["sub"])

        result = await db.execute(
            select(Shop).where(
                Shop.id == shop_id,
                Shop.user_id == user_id,
            )
        )
        shop = result.scalar_one_or_none()

        if not shop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="店铺不存在",
            )

    # 解密返回
    return {"shop_token": decrypt_aes256(shop.shop_token_encrypted)}
