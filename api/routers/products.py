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
from api.models.user import User
from api.services.auth import get_current_user_async
from api.services.storage import upload_image_from_url
from api.services.exchange import convert_cny_to_thb
from api.crawlers.alibaba_1688 import Alibaba1688Crawler
from api.crawlers.pinduoduo import PinduoduoCrawler
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/products", tags=["Products"])

# 爬虫实例池（复用浏览器连接）
_crawler_pool: dict[str, object] = {}


def _get_crawler(platform: str):
    """获取或创建爬虫实例（单例模式）"""
    if platform not in _crawler_pool:
        if platform == "1688":
            _crawler_pool[platform] = Alibaba1688Crawler()
        elif platform == "pdd":
            _crawler_pool[platform] = PinduoduoCrawler()
        else:
            raise ValueError(f"不支持的平台: {platform}")
    return _crawler_pool[platform]


# ==================== 导入商品（必须在 /{product_id} 之前定义）====================

@router.get("/import-product")
async def import_product(
    url: str = Query(..., description="商品链接（1688/拼多多）"),
    shop_id: int = Query(..., description="目标店铺 ID"),
    current_user: User = Depends(get_current_user_async),
):
    """
    导入商品（URL 解析 + Playwright 爬虫抓取）

    流程：
    1. 解析 URL 获取平台类型和商品 ID
    2. 调用对应平台的 Playwright 爬虫抓取商品详情
    3. 上传商品图片到对象存储
    4. 创建商品记录（含利润率自动计算）
    5. 触发翻译工作流（可选）
    """
    # 1. 检测平台并获取爬虫
    source_platform = "unknown"
    crawler = None

    if "1688" in url:
        source_platform = "1688"
        crawler = _get_crawler("1688")
    elif any(kw in url for kw in ["pinduoduo", "yangkeduo", "pdd_goods"]):
        source_platform = "pdd"
        crawler = _get_crawler("pdd")
    else:
        # 尝试通过 URL 内容自动判断
        if any(domain in url for domain in ["1688.com", "detail.1688.com"]):
            source_platform = "1688"
            crawler = _get_crawler("1688")
        elif any(domain in url for domain in ["yangkeduo.com", "mobile.yangkeduo.com"]):
            source_platform = "pdd"
            crawler = _get_crawler("pdd")

    if not crawler:
        raise HTTPException(
            status_code=400,
            detail="不支持的链接类型。请提供 1688 或拼多多商品链接。",
        )

    # 2. 检查店铺归属
    async with async_session() as db:
        shop_result = await db.execute(select(Shop).where(Shop.id == shop_id))
        shop = shop_result.scalar_one_or_none()
        if not shop or shop.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="无权在该店铺下导入商品")

    # 3. 调用爬虫抓取商品详情
    try:
        product_info = await crawler.fetch_product(url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"URL 解析失败: {str(e)}")
    except Exception as e:
        logger.error(f"爬虫抓取失败: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"商品抓取失败: {str(e)}。请检查链接是否有效。",
        )

    if not product_info.title_zh:
        raise HTTPException(
            status_code=422,
            detail="无法获取商品信息。请确认链接是否正确。",
        )

    # 4. 上传商品图片到对象存储
    image_oss_keys = []
    if product_info.images_urls:
        for img_url in product_info.images_urls:
            try:
                oss_key = upload_image_from_url(img_url)
                if oss_key:
                    image_oss_keys.append(oss_key)
            except Exception as e:
                logger.warning(f"图片上传失败 {img_url}: {e}")
                # 图片上传失败不影响商品创建

    # 5. 在数据库中创建或更新商品记录
    async with async_session() as db:
        # 去重检查
        existing = await db.execute(
            select(Product).where(
                Product.shop_id == shop_id,
                Product.source_platform == source_platform,
                Product.source_item_id == product_info.source_item_id,
            )
        )
        if existing.scalar_one_or_none():
            return {
                "status": "exists",
                "product_id": existing.scalar_one_or_none().id,
                "message": "商品已存在，跳过导入",
            }

        # 汇率转换（使用实时汇率）
        try:
            from api.services.exchange import convert_cny_to_thb
            price_thb = convert_cny_to_thb(product_info.price_cny) if product_info.price_cny else None
        except Exception:
            price_thb = round(product_info.price_cny * 5.0, 2) if product_info.price_cny else None
        cost_cny = product_info.cost_cny or product_info.price_cny
        cost_thb = cost_cny * exchange_rate if cost_cny else None

        # 利润率计算
        profit_margin = None
        if price_thb and cost_thb and price_thb > 0:
            profit_margin = round(((price_thb - cost_thb) / price_thb) * 100, 2)

        product = Product(
            shop_id=shop_id,
            source_platform=source_platform,
            source_item_id=product_info.source_item_id,
            title_zh=product_info.title_zh[:512],
            description_zh=product_info.description_zh[:4096] if product_info.description_zh else None,
            price_cny=product_info.price_cny,
            price_thb=price_thb,
            cost_cny=cost_cny,
            profit_margin=profit_margin,
            images_oss_keys=image_oss_keys,
            status="pending",
            risk_status="pending",
        )
        db.add(product)
        await db.commit()
        await db.refresh(product)

    # 6. 触发翻译工作流（异步）
    task_id = None
    try:
        from worker.tasks import translate_product
        task = translate_product.delay(product.id)
        task_id = task.id
    except Exception as e:
        logger.warning(f"翻译任务提交失败: {e}")

    return {
        "status": "success",
        "product_id": product.id,
        "source_platform": source_platform,
        "source_item_id": product_info.source_item_id,
        "title_zh": product_info.title_zh,
        "price_cny": product_info.price_cny,
        "price_thb": price_thb,
        "cost_cny": cost_cny,
        "profit_margin": profit_margin,
        "images_uploaded": len(image_oss_keys),
        "translate_task_id": task_id,
        "message": "商品导入成功",
    }


