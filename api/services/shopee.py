"""
Shopee API 服务 — 商品创建/更新/查询/库存管理

使用 Shopee Open Platform API v2
支持：
- 商品创建/更新/删除
- 图片上传（异步）
- 库存管理
- 订单同步
- 评价管理
"""

import hashlib
import hmac
import base64
import logging
import time
from typing import Optional
from datetime import datetime

from api.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class ShopeeClient:
    """Shopee API 客户端"""

    # Shopee API 环境映射
    API_ENV = {
        "shopee_th": {"base_url": "https://api.shopee.com/th", "market_id": 146},
        "shopee_vn": {"base_url": "https://api.shopee.vn", "market_id": 1},
        "shopee_sg": {"base_url": "https://api.shopee.sg", "market_id": 2},
        "shopee_my": {"base_url": "https://api.shopee.com.my", "market_id": 3},
        "shopee_ph": {"base_url": "https://api.shopee.com.ph", "market_id": 6},
        "shopee_ms": {"base_url": "https://api.shopee.com.my", "market_id": 7},
    }

    def __init__(self, shop_id: int, partner_id: str, client_secret: str, marketplace: str = "shopee_th"):
        self.shop_id = shop_id
        self.partner_id = partner_id
        self.client_secret = client_secret
        env = self.API_ENV.get(marketplace, self.API_ENV["shopee_th"])
        self.base_url = env["base_url"]
        self.marketplace = marketplace
        self.market_id = env["market_id"]

    def _sign_request(self, path: str, body: str = "") -> str:
        """
        生成 Shopee API 请求签名

        Signature = Base64(HMAC_SHA256(secret, path + body))
        """
        message = path + body
        signature = hmac.new(
            self.client_secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(signature).decode("utf-8")

    def _build_headers(self, signature: str, timestamp: Optional[int] = None) -> dict:
        """构建请求头"""
        ts = timestamp or int(time.time())
        return {
            "Authorization": f"Bearer {self.client_secret}",
            "Signature": signature,
            "SignAlg": "HMAC_SHA256",
            "Timestamp": str(ts),
            "Content-Type": "application/json",
            "X-Shop-Token": self.client_secret,
            "X-Short-Host": "1",
        }

    def _call_api(self, method: str, path: str, json_data: Optional[dict] = None,
                  params: Optional[dict] = None, timeout: float = 30.0) -> dict:
        """
        同步调用 Shopee API（使用 httpx sync client）
        """
        import httpx

        body_str = str(json_data) if json_data else ""
        signature = self._sign_request(path, body_str)
        headers = self._build_headers(signature)

        url = f"{self.base_url}{path}"

        with httpx.Client(timeout=timeout) as client:
            if method.upper() == "GET":
                resp = client.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                resp = client.post(url, json=json_data, headers=headers)
            elif method.upper() == "PUT":
                resp = client.put(url, json=json_data, headers=headers)
            elif method.upper() == "DELETE":
                resp = client.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            if resp.status_code in (200, 201):
                return resp.json()
            else:
                logger.error(f"Shopee API 错误 [{method} {path}]: {resp.status_code} {resp.text}")
                raise Exception(f"Shopee API 错误 ({resp.status_code}): {resp.text}")

    # ==================== 商品操作 ====================

    def create_product(self, product_data: dict) -> dict:
        """创建 Shopee 商品"""
        path = f"/api/v1/shop/{self.shop_id}/items"
        result = self._call_api("POST", path, json_data=product_data)
        item_id = result.get("item_id", result.get("response", {}).get("item_id", ""))
        logger.info(f"Shopee 商品创建成功: {item_id}")
        return {"item_id": item_id, "status": "success", "shop_id": self.shop_id}

    def update_product(self, item_id: str, product_data: dict) -> dict:
        """更新 Shopee 商品"""
        path = f"/api/v1/shop/{self.shop_id}/item/{item_id}"
        result = self._call_api("PUT", path, json_data=product_data)
        logger.info(f"Shopee 商品更新成功: {item_id}")
        return {"item_id": item_id, "status": "success"}

    def get_product(self, item_id: str) -> dict:
        """获取商品详情"""
        path = f"/api/v1/shop/{self.shop_id}/item/{item_id}"
        result = self._call_api("GET", path)
        logger.info(f"Shopee 商品详情获取成功: {item_id}")
        return result

    def delete_product(self, item_id: str) -> dict:
        """下架/删除商品"""
        path = f"/api/v1/shop/{self.shop_id}/item/{item_id}"
        result = self._call_api("DELETE", path)
        logger.info(f"Shopee 商品下架: {item_id}")
        return {"item_id": item_id, "status": "deleted"}

    def list_products(self, page: int = 1, size: int = 20) -> dict:
        """列出店铺商品"""
        path = f"/api/v1/shop/{self.shop_id}/items"
        params = {"page": page, "limit": size}
        result = self._call_api("GET", path, params=params)
        items = result.get("items", result.get("response", {}).get("items", []))
        total = result.get("total_count", result.get("response", {}).get("total_count", len(items)))
        logger.info(f"Shopee 商品列表获取成功: {len(items)} items")
        return {
            "shop_id": self.shop_id,
            "page": page,
            "size": size,
            "items": items,
            "total": total,
        }

    # ==================== 图片操作 ====================

    def upload_image(self, image_url: str) -> dict:
        """
        上传图片到 Shopee

        返回 image_id，可用于后续商品创建
        """
        path = "/api/v1/item/image"
        result = self._call_api(
            "POST", path,
            json_data={"shop_id": self.shop_id, "image": image_url},
            timeout=60.0,
        )
        image_id = result.get("image_id", result.get("response", {}).get("image_id", ""))
        logger.info(f"Shopee 图片上传成功: {image_id}")
        return {"image_id": image_id, "status": "success", "url": image_url}

    # ==================== 库存操作 ====================

    def update_stock(self, item_id: str, variation_id: str, stock: int) -> dict:
        """更新商品库存"""
        path = f"/api/v1/shop/{self.shop_id}/item/{item_id}/stock"
        result = self._call_api(
            "PUT", path,
            json_data={"variation_id": variation_id, "stock": stock},
        )
        logger.info(f"Shopee 库存更新成功: {item_id} -> {stock}")
        return {"item_id": item_id, "variation_id": variation_id, "stock": stock, "status": "success"}

    def bulk_update_stock(self, updates: list[dict]) -> dict:
        """
        批量更新库存

        updates: [{"item_id": "...", "variation_id": "...", "stock": 100}, ...]
        """
        results = []
        for update in updates:
            try:
                result = self.update_stock(
                    update["item_id"],
                    update["variation_id"],
                    update["stock"],
                )
                results.append({"item_id": update["item_id"], "status": "success", **result})
            except Exception as e:
                results.append({"item_id": update["item_id"], "status": "failed", "error": str(e)})

        success_count = sum(1 for r in results if r["status"] == "success")
        logger.info(f"批量库存更新: {success_count}/{len(results)} 成功")
        return {"results": results, "success_count": success_count, "total": len(updates)}

    # ==================== 订单操作 ====================

    def list_orders(self, status: str = "ALL", page: int = 1, size: int = 20) -> dict:
        """列出店铺订单"""
        path = f"/api/v1/shop/{self.shop_id}/orders"
        params = {"status": status, "page": page, "limit": size}
        result = self._call_api("GET", path, params=params)
        return result

    def update_order_status(self, order_id: str, status: str) -> dict:
        """更新订单状态"""
        path = f"/api/v1/shop/{self.shop_id}/order/{order_id}"
        result = self._call_api("PUT", path, json_data={"status": status})
        logger.info(f"订单状态更新: {order_id} -> {status}")
        return result

    # ==================== 评价操作 ====================

    def list_reviews(self, item_id: str, page: int = 1, size: int = 20) -> dict:
        """列出商品评价"""
        path = f"/api/v1/shop/{self.shop_id}/item/{item_id}/reviews"
        params = {"page": page, "limit": size}
        result = self._call_api("GET", path, params=params)
        return result

    def reply_review(self, review_id: str, reply_text: str) -> dict:
        """回复评价"""
        path = f"/api/v1/shop/{self.shop_id}/review/{review_id}/reply"
        result = self._call_api("POST", path, json_data={"reply": reply_text})
        logger.info(f"评价回复成功: {review_id}")
        return result


# ==================== 工厂函数 ====================

def create_shopee_client(shop_id: int, token: str, marketplace: str = "shopee_th") -> ShopeeClient:
    """
    创建 Shopee API 客户端

    Args:
        shop_id: 店铺 ID
        token: 店铺 OAuth Token（已解密）
        marketplace: 市场标识（shopee_th, shopee_vn, etc.）

    Returns:
        ShopeeClient 实例
    """
    partner_id = settings.SHOPEE_MARKET_ID or str(
        ShopeeClient.API_ENV.get(marketplace, ShopeeClient.API_ENV["shopee_th"])["market_id"]
    )
    client_secret = settings.SECRET_KEY

    return ShopeeClient(
        shop_id=shop_id,
        partner_id=partner_id,
        client_secret=client_secret,
        marketplace=marketplace,
    )


def list_to_shopee(
    product_id: int,
    shop_id: int,
    shop_token: str,
    marketplace: str = "shopee_th",
) -> dict:
    """
    上架商品到 Shopee

    Args:
        product_id: 商品 ID
        shop_id: 店铺 ID
        shop_token: 店铺 Token（已解密）
        marketplace: 市场标识

    Returns:
        上架结果
    """
    client = create_shopee_client(shop_id, shop_token, marketplace)

    product_data = {
        "name": "待翻译标题",
        "description": "待翻译描述",
        "price": 10000,
        "quantity": 100,
        "images": [],
        "variants": [],
    }

    result = client.create_product(product_data)

    return {
        "product_id": product_id,
        "shop_id": shop_id,
        "shopee_item_id": result.get("item_id"),
        "status": "success",
    }
