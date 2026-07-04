"""
店铺管理路由
"""

from fastapi import APIRouter, Depends, HTTPException
from api.schemas.shop import ShopCreate, ShopResponse

router = APIRouter(prefix="/shops", tags=["Shops"])


@router.get("", response_model=list[ShopResponse])
async def get_shops():
    """获取店铺列表"""
    # TODO: 实现
    raise NotImplementedError("店铺列表功能待实现")


@router.post("", response_model=ShopResponse)
async def create_shop(data: ShopCreate):
    """添加店铺"""
    # TODO: 实现
    raise NotImplementedError("添加店铺功能待实现")


@router.get("/{shop_id}")
async def get_shop(shop_id: int):
    """获取店铺详情"""
    # TODO: 实现
    raise NotImplementedError("店铺详情功能待实现")


@router.put("/{shop_id}")
async def update_shop(shop_id: int, data: ShopCreate):
    """更新店铺"""
    # TODO: 实现
    raise NotImplementedError("更新店铺功能待实现")


@router.delete("/{shop_id}")
async def delete_shop(shop_id: int):
    """删除店铺"""
    # TODO: 实现
    raise NotImplementedError("删除店铺功能待实现")
