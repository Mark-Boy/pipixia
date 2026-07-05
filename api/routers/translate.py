"""
翻译工作流路由
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, status, Query, Depends
from sqlalchemy import select, func

from api.database import async_session
from api.models.translate import Translate
from api.models.product import Product
from api.models.risk_log import RiskLog
from api.models.user import User
from api.services.auth import get_current_user_async
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/translate", tags=["翻译工作流"])


@router.post("/trigger")
async def trigger_translate(
    product_id: int,
    current_user: User = Depends(get_current_user_async),
):
    """触发单个商品翻译工作流"""
    async with async_session() as db:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")

        # 启动翻译工作流（异步）
        from worker.tasks import translate_product
        task = translate_product.delay(product_id)

    return {
        "status": "queued",
        "task_id": task.id,
        "product_id": product_id,
        "message": "翻译工作流已提交",
    }


@router.post("/batch")
async def batch_translate(
    product_ids: list[int],
    current_user: User = Depends(get_current_user_async),
):
    """批量翻译"""
    from worker.tasks import batch_translate_task
    task = batch_translate_task.delay(product_ids)

    return {
        "status": "queued",
        "task_id": task.id,
        "total": len(product_ids),
        "message": f"批量翻译任务已提交，共 {len(product_ids)} 个商品",
    }


@router.get("/history", response_model=dict)
async def get_translate_history(
    product_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user_async),
):
    """查询翻译历史"""
    async with async_session() as db:
        query = select(Translate)
        if product_id:
            query = query.where(Translate.product_id == product_id)

        count_result = await db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar() or 0

        query = query.order_by(Translate.created_at.desc())
        query = query.offset((page - 1) * size).limit(size)
        result = await db.execute(query)
        records = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "size": size,
        "records": [
            {
                "id": r.id,
                "product_id": r.product_id,
                "translate_type": r.translate_type,
                "source_text": r.source_text,
                "target_text": r.target_text,
                "confidence_score": r.confidence_score,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ],
    }


@router.post("/sync/{product_id}")
async def sync_translation(
    product_id: int,
    current_user: User = Depends(get_current_user_async),
):
    """同步翻译结果到商品（审核前自动调用）"""
    async with async_session() as db:
        # 获取所有翻译记录
        result = await db.execute(
            select(Translate).where(
                Translate.product_id == product_id,
                Translate.status == "completed",
            )
        )
        records = result.scalars().all()

        if not records:
            raise HTTPException(status_code=404, detail="无翻译记录")

        # 更新商品
        product_result = await db.execute(select(Product).where(Product.id == product_id))
        product = product_result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")

        for record in records:
            if record.translate_type == "title":
                product.title_th = record.target_text
            elif record.translate_type == "description":
                product.description_th = record.target_text

        await db.commit()

    return {
        "status": "synced",
        "product_id": product_id,
        "message": "翻译结果已同步到商品",
    }
