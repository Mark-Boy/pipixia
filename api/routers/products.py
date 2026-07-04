"""
商品管理路由 — CRUD + 导入 + 翻译 + 利润核算
"""

from typing import Optional, List
import re
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from api.database import async_session
from api.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from api.models.product import Product
from api.models.shop import Shop
from api.models.translate import Translate
from api.models.risk_log import RiskLog
from api.services.auth import decode_token
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/products", tags=["Products"])


def parse_credentials(credentials_str: Optional[str]) -> dict:
    """解析 Token，返回用户信息"""
    if not credentials_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少认证 Token",
        )
    scheme, _, token = credentials_str.partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 格式错误")
    payload = decode_token(token)
    return {"user_id": int(payload["sub"]), "role": payload.get("role", "operator")}


@router.get("", response_model=List[dict])
async def get_products(
    shop_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    source_platform: Optional[str] = Query(None),
    risk_status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    credentials_str: Optional[str] = Query(None),
):
    """商品列表（分页 + 多条件筛选）"""
    user_info = parse_credentials(credentials_str)

    async with async_session() as db:
        # 权限过滤：operator 只能看自己店铺的，admin 可以看所有
        query = select(Product)
        if user_info["role"] != "admin":
            shop_ids = await db.execute(
                select(Shop.id).where(Shop.user_id == user_info["user_id"])
            )
            shop_ids = [s.id for s in shop_ids.scalars().all()]
            if shop_ids:
                query = query.where(Product.shop_id.in_(shop_ids))

        if shop_id:
            query = query.where(Product.shop_id == shop_id)
        if status_filter:
            query = query.where(Product.status == status_filter)
        if source_platform:
            query = query.where(Product.source_platform == source_platform)
        if risk_status:
            query = query.where(Product.risk_status == risk_status)

        # 总数
        count_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar() or 0

        # 分页
        query = query.order_by(Product.created_at.desc())
        query = query.offset((page - 1) * size).limit(size)
        result = await db.execute(query)
        products = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "size": size,
        "products": [
            {
                "id": p.id,
                "shop_id": p.shop_id,
                "source_platform": p.source_platform,
                "source_item_id": p.source_item_id,
                "title_zh": p.title_zh,
                "title_th": p.title_th,
                "price_cny": p.price_cny,
                "price_thb": p.price_thb,
                "cost_cny": p.cost_cny,
                "profit_margin": p.profit_margin,
                "risk_status": p.risk_status,
                "status": p.status,
                "images_oss_keys": p.images_oss_keys or [],
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in products
        ],
    }


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    credentials_str: Optional[str] = Query(None),
):
    """获取商品详情"""
    user_info = parse_credentials(credentials_str)

    async with async_session() as db:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")

        # 权限检查
        if user_info["role"] != "admin":
            shop_result = await db.execute(
                select(Shop).where(Shop.id == product.shop_id)
            )
            shop = shop_result.scalar_one_or_none()
            if not shop or shop.user_id != user_info["user_id"]:
                raise HTTPException(status_code=403, detail="无权查看该商品")

    return ProductResponse.model_validate(product)


