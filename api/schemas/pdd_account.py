"""
拼多多采集账号相关 Schema
"""

from typing import Optional, List, Any
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime


# ==================== 拼多多采集账号 ====================

class PddAccountBase(BaseModel):
    """拼多多账号基础字段"""
    account_name: str = Field(..., min_length=1, max_length=64, description="账号备注名")
    phone: Optional[str] = Field(None, pattern=r"^1\d{10}$", description="手机号")
    notes: Optional[str] = Field(None, max_length=500, description="备注")


class PddAccountCreate(PddAccountBase):
    """创建拼多多采集账号"""
    pass


class PddAccountUpdate(BaseModel):
    """更新拼多多采集账号"""
    account_name: Optional[str] = Field(None, min_length=1, max_length=64)
    phone: Optional[str] = Field(None, pattern=r"^1\d{10}$")
    notes: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    login_status: Optional[str] = None  # logged_in / expired / error


class PddAccountResponse(PddAccountBase):
    """拼多多账号响应"""
    id: int
    user_id: int
    login_status: str
    storage_state: Optional[str] = None  # Playwright storage state (JSON string)
    last_login_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PddAccountListResponse(BaseModel):
    """账号列表响应"""
    total: int
    page: int
    size: int
    accounts: List[PddAccountResponse]


# ==================== 二维码登录 ====================

class PddQrcodeGenerateRequest(BaseModel):
    """生成二维码请求"""
    account_id: int = Field(..., description="采集账号 ID")


class PddQrcodeGenerateResponse(BaseModel):
    """生成二维码响应"""
    account_id: int
    qrcode_url: str = Field(..., description="二维码图片 URL (data:image/png;base64,...)")
    qrcode_token: str = Field(..., description="二维码唯一标识，用于轮询状态")
    expires_at: datetime = Field(..., description="二维码过期时间")
    message: str = Field(default="请使用拼多多 APP 扫码登录，二维码 3 分钟有效")


class PddQrcodeStatusRequest(BaseModel):
    """查询二维码状态请求"""
    qrcode_token: str = Field(..., description="二维码标识")


class PddQrcodeStatusResponse(BaseModel):
    """二维码状态响应"""
    qrcode_token: str
    status: str = Field(..., description="waiting / scanned / confirmed / expired / error")
    message: str
    account_id: Optional[int] = None
    account_name: Optional[str] = None
    storage_state: Optional[str] = None  # 登录成功后返回 storage state


# ==================== 商品采集 ====================

class PddProductCollectRequest(BaseModel):
    """采集商品请求"""
    account_id: int = Field(..., description="采集账号 ID")
    urls: List[str] = Field(..., min_length=1, max_length=50, description="商品链接列表")
    target_shop_id: int = Field(..., description="目标店铺 ID")


class PddProductCollectResponse(BaseModel):
    """采集商品响应"""
    total: int
    success: int
    failed: int
    results: List[Any]


# ==================== 店铺信息（采集账号视角） ====================

class PddShopInfo(BaseModel):
    """拼多多店铺信息（用于选择采集账号关联的店铺）"""
    mall_id: str
    mall_name: str
    avatar: Optional[str] = None
    is_cross_border: bool = False
    main_category: Optional[str] = None