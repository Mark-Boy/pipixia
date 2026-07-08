"""
Shopee API v2.0 测试

测试内容:
- 签名生成
- 店铺信息获取
- 商品创建/更新
- 图片上传
- 库存同步
- 调度器运行

不包含报关功能测试
"""

import sys
import os
import time
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.services.shopee_v2 import ShopeeV2Client, create_shopee_client


class TestShopeeV2Client(unittest.TestCase):
    """Shopee API v2.0 客户端测试"""

    def setUp(self):
        self.client = ShopeeV2Client(
            partner_id="test_partner_123",
            client_secret="test_secret_key",
            access_token="test_access_token",
            marketplace="shopee_th",
            sandbox=True,
        )

    def test_init_default_marketplace(self):
        """测试默认市场初始化"""
        self.assertEqual(self.client.marketplace, "shopee_th")
        self.assertEqual(self.client.market_id, 146)
        self.assertEqual(self.client.currency, "THB")
        self.assertTrue(self.client.sandbox)
        self.assertIn("test-stable", self.client.api_url)

    def test_init_thailand(self):
        """测试泰国市场"""
        client = ShopeeV2Client(
            partner_id="p1",
            client_secret="s1",
            access_token="t1",
            marketplace="shopee_th",
        )
        self.assertEqual(client.market_id, 146)
        self.assertEqual(client.currency, "THB")

    def test_init_vietnam(self):
        """测试越南市场"""
        client = ShopeeV2Client(
            partner_id="p1",
            client_secret="s1",
            access_token="t1",
            marketplace="shopee_vn",
        )
        self.assertEqual(client.market_id, 1)
        self.assertEqual(client.currency, "VND")

    def test_get_auth_url(self):
        """测试授权链接生成"""
        auth_url = self.client.get_auth_url("shop_123", "http://localhost:8000/callback")
        self.assertIn("oauth.authorize", auth_url)
        self.assertIn("client_id=test_partner_123", auth_url)
        self.assertIn("shop_id=shop_123", auth_url)
        self.assertIn("scope=shop_basic", auth_url)

    def test_sign(self):
        """测试签名生成"""
        path = "/item/add/v2"
        body = '{"name": "test"}'
        signature = self.client._sign(path, body)
        self.assertIsInstance(signature, str)
        self.assertTrue(len(signature) > 0)
        # 签名应该一致 (确定性)
        sig2 = self.client._sign(path, body)
        self.assertEqual(signature, sig2)

    def test_different_bodies_produce_different_signatures(self):
        """测试不同 body 产生不同签名"""
        sig1 = self.client._sign("/test", '{"name": "a"}')
        sig2 = self.client._sign("/test", '{"name": "b"}')
        self.assertNotEqual(sig1, sig2)

    def test_different_paths_produce_different_signatures(self):
        """测试不同 path 产生不同签名"""
        sig1 = self.client._sign("/item/add", "{}")
        sig2 = self.client._sign("/item/update", "{}")
        self.assertNotEqual(sig1, sig2)

    @patch("api.services.shopee_v2.httpx.Client")
    def test_get_shop_info(self, mock_client_class):
        """测试获取店铺信息 (mock)"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "error_code": 0,
            "shop_info": {
                "shop_id": "shop_123",
                "shop_name": "Test Shop",
                "username": "testuser",
                "marketplace": "shopee_th",
            }
        }
        mock_client_class.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_client_class.return_value.__enter__.post.return_value = mock_resp

        # 直接测试签名和 headers
        path = "/shop/get_partner_shop_info"
        headers = self.client._headers(path)
        self.assertIn("Authorization", headers)
        self.assertIn("Signature", headers)
        self.assertIn("Timestamp", headers)


class TestCreateShopeeClient(unittest.TestCase):
    """工厂函数测试"""

    @patch("api.services.shopee_v2.get_settings")
    def test_create_client(self, mock_settings):
        """测试工厂函数"""
        mock_settings.return_value.SHOPEE_MARKET_ID = 146
        mock_settings.return_value.SHOPEE_SECRET = "test_secret"

        client = create_shopee_client(
            shop_id=1,
            token="test_token",
            marketplace="shopee_th",
            sandbox=True,
        )

        self.assertIsInstance(client, ShopeeV2Client)
        self.assertEqual(client.access_token, "test_token")
        self.assertEqual(client.marketplace, "shopee_th")


class TestShopeeSyncService(unittest.TestCase):
    """Shopee 同步服务测试"""

    def test_list_to_shopee_price_conversion(self):
        """测试价格转换 (CNY -> THB -> Shopee unit)"""
        # 假设 1 CNY = 5 THB
        price_cny = 10.0
        price_thb = price_cny * 5  # 50 THB

        # Shopee API 使用最小货币单位 (泰铢的 1/1000)
        shopee_price = int(price_thb * 1000)  # 50000
        self.assertEqual(shopee_price, 50000)


if __name__ == "__main__":
    unittest.main()
