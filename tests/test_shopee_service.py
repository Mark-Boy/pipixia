"""
Shopee API 服务测试 — URL 签名、环境映射
"""

import pytest
from api.services.shopee import ShopeeClient, create_shopee_client


class TestShopeeClientInit:
    """ShopeeClient 初始化测试"""

    def test_default_marketplace(self):
        client = ShopeeClient(
            shop_id=1,
            partner_id="test_partner",
            client_secret="test_secret",
        )
        assert client.marketplace == "shopee_th"
        assert client.market_id == 146
        assert "shopee.com" in client.base_url

    def test_thailand_marketplace(self):
        client = ShopeeClient(1, "p", "s", "shopee_th")
        assert client.marketplace == "shopee_th"
        assert client.market_id == 146

    def test_vietnam_marketplace(self):
        client = ShopeeClient(1, "p", "s", "shopee_vn")
        assert client.marketplace == "shopee_vn"
        assert client.market_id == 1

    def test_singapore_marketplace(self):
        client = ShopeeClient(1, "p", "s", "shopee_sg")
        assert client.marketplace == "shopee_sg"
        assert client.market_id == 2

    def test_all_marketplaces(self):
        """验证所有市场配置"""
        for mp in ["shopee_th", "shopee_vn", "shopee_sg", "shopee_my", "shopee_ph", "shopee_ms"]:
            client = ShopeeClient(1, "p", "s", mp)
            assert client.marketplace == mp
            assert client.market_id > 0
            assert client.base_url.startswith("https://")


class TestRequestSigning:
    """请求签名测试"""

    def test_sign_request_generates_signature(self):
        client = ShopeeClient(1, "p", "test_secret_123")
        sig = client._sign_request("/api/v1/items", "{}")
        assert sig is not None
        assert isinstance(sig, str)
        assert len(sig) > 0

    def test_signature_deterministic(self):
        """相同输入产生相同签名"""
        client = ShopeeClient(1, "p", "test_secret_123")
        sig1 = client._sign_request("/api/v1/items", '{"name":"test"}')
        sig2 = client._sign_request("/api/v1/items", '{"name":"test"}')
        assert sig1 == sig2

    def test_signature_different_inputs(self):
        """不同输入产生不同签名"""
        client = ShopeeClient(1, "p", "test_secret_123")
        sig1 = client._sign_request("/api/v1/items", '{"name":"test1"}')
        sig2 = client._sign_request("/api/v1/items", '{"name":"test2"}')
        assert sig1 != sig2

    def test_build_headers(self):
        client = ShopeeClient(1, "p", "test_secret")
        sig = client._sign_request("/test", "{}")
        headers = client._build_headers(sig)
        assert "Authorization" in headers
        assert "Signature" in headers
        assert "SignAlg" in headers
        assert headers["SignAlg"] == "HMAC_SHA256"
        assert "Timestamp" in headers
        assert "X-Shop-Token" in headers


class TestCreateShopeeClient:
    """工厂函数测试"""

    def test_create_client(self):
        client = create_shopee_client(
            shop_id=1,
            token="test_token",
            marketplace="shopee_th",
        )
        assert isinstance(client, ShopeeClient)
        assert client.shop_id == 1

    def test_create_client_default_marketplace(self):
        client = create_shopee_client(shop_id=1, token="test_token")
        assert isinstance(client, ShopeeClient)
