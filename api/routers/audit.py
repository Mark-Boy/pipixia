"""
审核路由 — 审核队列 + 审核操作
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session

from api.database import async_session
from api.schemas.audit import AuditRequest, AuditResponse
from api.models.product import Product
from api.models.listing import Listing

router = APIRouter(prefix="/audit", tags=["Audit"])


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


@router.get("/queue", response_model=List[AuditResponse])
async def get_audit_queue(
    status_filter: str = Query("pending", alias="status"),
    shop_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    credentials_str: Optional[str] = Query(None),
):
    """获取审核队列"""
    user_id = await get_user_id_from_token(credentials_str)

    async with async_session() as db:
        query = select(Product).where(
            Product.status == status_filter,
        )
        if shop_id:
            query = query.where(Product.shop_id == shop_id)

        # 总数
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        # 分页
        query = query.order_by(Product.created_at.desc())
        query = query.offset((page - 1) * size).limit(size)
        result = await db.execute(query)
        products = result.scalars().all()

    responses = []
    for product in products:
        responses.append(AuditResponse(
            id=product.id,
            product_id=product.id,
            status=product.status,
            comment=None,
        ))
    return responses


@router.post("/{product_id}/approve")
async def approve_product(
    product_id: int,
    credentials_str: Optional[str] = Query(None),
):
    """审核通过"""
    user_id = await get_user_id_from_token(credentials_str)

    async with async_session() as db:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="商品不存在",
            )

        # 更新商品状态
        product.status = "audited"
        await db.commit()

    return {
        "status": "approved",
        "product_id": product_id,
        "message": "审核通过",
    }


@router.post("/{product_id}/reject")
async def reject_product(
    product_id: int,
    data: AuditRequest = None,
    credentials_str: Optional[str] = Query(None),
):
    """审核拒绝"""
    user_id = await get_user_id_from_token(credentials_str)

    async with async_session() as db:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="商品不存在",
            )

        # 更新商品状态
        product.status = "rejected"
        await db.commit()

    return {
        "status": "rejected",
        "product_id": product_id,
        "comment": data.comment if data else None,
        "message": "审核拒绝",
    }


@router.post("/batch/approve")
async def batch_approve(
    ids: list[int],
    credentials_str: Optional[str] = Query(None),
):
    """批量通过"""
    user_id = await get_user_id_from_token(credentials_str)

    async with async_session() as db:
        result = await db.execute(select(Product).where(Product.id.in_(ids)))
        products = result.scalars().all()

        count = 0
        for product in products:
            if product.status == "pending":
                product.status = "audited"
                count += 1

        await db.commit()

    return {
        "status": "batch_approved",
        "approved_count": count,
        "total_count": len(ids),
        "message": f"批量审核完成，通过 {count} 个商品",
    }


@router.post("/batch/reject")
async def batch_reject(
    ids: list[int],
    comment: str = "",
    credentials_str: Optional[str] = Query(None),
):
    """批量拒绝"""
    user_id = await get_user_id_from_token(credentials_str)

    async with async_session() as db:
        result = await db.execute(select(Product).where(Product.id.in_(ids)))
        products = result.scalars().all()

        count = 0
        for product in products:
            if product.status == "pending":
                product.status = "rejected"
                count += 1

        await db.commit()

    return {
        "status": "batch_rejected",
        "rejected_count": count,
        "total_count": len(ids),
        "comment": comment,
        "message": f"批量审核完成，拒绝 {count} 个商品",
    }


@router.post("/{product_id}/list")
async def trigger_listing(
    product_id: int,
    credentials_str: Optional[str] = Query(None),
):
    """触发上架（审核通过后调用）"""
    user_id = await get_user_id_from_token(credentials_str)

    async with async_session() as db:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="商品不存在",
            )

        if product.status != "audited":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="商品未通过审核，无法上架",
            )

    # 调用 Celery 上架任务
    from worker.tasks import listing_product
    try:
        task = listing_product.delay(product_id, None)
    except Exception:
        # Celery 不可用时直接执行
        result = listing_product(product_id, None)
        return {
            "status": "success",
            "result": result,
            "product_id": product_id,
            "message": "上架任务完成",
        }

    return {
        "status": "queued",
        "task_id": task.id,
        "product_id": product_id,
        "message": f"上架任务已提交，商品 ID: {product_id}",
    }
