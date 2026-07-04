"""
翻译工作流路由
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, status, Query
from sqlalchemy import select, func

from api.database import async_session
from api.models.translate import Translate
from api.models.product import Product
from api.models.risk_log import RiskLog
from api.langgraph.graph import run_translation_workflow
from api.services.auth import decode_token
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/translate", tags=["翻译工作流"])


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


@router.post("/trigger")
async def trigger_translate(
    product_id: int,
    credentials_str: Optional[str] = Query(None),
):
    """触发单个商品翻译工作流"""
    user_info = parse_credentials(credentials_str)

    async with async_session() as db:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")

        # 启动翻译工作流（异步）
        from celery_app import celery_app
        task = celery_app.send_task(
            "worker.tasks.translate_product",
            args=[product_id],
        )

    return {
        "status": "queued",
        "task_id": task.id,
        "product_id": product_id,
        "message": "翻译工作流已提交",
    }


@router.post("/batch")
async def batch_translate(
    product_ids: list[int],
    credentials_str: Optional[str] = Query(None),
):
    """批量翻译"""
    user_info = parse_credentials(credentials_str)

    from celery_app import celery_app
    task = celery_app.send_task(
        "worker.tasks.batch_translate",
        args=[product_ids],
    )

    return {
        "status": "queued",
        "task_id": task.id,
        "total": len(product_ids),
        "message": f"批量翻译任务已提交，共 {len(product_ids)} 个商品",
    }


@router.get("/history")
async def get_translate_history(
    product_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    credentials_str: Optional[str] = Query(None),
):
    """查询翻译历史"""
    user_info = parse_credentials(credentials_str)

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
    credentials_str: Optional[str] = Query(None),
):
    """同步翻译结果到商品（审核前自动调用）"""
    user_info = parse_credentials(credentials_str)

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
