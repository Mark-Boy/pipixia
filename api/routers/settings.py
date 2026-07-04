"""
配置路由路由
"""

from fastapi import APIRouter

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("")
async def get_settings():
    """获取系统配置"""
    # TODO: 实现
    raise NotImplementedError("系统配置功能待实现")


@router.put("")
async def update_settings(data: dict):
    """更新系统配置"""
    # TODO: 实现
    raise NotImplementedError("更新系统配置功能待实现")