@router.post("", response_model=dict, status_code=201)
async def create_product(
    data: ProductCreate,
    credentials_str: Optional[str] = Query(None),
):
    """手动创建商品"""
    user_info = parse_credentials(credentials_str)

    async with async_session() as db:
        # 检查店铺归属
        shop_result = await db.execute(select(Shop).where(Shop.id == data.shop_id))
        shop = shop_result.scalar_one_or_none()
        if not shop or shop.user_id != user_info["user_id"]:
            raise HTTPException(status_code=403, detail="无权在该店铺下创建商品")

        # 去重检查
        existing = await db.execute(
            select(Product).where(
                Product.shop_id == data.shop_id,
                Product.source_platform == data.source_platform,
                Product.source_item_id == data.source_item_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="商品已存在")

        # 汇率转换（1 CNY = 5 THB）
        exchange_rate = 5.0
        price_thb = round(data.price_cny * exchange_rate, 2)
        cost_thb = data.cost_cny * exchange_rate

        # 利润率计算
        profit_margin = round(
            ((price_thb - cost_thb) / price_thb) * 100, 2
        ) if price_thb > 0 else 0

        product = Product(
            shop_id=data.shop_id,
            source_platform=data.source_platform,
            source_item_id=data.source_item_id,
            title_zh=data.title_zh,
            description_zh=data.description_zh if hasattr(data, "description_zh") else None,
            price_cny=data.price_cny,
            price_thb=price_thb,
            cost_cny=data.cost_cny,
            profit_margin=profit_margin,
            images_oss_keys=data.images_urls if hasattr(data, "images_urls") else [],
            status="pending",
            risk_status="pending",
        )
        db.add(product)
        await db.commit()
        await db.refresh(product)

    return {
        "id": product.id,
        "status": "created",
        "profit_margin": profit_margin,
        "message": "商品创建成功",
    }


@router.post("/import")
async def import_product(
    url: str = Query(..., description="商品链接"),
    shop_id: int = Query(...),
    credentials_str: Optional[str] = Query(None),
):
    """
    导入商品（URL 解析 + 爬虫抓取）
    
    流程：
    1. 解析 URL 获取平台类型和商品 ID
    2. 调用 Playwright 抓取商品详情（标题、图片、价格、成本）
    3. 创建商品记录
    4. 触发翻译工作流
    """
    user_info = parse_credentials(credentials_str)

    # 1. 解析 URL 获取平台
    source_platform = "unknown"
    if "1688.com" in url or "1688" in url:
        source_platform = "1688"
    elif "pinduoduo.com" in url or "duoduo" in url:
        source_platform = "pdd"
    else:
        raise HTTPException(status_code=400, detail="不支持的链接类型")

    # 2. 提取商品 ID
    match = re.search(r"/(\d+)", url)
    if not match:
        raise HTTPException(status_code=400, detail="无法从 URL 提取商品 ID")
    source_item_id = match.group(1)

    # 3. 检查店铺归属
    async with async_session() as db:
        shop_result = await db.execute(select(Shop).where(Shop.id == shop_id))
        shop = shop_result.scalar_one_or_none()
        if not shop or shop.user_id != user_info["user_id"]:
            raise HTTPException(status_code=403, detail="无权在该店铺下导入商品")

    # 4. 调用爬虫抓取商品详情（TODO: 接入 Playwright 爬虫）
    # 暂时返回占位数据
    return {
        "status": "queued",
        "task_type": "import",
        "url": url,
        "shop_id": shop_id,
        "source_platform": source_platform,
        "source_item_id": source_item_id,
        "message": "导入任务已提交，等待抓取",
    }


@router.post("/{product_id}/translate")
async def trigger_translate(
    product_id: int,
    credentials_str: Optional[str] = Query(None),
):
    """触发 LangGraph 翻译工作流"""
    user_info = parse_credentials(credentials_str)

    async with async_session() as db:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")

        # 调用 Celery 异步翻译
        from worker.tasks import translate_product
        task = translate_product.delay(product_id)

    return {
        "status": "queued",
        "task_id": task.id,
        "product_id": product_id,
        "message": "翻译工作流已提交",
    }


@router.post("/{product_id}/list")
async def trigger_listing(
    product_id: int,
    credentials_str: Optional[str] = Query(None),
):
    """触发上架（审核通过后调用）"""
    user_info = parse_credentials(credentials_str)

    async with async_session() as db:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")

        if product.status not in ("audited", "reviewed"):
            raise HTTPException(
                status_code=400,
                detail="商品未通过审核，无法上架",
            )

        # 获取店铺 Token
        shop_result = await db.execute(select(Shop).where(Shop.id == product.shop_id))
        shop = shop_result.scalar_one_or_none()
        if not shop:
            raise HTTPException(status_code=404, detail="店铺不存在")

        # 解密 Token
        from api.services.crypto import decrypt_aes256
        shop_token = decrypt_aes256(shop.shop_token_encrypted)

        # 调用 Celery 上架任务
        from worker.tasks import listing_product
        task = listing_product.delay(product_id, None)

    return {
        "status": "queued",
        "task_id": task.id,
        "product_id": product_id,
        "message": "上架任务已提交",
    }


@router.post("/{product_id}/finance/check")
async def check_finance(
    product_id: int,
    credentials_str: Optional[str] = Query(None),
):
    """手动利润核算"""
    user_info = parse_credentials(credentials_str)

    async with async_session() as db:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")

        # 详细利润计算
        exchange_rate = 5.0
        revenue_thb = product.price_thb or 0
        cost_cny = product.cost_cny or 0
        cost_thb = cost_cny * exchange_rate

        commission_rate = 0.05
        commission_thb = revenue_thb * commission_rate
        platform_fee = 3.0
        logistics = 40.0

        total_cost_thb = cost_thb + commission_thb + platform_fee + logistics
        profit_thb = revenue_thb - total_cost_thb
        profit_margin = round((profit_thb / revenue_thb) * 100, 2) if revenue_thb > 0 else 0

        # 熔断阈值
        is_blocked = profit_margin < 10  # 低于 10% 熔断

    return {
        "product_id": product_id,
        "exchange_rate": exchange_rate,
        "revenue_thb": round(revenue_thb, 2),
        "cost_breakdown": {
            "product_cost_thb": round(cost_thb, 2),
            "commission_thb": round(commission_thb, 2),
            "platform_fee_thb": round(platform_fee, 2),
            "logistics_thb": round(logistics, 2),
        },
        "total_cost_thb": round(total_cost_thb, 2),
        "profit_thb": round(profit_thb, 2),
        "profit_margin": profit_margin,
        "is_blocked": is_blocked,
        "block_threshold": 10,
    }


@router.put("/{product_id}")
async def update_product(
    product_id: int,
    data: ProductUpdate,
    credentials_str: Optional[str] = Query(None),
):
    """更新商品"""
    user_info = parse_credentials(credentials_str)

    async with async_session() as db:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")

        update_fields = data.model_dump(exclude_unset=True)
        for field_name, value in update_fields.items():
            if hasattr(product, field_name):
                setattr(product, field_name, value)

        await db.commit()
        await db.refresh(product)

    return ProductResponse.model_validate(product)


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    credentials_str: Optional[str] = Query(None),
):
    """删除商品（软删除）"""
    user_info = parse_credentials(credentials_str)

    async with async_session() as db:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")

        # 权限检查
        if user_info["role"] != "admin":
            shop_result = await db.execute(
                select(Shop).where(Shop.id == product.shop_id)
            )
            shop = shop_result.scalar_one_or_none()
            if not shop or shop.user_id != user_info["user_id"]:
                raise HTTPException(status_code=403, detail="无权删除该商品")

        product.status = "removed"
        await db.commit()

    return {"message": "商品已删除"}
