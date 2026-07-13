"""
Pydantic Schema 包
"""

from api.schemas.user import UserCreate, UserLogin, UserResponse, Token
from api.schemas.product import ProductCreate, ProductResponse
from api.schemas.shop import ShopCreate, ShopUpdate, ShopResponse, ShopTokenResponse
from api.schemas.audit import AuditRequest, AuditResponse
from api.schemas.pdd_account import (
    PddAccountCreate,
    PddAccountUpdate,
    PddAccountResponse,
    PddAccountListResponse,
    PddQrcodeGenerateRequest,
    PddQrcodeGenerateResponse,
    PddQrcodeStatusResponse,
    PddProductCollectRequest,
    PddProductCollectResponse,
    PddShopInfo,
)

__all__ = [
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "Token",
    "ProductCreate",
    "ProductUpdate",
    "ProductResponse",
    "ShopCreate",
    "ShopUpdate",
    "ShopResponse",
    "ShopTokenResponse",
    "AuditRequest",
    "AuditResponse",
    "PddAccountCreate",
    "PddAccountUpdate",
    "PddAccountResponse",
    "PddAccountListResponse",
    "PddQrcodeGenerateRequest",
    "PddQrcodeGenerateResponse",
    "PddQrcodeStatusResponse",
    "PddProductCollectRequest",
    "PddProductCollectResponse",
    "PddShopInfo",
]
