"""
审核路由
"""

from fastapi import APIRouter
from api.schemas.audit import AuditRequest, AuditResponse

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("", response_model=list[AuditResponse])
async def get_audit_queue(status: str = "pending"):
    """获取审核队列"""
    # TODO: 实现
    raise NotImplementedError("审核队列功能待实现")


@router.post("/{product_id}/approve")
async def approve_product(product_id: int):
    """审核通过"""
    # TODO: 实现
    raise NotImplementedError("审核通过功能待实现")


@router.post("/{product_id}/reject")
async def reject_product(product_id: int, data: AuditRequest):
    """审核拒绝"""
    # TODO: 实现
    raise NotImplementedError("审核拒绝功能待实现")


@router.post("/batch/approve")
async def batch_approve(ids: list[int]):
    """批量通过"""
    # TODO: 实现
    raise NotImplementedError("批量通过功能待实现")


@router.post("/batch/reject")
async def batch_reject(ids: list[int], comment: str):
    """批量拒绝"""
    # TODO: 实现
    raise NotImplementedError("批量拒绝功能待实现")
