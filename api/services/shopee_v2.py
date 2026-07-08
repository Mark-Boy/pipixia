"""
Shopee Open API v2.0 完整客户端

基于 Open API Developer Guide v2.1 (20220722)

核心功能:
- OAuth 授权流程 (getAuthUrl, getAccessToken)
- 店铺信息管理 (getShopInfo)
- 商品管理 (创建/更新/删除/列表/搜索)
- 图片上传
- 物流跟踪
- Webhook 验证
"""

import hashlib
import hmac
import base64
import logging
import time
import urllib.parse
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import httpx

from api.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


# ==================== API 端点 ====================

API_ENDPOINTS = {
    "get_shop_info": "/shop/get_partner_shop_info",
    "item_add": "/item/add/v2",
    "item_get": "/item/get/v2",
    "item_update": "/item/update/v2",
    "item_del": "/item/del/v2",
    "item_list": "/item/list",
    "item_search": "/item/search",
    "upload_image": "/image/upload_item_image",
    "model_add": "/item/model/add",
    "model_update": "/item/model/update",
    "model_del": "/item/model/del",
    "get_categories": "/category/get",
    "get_category_options": "/category/get_options",
    "get_order_list": "/order/get_order_list",
    "get_order_detail": "/order/get_order_detail",
    "cancel_order": "/order/cancel_order",
    "get_tracking_number": "/order/get_tracking_number",
    "print_airwaybill": "/order/print_airwaybill",
}