# ==================== 商品列表 ====================

@router.get("")
async def get_products(
    shop_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    source_platform: Optional[str] = Query(None),
    risk_status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user_async),
):
    """商品列表（分页 + 多条件筛选）"""
    async with async_session() as db:
        query = select(Product)

        # 权限过滤：operator 只能看自己店铺的，admin 可以看所有
        if current_user.role != "admin":
            shop_result = await db.execute(
                select(Shop).where(Shop.user_id == current_user.id)
            )
            shops = shop_result.scalars().all()
            shop_ids = [s.id for s in shops]
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
    current_user: User = Depends(get_current_user_async),
):
    """获取商品详情"""
    async with async_session() as db:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")

        # 权限检查
        if current_user.role != "admin":
            shop_result = await db.execute(
                select(Shop).where(Shop.id == product.shop_id)
            )
            shop = shop_result.scalar_one_or_none()
            if not shop or shop.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="无权查看该商品")

    return ProductResponse.model_validate(product)


# ==================== 创建商品 ====================

@router.post("", response_model=dict, status_code=201)
async def create_product(
    data: ProductCreate,
    current_user: User = Depends(get_current_user_async),
):
    """手动创建商品"""
    async with async_session() as db:
        # 检查店铺归属
        shop_result = await db.execute(select(Shop).where(Shop.id == data.shop_id))
        shop = shop_result.scalar_one_or_none()
        if not shop or shop.user_id != current_user.id:
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

        # 汇率转换（使用实时汇率）
        try:
            from api.services.exchange import convert_cny_to_thb
            price_thb = convert_cny_to_thb(data.price_cny)
        except Exception:
            price_thb = round(data.price_cny * 5.0, 2)
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


# ==================== 翻译 / 上架 / 财务 ====================

@router.post("/{product_id}/translate")
async def trigger_translate(
    product_id: int,
    current_user: User = Depends(get_current_user_async),
):
    """触发 LangGraph 翻译工作流"""
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
    current_user: User = Depends(get_current_user_async),
):
    """触发上架（审核通过后调用）"""
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
    current_user: User = Depends(get_current_user_async),
):
    """手动利润核算"""
    async with async_session() as db:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")

        # 详细利润计算（使用实时汇率）
        try:
            from api.services.exchange import fetch_exchange_rate
            exchange_rate = fetch_exchange_rate()
        except Exception:
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


# ==================== 更新 / 删除 ====================

@router.put("/{product_id}")
async def update_product(
    product_id: int,
    data: ProductUpdate,
    current_user: User = Depends(get_current_user_async),
):
    """更新商品"""
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
    current_user: User = Depends(get_current_user_async),
):
    """删除商品（软删除）"""
    async with async_session() as db:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")

        # 权限检查
        if current_user.role != "admin":
            shop_result = await db.execute(
                select(Shop).where(Shop.id == product.shop_id)
            )
            shop = shop_result.scalar_one_or_none()
            if not shop or shop.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="无权删除该商品")

        product.status = "removed"
        await db.commit()

    return {"message": "商品已删除"}
