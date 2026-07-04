"""
商品管理路由
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from api.schemas.product import ProductCreate, ProductResponse

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("", response_model=list[ProductResponse])
async def get_products(
    shop_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    source_platform: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """获取商品列表（分页、筛选）"""
    # TODO: 实现
    raise NotImplementedError("商品列表功能待实现")


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(product_id: int):
    """获取商品详情"""
    # TODO: 实现
    raise NotImplementedError("商品详情功能待实现")


@router.post("", response_model=ProductResponse)
async def create_product(data: ProductCreate):
    """创建商品"""
    # TODO: 实现
    raise NotImplementedError("创建商品功能待实现")


@router.post("/import")
async def import_product(url: str):
    """导入商品（URL 解析）"""
    # TODO: 实现 1688/PDD 链接解析
    raise NotImplementedError("商品导入功能待实现")


@router.post("/{product_id}/translate")
async def trigger_translate(product_id: int):
    """触发 LangGraph 翻译工作流"""
    # TODO: 实现
    raise NotImplementedError("翻译功能待实现")


@router.post("/{product_id}/finance/check")
async def check_finance(product_id: int):
    """手动利润核算"""
    # TODO: 实现
    raise NotImplementedError("利润核算功能待实现")