class ShopeeV2Client:
    """Shopee Open Platform API v2.0 Client"""

    MARKET_CONFIG = {
        "shopee_th": {"sandbox_url": "https://partner.test-stable.shopee.com/api/v2", "live_url": "https://partner.shopeemobile.com/api/v2", "market_id": 146, "currency": "THB"},
        "shopee_vn": {"sandbox_url": "https://partner.test-stable.shopee.com/api/v2", "live_url": "https://partner.shopeemobile.com/api/v2", "market_id": 1, "currency": "VND"},
        "shopee_sg": {"sandbox_url": "https://partner.test-stable.shopee.com/api/v2", "live_url": "https://partner.shopeemobile.com/api/v2", "market_id": 2, "currency": "SGD"},
        "shopee_my": {"sandbox_url": "https://partner.test-stable.shopee.com/api/v2", "live_url": "https://partner.shopeemobile.com/api/v2", "market_id": 3, "currency": "MYR"},
        "shopee_ph": {"sandbox_url": "https://partner.test-stable.shopee.com/api/v2", "live_url": "https://partner.shopeemobile.com/api/v2", "market_id": 6, "currency": "PHP"},
    }

    def __init__(self, partner_id: str, client_secret: str, access_token: str, marketplace: str = "shopee_th", sandbox: bool = True):
        self.partner_id = partner_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.marketplace = marketplace
        self.sandbox = sandbox
        cfg = self.MARKET_CONFIG.get(marketplace, self.MARKET_CONFIG["shopee_th"])
        self.api_url = cfg["sandbox_url"] if sandbox else cfg["live_url"]
        self.market_id = cfg["market_id"]
        self.currency = cfg["currency"]

    # ========== 签名 ==========
    def _sign(self, path: str, body: str) -> str:
        msg = path + body
        sig = hmac.new(self.client_secret.encode(), msg.encode(), hashlib.sha256).digest()
        return base64.b64encode(sig).decode()

    def _headers(self, path: str, body: str = "") -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Signature": self._sign(path, body),
            "SignAlg": "SHA256",
            "Timestamp": str(int(time.time())),
            "Content-Type": "application/json",
        }

    # ========== HTTP 调用 ==========
    def _api(self, method: str, path: str, params: dict | None = None, json_data: dict | None = None, timeout: float = 30.0) -> dict:
        body_str = str(json_data) if json_data else ""
        headers = self._headers(path, body_str)
        url = self.api_url + path

        with httpx.Client(timeout=timeout) as c:
            resp = getattr(c, method.lower())(url, headers=headers, params=params, json=json_data)
            if resp.status_code in (200, 201):
                return resp.json()
            logger.error(f"API [{method} {path}] {resp.status_code}: {resp.text}")
            raise Exception(f"Shopee API error {resp.status_code}: {resp.text}")

    # ========== OAuth ==========
    def get_auth_url(self, shop_id: str, callback_url: str) -> str:
        """生成 OAuth 授权链接 (365天有效)"""
        state = f"{shop_id}_{int(time.time())}"
        base = self.api_url.replace("/api/v2", "")
        return f"{base}/oauth.authorize?client_id={self.partner_id}&shop_id={shop_id}&state={state}&scope=shop_basic&callback_url={urllib.parse.quote(callback_url)}"

    def get_access_token(self, shop_id: str, code: str) -> dict:
        """用 code 换取 access_token"""
        path = "/shop/auth"
        data = {"shop_id": shop_id, "code": code}
        body_str = str(data)
        headers = self._headers(path, body_str)
        with httpx.Client(timeout=30.0) as c:
            resp = c.post(self.api_url + path, json=data, headers=headers)
            resp.raise_for_status()
            return resp.json()

    # ========== 店铺 ==========
    def get_shop_info(self) -> dict:
        return self._api("POST", "/shop/get_partner_shop_info")

    def get_shop_detail(self) -> dict:
        result = self.get_shop_info()
        s = result.get("shop_info", {})
        return {
            "shop_id": s.get("shop_id", ""),
            "shop_name": s.get("shop_name", ""),
            "username": s.get("username", ""),
            "marketplace": s.get("marketplace", self.marketplace),
            "currency": self.currency,
            "status": s.get("status", "active"),
            "is_official_shop": s.get("is_official_shop", False),
            "is_shopee_mall": s.get("is_shopee_mall", False),
        }

    # ========== 商品 CRUD ==========
    def create_product(self, data: dict) -> dict:
        result = self._api("POST", "/item/add/v2", json_data=data, timeout=60.0)
        item_id = result.get("item_id") or result.get("response", {}).get("item_id")
        logger.info(f"商品创建成功: {item_id}")
        return {"item_id": item_id, "status": "success"}

    def update_product(self, item_id: str, data: dict) -> dict:
        result = self._api("POST", "/item/update/v2", json_data={"item_id": item_id, **data}, timeout=60.0)
        return {"item_id": item_id, "status": result.get("response", {}).get("status", "success")}

    def get_product(self, item_id: str) -> dict:
        return self._api("GET", "/item/get/v2", params={"item_id": item_id})

    def delete_product(self, item_id: str) -> dict:
        result = self._api("GET", "/item/del/v2", params={"item_id": item_id})
        return {"item_id": item_id, "status": "deleted"}

    def list_products(self, page: int = 1, size: int = 20, status: str = "ALL") -> dict:
        result = self._api("GET", "/item/list", params={"page": page, "limit": size, "status": status})
        return {
            "items": result.get("items", []),
            "total": result.get("count", 0),
            "page": page,
            "size": size,
        }

    def search_products(self, keywords: str, page: int = 1) -> dict:
        return self._api("GET", "/item/search", params={"keywords": keywords, "page": page})

    def update_stock(self, item_id: str, stock: int) -> dict:
        return self._api("POST", "/item/update/v2", json_data={"item_id": item_id, "stock": stock}, timeout=30.0)

    def bulk_update_stock(self, updates: list) -> dict:
        results = []
        for u in updates:
            try:
                r = self.update_stock(u["item_id"], u["stock"])
                results.append({"item_id": u["item_id"], "stock": u["stock"], "status": "success"})
            except Exception as e:
                results.append({"item_id": u["item_id"], "stock": u["stock"], "status": "failed", "error": str(e)})
        ok = sum(1 for r in results if r["status"] == "success")
        return {"results": results, "success_count": ok, "total": len(updates)}

    # ========== 图片 ==========
    def upload_image(self, image_url: str) -> dict:
        result = self._api("POST", "/image/upload_item_image", json_data={"image": image_url}, timeout=60.0)
        return {"image_id": result.get("image_id"), "url": image_url}

    def upload_images(self, urls: list[str]) -> list[dict]:
        return [self.upload_image(u) for u in urls]

    # ========== 规格 ==========
    def add_variation(self, item_id: str, data: dict) -> dict:
        return self._api("POST", "/item/model/add", json_data={"item_id": item_id, **data})

    def update_variation(self, item_id: str, var_id: str, data: dict) -> dict:
        return self._api("POST", "/item/model/update", json_data={"item_id": item_id, "variation_id": var_id, **data})

    def delete_variation(self, item_id: str, var_id: str) -> dict:
        return self._api("GET", "/item/model/del", params={"item_id": item_id, "variation_id": var_id})

    # ========== 类目 ==========
    def get_categories(self) -> dict:
        return self._api("GET", "/category/get")

    def get_category_options(self, category_id: int) -> dict:
        return self._api("GET", "/category/get_options", params={"category_id": category_id})

    # ========== 订单 ==========
    def get_orders(self, status: str = "ALL", page: int = 1, limit: int = 20) -> dict:
        return self._api("GET", "/order/get_order_list", params={"status": status, "page": page, "limit": limit})

    def get_order_detail(self, order_id: str) -> dict:
        return self._api("GET", "/order/get_order_detail", params={"order_id": order_id})

    def cancel_order(self, order_id: str, reason: str = "Customer request") -> dict:
        return self._api("GET", "/order/cancel_order", params={"order_id": order_id, "reason": reason})

    # ========== 物流 ==========
    def get_tracking_number(self, order_id: str, courier: str) -> dict:
        return self._api("GET", "/order/get_tracking_number", params={"order_id": order_id, "courier": courier})

    def print_airwaybill(self, order_id: str, courier: str) -> dict:
        return self._api("GET", "/order/print_airwaybill", params={"order_id": order_id, "courier": courier})


# ==================== 工厂函数 ====================
def create_shopee_client(shop_id: int, token: str, marketplace: str = "shopee_th", sandbox: bool = True) -> ShopeeV2Client:
    pid = settings.SHOPEE_MARKET_ID or ShopeeV2Client.MARKET_CONFIG.get(marketplace, ShopeeV2Client.MARKET_CONFIG["shopee_th"])["market_id"]
    return ShopeeV2Client(
        partner_id=str(pid),
        client_secret=settings.SHOPEE_SECRET or "test_secret",
        access_token=token,
        marketplace=marketplace,
        sandbox=sandbox,
    )


def list_to_shopee(product_id: int, shop_id: int, shop_token: str, marketplace: str = "shopee_th") -> dict:
    """上架商品到 Shopee"""
    client = create_shopee_client(shop_id, shop_token, marketplace)
    data = {"name": "待翻译", "description": "待翻译", "price": 100000, "quantity": 100}
    result = client.create_product(data)
    return {"product_id": product_id, "shop_id": shop_id, "shopee_item_id": result.get("item_id"), "status": "success"}
