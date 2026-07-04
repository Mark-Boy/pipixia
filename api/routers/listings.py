"""
上架记录路由
"""

from fastapi import APIRouter
from typing import Optional

router = APIRouter(prefix="/listings", tags=["Listings"])


@router.get("", response_model=list)
async def get_listings(
    shop_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
):
    """获取上架记录"""
    # TODO: 实现
    raise NotImplementedError("上架记录功能待实现")


@router.post("")
async def create_listing():
    """创建上架任务"""
    # TODO: 实现
    raise NotImplementedError("创建上架任务功能待实现")


@router.post("/{listing_id}/retry")
async def retry_listing(listing_id: int):
    """手动重试"""
    # TODO: 实现
    raise NotImplementedError("重试功能待实现")
