"""
Shopee API 路由

功能:
- 店铺授权 (OAuth)
- 店铺信息获取
- 商品列表 / 详情
- 自动采集 + 上传
- 库存同步
- 同步状态查询
- 调度器管理

不包含报关功能
"""

import logging
import time
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.database import async_session, get_db
from api.models.shop import Shop
from api.models.product import Product
from api.models.listing import Listing
from api.services.crypto import decrypt_aes256, encrypt_aes256
from api.services.shopee_v2 import ShopeeV2Client, create_shopee_client
from api.services.shopee_sync import ShopeeSyncService
from api.services.scheduler import get_scheduler, start_scheduler
from api.models.user import User
from api.services.auth import get_current_user_async

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/shopee", tags=["Shopee"])


@router.get("/status", description="获取 Shopee 同步状态")
async def get_shopee_status(current_user: User = Depends(get_current_user_async)):
    """获取 Shopee 同步状态 (待上架、已上架、失败等)"""
    async with async_session() as db:
        service = ShopeeSyncService(db)
        return service.get_sync_status()


@router.post("/list", description="自动采集 + 自动上传 (批量)")
async def auto_list_products(
    max_products: int = Query(20, ge=1, le=100, description="最大处理商品数"),
    marketplace: str = Query("shopee_th", description="目标市场"),
    current_user: User = Depends(get_current_user_async),
):
    """
    自动采集 + 自动上传商品到 Shopee

    流程:
    1. 获取待上架商品 (status=pending)
    2. AI 翻译标题/描述
    3. 上传图片到 Shopee
    4. 创建/更新 Shopee 商品
    5. 记录上架结果

    不包含报关功能
    """
    async with async_session() as db:
        service = ShopeeSyncService(db)
        return service.auto_list_all(max_products=max_products, marketplace=marketplace)


@router.post("/sync-stock", description="同步库存到 Shopee")
async def sync_stock_to_shopee(
    shop_id: int = Query(..., ge=1, description="店铺 ID"),
    marketplace: str = Query("shopee_th", description="目标市场"),
    current_user: User = Depends(get_current_user_async),
):
    """同步本地库存到 Shopee"""
    async with async_session() as db:
        service = ShopeeSyncService(db)
        return service.auto_update_stock(shop_id=shop_id, marketplace=marketplace)


@router.post("/sync-products", description="从 Shopee 同步商品列表")
async def sync_products_from_shopee(
    shop_id: int = Query(..., ge=1, description="店铺 ID"),
    marketplace: str = Query("shopee_th", description="目标市场"),
    current_user: User = Depends(get_current_user_async),
):
    """从 Shopee 拉取商品列表同步到本地"""
    async with async_session() as db:
        service = ShopeeSyncService(db)
        return service.sync_product_list(shop_id=shop_id, marketplace=marketplace)


@router.get("/shop-info", description="获取店铺信息")
async def get_shop_info(
    shop_id: int = Query(..., ge=1, description="店铺 ID"),
    marketplace: str = Query("shopee_th", description="目标市场"),
    current_user: User = Depends(get_current_user_async),
):
    """获取 Shopee 店铺信息 (shop_name, marketplace, currency 等)"""
    async with async_session() as db:
        result = await db.execute(select(Shop).where(Shop.id == shop_id, Shop.is_active == True))  # noqa
        shop = result.scalar_one_or_none()

        if not shop:
            raise HTTPException(404, "店铺不存在或未激活")

        shop_token = decrypt_aes256(shop.shop_token_encrypted)
        client = create_shopee_client(
            shop_id=shop.id,
            token=shop_token,
            marketplace=marketplace,
            sandbox=True,
        )

        try:
            return client.get_shop_detail()
        except Exception as e:
            raise HTTPException(500, f"获取店铺信息失败: {e}")


@router.get("/products", description="获取商品列表")
async def get_products(
    shop_id: int = Query(None, ge=1, description="店铺 ID"),
    status_filter: str = Query("ALL", description="状态筛选: ALL/pending/listed/failed"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user_async),
):
    """获取商品列表 (本地)"""
    async with async_session() as db:
        query = select(Product)
        if shop_id:
            query = query.where(Product.shop_id == shop_id)
        if status_filter != "ALL":
            query = query.where(Product.status == status_filter)

        total_result = await db.execute(select(db.func.count()).select_from(query.subquery()))
        total = total_result.scalar() or 0

        query = query.order_by(Product.created_at.desc())
        query = query.offset((page - 1) * size).limit(size)
        result = await db.execute(query)
        products = result.scalars().all()

        return {
            "total": total,
            "page": page,
            "size": size,
            "products": [{
                "id": p.id,
                "title_zh": p.title_zh,
                "title_th": p.title_th,
                "price_cny": p.price_cny,
                "price_thb": p.price_thb,
                "cost_cny": p.cost_cny,
                "status": p.status,
                "risk_status": p.risk_status,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            } for p in products],
        }


