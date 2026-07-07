"""
测试 Webhook 路由
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from api.main import app


client = TestClient(app)


class TestWebhooks:
    """Webhook 端点测试"""

    def test_order_webhook_invalid_json(self):
        """订单 Webhook 接收无效 JSON"""
        response = client.post(
            "/webhook/shopee/order",
            content=b"not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 400

    def test_order_webhook_missing_signature(self):
        """订单 Webhook 缺少签名"""
        import json
        payload = json.dumps({"type": "ORDER_STATUS_UPDATED", "data": {}}).encode()
        response = client.post(
            "/webhook/shopee/order",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 401

    def test_order_webhook_unknown_event(self):
        """订单 Webhook 未知事件类型"""
        import json
        import hashlib
        import hmac
        from api.routers.webhooks import WEBHOOK_SECRET

        payload = json.dumps({
            "type": "UNKNOWN_EVENT",
            "data": {"order_id": "123"},
        }).encode()

        signature = hmac.new(
            WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        response = client.post(
            "/webhook/shopee/order",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-Shopee-Signature": signature,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "received"

    def test_order_webhook_valid_event(self):
        """订单 Webhook 有效事件（状态变更）"""
        import json
        import hashlib
        import hmac
        from api.routers.webhooks import WEBHOOK_SECRET

        payload = json.dumps({
            "type": "ORDER_STATUS_UPDATED",
            "data": {
                "order_id": "ORD-12345",
                "order_status": "paid",
                "item_id": "ITEM-001",
            },
        }).encode()

        signature = hmac.new(
            WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        with patch('api.routers.webhooks.async_session') as mock_session:
            mock_ctx = MagicMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.execute = AsyncMock(return_value=mock_result)
            mock_ctx.commit = AsyncMock()
            mock_session.return_value = mock_ctx

            response = client.post(
                "/webhook/shopee/order",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Shopee-Signature": signature,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processed"
            assert data["result"]["action"] == "order_status_updated"

    def test_review_webhook_negative_rating(self):
        """评价 Webhook 负面评价"""
        import json
        import hashlib
        import hmac
        from api.routers.webhooks import WEBHOOK_SECRET

        payload = json.dumps({
            "type": "PRODUCT_REVIEW",
            "data": {
                "review_id": "REV-001",
                "rating": 1,
                "product_id": 123,
            },
        }).encode()

        signature = hmac.new(
            WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        response = client.post(
            "/webhook/shopee/review",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-Shopee-Signature": signature,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["result"]["compensation"] is True

    def test_review_webhook_positive_rating(self):
        """评价 Webhook 正面评价"""
        import json
        import hashlib
        import hmac
        from api.routers.webhooks import WEBHOOK_SECRET

        payload = json.dumps({
            "type": "PRODUCT_REVIEW",
            "data": {
                "review_id": "REV-002",
                "rating": 5,
                "product_id": 123,
            },
        }).encode()

        signature = hmac.new(
            WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        response = client.post(
            "/webhook/shopee/review",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-Shopee-Signature": signature,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["result"]["compensation"] is False

    def test_inventory_webhook_low_stock(self):
        """库存 Webhook 低库存预警"""
        import json
        import hashlib
        import hmac
        from api.routers.webhooks import WEBHOOK_SECRET

        payload = json.dumps({
            "type": "INVENTORY_ALERT",
            "data": {
                "item_id": "ITEM-001",
                "stock": 5,
                "alert_threshold": 10,
            },
        }).encode()

        signature = hmac.new(
            WEBHOOK_SECRET.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        with patch('api.routers.webhooks.async_session') as mock_session:
            mock_ctx = MagicMock()
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.execute = AsyncMock(return_value=mock_result)
            mock_ctx.commit = AsyncMock()
            mock_session.return_value = mock_ctx

            response = client.post(
                "/webhook/shopee/inventory",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Shopee-Signature": signature,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["result"]["below_threshold"] is True

    def test_callback_url_config(self):
        """获取回调 URL 配置"""
        response = client.get("/webhook/shopee/callback-url")
        assert response.status_code == 200
        data = response.json()
        assert "callback_url" in data
        assert "events" in data
        assert "HMAC-SHA256" in data["signature_method"]
