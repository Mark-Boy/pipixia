"""
Shopee API 服务 — 商品创建/更新/查询

使用 Shopee Open Platform API v2
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

    def __init__(self, shop_id: int, partner_id: str, client_secret: str):
        self.shop_id = shop_id
        self.partner_id = partner_id
        self.client_secret = client_secret
        self.base_url = "https://api.shopee.com/theme"  # 泰国站
        self.market_id = settings.SHOPEE_MARKET_ID  # 146 = Thailand

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

    def create_product(self, product_data: dict) -> dict:
        """
        创建 Shopee 商品
        
        Args:
            product_data: 商品数据
                {
                    "name": "泰语标题",
                    "description": "泰语描述",
                    "price": 10000,  # 单位：分（10000 = 100.00 THB）
                    "quantity": 100,
                    "images": ["url1", "url2"],
                    "variants": [...],
                    "category_id": 123,
                }
                
        Returns:
            {item_id, status}
        """
        path = f"/api/v1/shop/{self.shop_id}/items"
        body = str(product_data)
        signature = self._sign_request(path, body)

        headers = {
            "Signature": signature,
            "SignAlg": "HMAC_SHA256",
            "Timestamp": str(int(time.time())),
            "Content-Type": "application/json",
        }

        # TODO: 实际调用 Shopee API
        # import httpx
        # async with httpx.AsyncClient() as client:
        #     response = await client.post(
        #         f"{self.base_url}{path}",
        #         json=product_data,
        #         headers=headers,
        #     )
        #     return response.json()

        logger.info(f"模拟创建商品: {product_data.get('name', '')}")
        return {
            "item_id": f"shopee-{self.shop_id}-{int(time.time())}",
            "status": "success",
            "shop_id": self.shop_id,
        }

    def update_product(self, item_id: str, product_data: dict) -> dict:
        """更新 Shopee 商品"""
        path = f"/api/v1/shop/{self.shop_id}/item/{item_id}"
        body = str(product_data)
        signature = self._sign_request(path, body)

        headers = {
            "Signature": signature,
            "SignAlg": "HMAC_SHA256",
            "Timestamp": str(int(time.time())),
            "Content-Type": "application/json",
        }

        # TODO: 实际调用 Shopee API
        logger.info(f"模拟更新商品: {item_id}")
        return {
            "item_id": item_id,
            "status": "success",
        }

    def upload_image(self, image_url: str) -> dict:
        """
        上传图片到 Shopee（异步模式）
        
        返回 image_id，可用于后续商品创建
        """
        path = "/api/v1/item/image"
        body = f'{{"shop_id": {self.shop_id}, "image": "{image_url}"}}'
        signature = self._sign_request(path, body)

        headers = {
            "Signature": signature,
            "SignAlg": "HMAC_SHA256",
            "Timestamp": str(int(time.time())),
            "Content-Type": "application/json",
        }

        # TODO: 实际调用 Shopee 图片上传 API
        logger.info(f"模拟上传图片: {image_url}")
        return {
            "image_id": f"img-{self.shop_id}-{int(time.time())}",
            "status": "success",
            "url": image_url,
        }

    def get_product(self, item_id: str) -> dict:
        """获取商品详情"""
        path = f"/api/v1/shop/{self.shop_id}/item/{item_id}"
        body = ""
        signature = self._sign_request(path, body)

        headers = {
            "Signature": signature,
            "SignAlg": "HMAC_SHA256",
            "Timestamp": str(int(time.time())),
        }

        # TODO: 实际调用 Shopee API
        logger.info(f"模拟获取商品详情: {item_id}")
        return {
            "item_id": item_id,
            "shop_id": self.shop_id,
            "status": "active",
        }

    def update_stock(self, item_id: str, variation_id: str, stock: int) -> dict:
        """更新商品库存"""
        path = f"/api/v1/shop/{self.shop_id}/item/{item_id}/stock"
        body = f'{{"variation_id": "{variation_id}", "stock": {stock}}}'
        signature = self._sign_request(path, body)

        headers = {
            "Signature": signature,
            "SignAlg": "HMAC_SHA256",
            "Timestamp": str(int(time.time())),
            "Content-Type": "application/json",
        }

        # TODO: 实际调用 Shopee API
        logger.info(f"模拟更新库存: {item_id} -> {stock}")
        return {
            "item_id": item_id,
            "variation_id": variation_id,
            "stock": stock,
            "status": "success",
        }

    def list_products(self, page: int = 1, size: int = 20) -> dict:
        """列出店铺商品"""
        path = f"/api/v1/shop/{self.shop_id}/items"
        body = f'?page={page}&size={size}'
        signature = self._sign_request(path, body)

        headers = {
            "Signature": signature,
            "SignAlg": "HMAC_SHA256",
            "Timestamp": str(int(time.time())),
        }

        # TODO: 实际调用 Shopee API
        logger.info(f"模拟列出商品: page={page}, size={size}")
        return {
            "shop_id": self.shop_id,
            "page": page,
            "size": size,
            "items": [],
            "total": 0,
        }


def create_shopee_client(shop_id: int, token: str) -> ShopeeClient:
    """
    创建 Shopee API 客户端
    
    Args:
        shop_id: 店铺 ID
        token: 店铺 OAuth Token（已解密）
        
    Returns:
        ShopeeClient 实例
    """
    # 从配置获取 Partner ID 和 Client Secret
    partner_id = settings.SHOPEE_MARKET_ID  # 简化：使用 market_id 作为 partner_id
    client_secret = settings.SECRET_KEY  # 生产环境应从 Vault 读取

    return ShopeeClient(
        shop_id=shop_id,
        partner_id=partner_id,
        client_secret=client_secret,
    )


def list_to_shopee(
    product_id: int,
    shop_id: int,
    shop_token: str,
) -> dict:
    """
    上架商品到 Shopee
    
    Args:
        product_id: 商品 ID
        shop_id: 店铺 ID
        shop_token: 店铺 Token（已解密）
        
    Returns:
        上架结果
    """
    # 创建 Shopee 客户端
    client = create_shopee_client(shop_id, shop_token)

    # 构建商品数据
    product_data = {
        "name": "待翻译标题",  # 应由翻译服务填充
        "description": "待翻译描述",
        "price": 10000,  # 默认 100 THB（单位：分）
        "quantity": 100,
        "images": [],
        "variants": [],
    }

    # 调用 Shopee API 创建商品
    result = client.create_product(product_data)

    return {
        "product_id": product_id,
        "shop_id": shop_id,
        "shopee_item_id": result.get("item_id"),
        "status": "success",
    }
