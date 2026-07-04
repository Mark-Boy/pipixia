"""
商品 Schema
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ProductCreate(BaseModel):
    shop_id: int
    source_platform: str
    source_item_id: str
    title_zh: str
    price_cny: float
    cost_cny: float
    images_urls: Optional[List[str]] = []


class ProductUpdate(BaseModel):
    title_zh: Optional[str] = None
    description_zh: Optional[str] = None
    price_cny: Optional[float] = None
    cost_cny: Optional[float] = None


class ProductResponse(BaseModel):
    id: int
    shop_id: int
    source_platform: str
    source_item_id: str
    title_zh: str
    title_th: Optional[str] = None
    description_zh: Optional[str] = None
    description_th: Optional[str] = None
    price_cny: float
    price_thb: float
    cost_cny: float
    profit_margin: Optional[float] = None
    risk_status: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
