"""
上架记录路由 — 创建 + 查询 + 重试
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from api.database import async_session
from api.models.listing import Listing
from api.models.product import Product

router = APIRouter(prefix="/listings", tags=["Listings"])


def parse_token(credentials_str: Optional[str]) -> HTTPAuthorizationCredentials:
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


async def get_user_id_from_token(credentials_str: Optional[str]) -> int:
    token = parse_token(credentials_str)
    from api.services.auth import decode_token
    payload = decode_token(token.credentials)
    return int(payload["sub"])


@router.get("", response_model=List[dict])
async def get_listings(
    shop_id: Optional[int] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    credentials_str: Optional[str] = Query(None),
):
    """获取上架记录"""
    user_id = await get_user_id_from_token(credentials_str)

    async with async_session() as db:
        query = select(Listing)
        if shop_id:
            query = query.where(Listing.shop_id == shop_id)
        if status_filter:
            query = query.where(Listing.shopee_status == status_filter)

        # 总数
        count_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar()

        # 分页
        query = query.order_by(Listing.created_at.desc())
        query = query.offset((page - 1) * size).limit(size)
        result = await db.execute(query)
        listings = result.scalars().all()

    return [
        {
            "id": listing.id,
            "product_id": listing.product_id,
            "shop_id": listing.shop_id,
            "shopee_item_id": listing.shopee_item_id,
            "shopee_status": listing.shopee_status,
            "listing_price_thb": listing.listing_price_thb,
            "stock": listing.stock,
            "audit_status": listing.audit_status,
            "audit_comment": listing.audit_comment,
            "listing_mode": listing.listing_mode,
            "retry_count": listing.retry_count,
            "last_error": listing.last_error,
            "created_at": listing.created_at.isoformat() if listing.created_at else None,
            "updated_at": listing.updated_at.isoformat() if listing.updated_at else None,
        }
        for listing in listings
    ]


@router.post("")
async def create_listing(
    data: dict,
    credentials_str: Optional[str] = Query(None),
):
    """创建上架任务"""
    user_id = await get_user_id_from_token(credentials_str)

    product_id = data.get("product_id")
    if not product_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少 product_id",
        )

    async with async_session() as db:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="商品不存在",
            )

        # 创建上架记录
        listing = Listing(
            product_id=product_id,
            shop_id=product.shop_id,
            shopee_item_id=None,
            shopee_status="pending",
            listing_price_thb=product.price_thb,
            variation_data=data.get("variation_data", {}),
            audit_status="approved",  # 已审核通过的商品
            listing_mode=data.get("listing_mode", "manual"),
        )
        db.add(listing)
        await db.commit()
        await db.refresh(listing)

    return {
        "id": listing.id,
        "status": "created",
        "message": "上架任务已创建",
    }


@router.post("/{listing_id}/retry")
async def retry_listing(
    listing_id: int,
    credentials_str: Optional[str] = Query(None),
):
    """手动重试"""
    user_id = await get_user_id_from_token(credentials_str)

    async with async_session() as db:
        result = await db.execute(select(Listing).where(Listing.id == listing_id))
        listing = result.scalar_one_or_none()

        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="上架记录不存在",
            )

        # 重试计数
        listing.retry_count = (listing.retry_count or 0) + 1
        listing.shopee_status = "retrying"
        listing.last_error = None
        await db.commit()

    return {
        "status": "retrying",
        "listing_id": listing_id,
        "retry_count": listing.retry_count,
        "message": "正在重试上架",
    }


@router.get("/{listing_id}", response_model=dict)
async def get_listing(
    listing_id: int,
    credentials_str: Optional[str] = Query(None),
):
    """获取上架记录详情"""
    user_id = await get_user_id_from_token(credentials_str)

    async with async_session() as db:
        result = await db.execute(select(Listing).where(Listing.id == listing_id))
        listing = result.scalar_one_or_none()

        if not listing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="上架记录不存在",
            )

    return {
        "id": listing.id,
        "product_id": listing.product_id,
        "shop_id": listing.shop_id,
        "shopee_item_id": listing.shopee_item_id,
        "shopee_status": listing.shopee_status,
        "listing_price_thb": listing.listing_price_thb,
        "stock": listing.stock,
        "variation_data": listing.variation_data,
        "audit_status": listing.audit_status,
        "audit_comment": listing.audit_comment,
        "listing_mode": listing.listing_mode,
        "retry_count": listing.retry_count,
        "last_error": listing.last_error,
        "created_at": listing.created_at.isoformat() if listing.created_at else None,
        "updated_at": listing.updated_at.isoformat() if listing.updated_at else None,
    }
