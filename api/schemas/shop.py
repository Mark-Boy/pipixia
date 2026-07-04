"""
店铺 Schema
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class ShopCreate(BaseModel):
    user_id: int
    shop_name: str
    platform: str = "shopee_th"
    shop_token: str
    config: Optional[Dict[str, Any]] = {}


class ShopUpdate(BaseModel):
    shop_name: Optional[str] = None
    platform: Optional[str] = None
    shop_token: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class ShopResponse(BaseModel):
    id: int
    user_id: int
    shop_name: str
    platform: str
    is_active: bool
    config: Optional[Dict[str, Any]] = {}
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ShopTokenResponse(BaseModel):
    shop_token: str