@router.get("/listings", description="获取上架记录")
async def get_listings(
    shop_id: int = Query(None, ge=1, description="店铺 ID"),
    audit_status: str = Query(None, description="审核状态"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user_async),
):
    """获取商品上架记录"""
    async with async_session() as db:
        query = select(Listing)
        if shop_id:
            query = query.where(Listing.shop_id == shop_id)
        if audit_status:
            query = query.where(Listing.audit_status == audit_status)

        total_result = await db.execute(select(db.func.count()).select_from(query.subquery()))
        total = total_result.scalar() or 0

        query = query.order_by(Listing.created_at.desc())
        query = query.offset((page - 1) * size).limit(size)
        result = await db.execute(query)
        listings = result.scalars().all()

        return {
            "total": total,
            "page": page,
            "size": size,
            "listings": [{
                "id": l.id,
                "product_id": l.product_id,
                "shopee_item_id": l.shopee_item_id,
                "shopee_status": l.shopee_status,
                "listing_price_thb": l.listing_price_thb,
                "stock": l.stock,
                "listing_mode": l.listing_mode,
                "audit_status": l.audit_status,
                "retry_count": l.retry_count,
                "last_error": l.last_error,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            } for l in listings],
        }


@router.post("/authorize", description="店铺 OAuth 授权")
async def authorize_shop(
    shop_id: str = Query(..., description="Shopee 店铺 ID"),
    callback_url: str = Query("http://localhost:8000/api/v1/shopee/callback", description="OAuth 回调地址"),
    current_user: User = Depends(get_current_user_async),
):
    """生成 OAuth 授权链接"""
    from api.config import get_settings
    settings = get_settings()

    client = ShopeeV2Client(
        partner_id=str(settings.SHOPEE_MARKET_ID or 146),
        client_secret=settings.SHOPEE_SECRET or "test_secret",
        access_token="",
        marketplace="shopee_th",
        sandbox=True,
    )
    auth_url = client.get_auth_url(shop_id, callback_url)
    return {"auth_url": auth_url, "shop_id": shop_id}


@router.post("/oauth/callback", description="OAuth 回调处理")
async def oauth_callback(
    shop_id: str = Query(..., description="店铺 ID"),
    code: str = Query(..., description="OAuth code"),
    state: str = Query(None, description="状态参数"),
    current_user: User = Depends(get_current_user_async),
):
    """处理 OAuth 回调，获取 access_token 并保存"""
    from api.config import get_settings
    settings = get_settings()

    client = ShopeeV2Client(
        partner_id=str(settings.SHOPEE_MARKET_ID or 146),
        client_secret=settings.SHOPEE_SECRET or "test_secret",
        access_token="",
        marketplace="shopee_th",
        sandbox=True,
    )

    try:
        token_result = client.get_access_token(shop_id, code)
        access_token = token_result.get("access_token")

        if not access_token:
            raise HTTPException(400, f"获取 access_token 失败: {token_result}")

        # 获取店铺信息
        client.access_token = access_token
        shop_detail = client.get_shop_detail()

        # 保存到数据库
        async with async_session() as db:
            result = await db.execute(select(Shop).where(Shop.shop_id == shop_id))
            shop = result.scalar_one_or_none()

            if shop:
                shop.shop_token_encrypted = encrypt_aes256(access_token)
                shop.shop_name = shop_detail.get("shop_name", shop.shop_name)
                await db.commit()
            else:
                new_shop = Shop(
                    user_id=current_user.id,
                    shop_name=shop_detail.get("shop_name", ""),
                    shop_id=shop_id,
                    shop_token_encrypted=encrypt_aes256(access_token),
                    is_active=True,
                )
                db.add(new_shop)
                await db.commit()

        return {
            "success": True,
            "shop_id": shop_id,
            "shop_name": shop_detail.get("shop_name"),
            "access_token": access_token,
        }

    except Exception as e:
        raise HTTPException(500, f"OAuth 回调处理失败: {e}")


@router.post("/start-scheduler", description="启动自动同步调度器")
async def start_sync_scheduler(current_user: User = Depends(get_current_user_async)):
    """启动每分钟自动同步调度器"""
    start_scheduler()
    return {"message": "Shopee 同步调度器已启动 (每分钟自动同步)", "interval": "60s"}


@router.get("/scheduler/status", description="调度器状态")
async def get_scheduler_status(current_user: User = Depends(get_current_user_async)):
    """获取调度器状态"""
    scheduler = get_scheduler()
    return scheduler.get_stats()


@router.post("/scheduler/stop", description="停止调度器")
async def stop_sync_scheduler(current_user: User = Depends(get_current_user_async)):
    """停止自动同步调度器"""
    scheduler = get_scheduler()
    scheduler.stop()
    return {"message": "Shopee 同步调度器已停止"}
