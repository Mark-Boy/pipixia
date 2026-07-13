"""
测试 worker Celery 任务 — 重点是 S07 图片翻译任务和 batch 任务链路

策略:
- 用 task_always_eager=True 同步执行
- 对图片翻译核心逻辑全部 mock OCR/合成/上传, 只验证 task 调用约定与重试降级
- 对 webhook_handler_async 跑真实异步 DB handler 但 mock 库存 listing 查询
- 对 batch_translate 验证速率限制 + 失败统计
"""

import os
import sys
import json
import asyncio

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# 确保 worker 在 PYTHONPATH 中（worker 内 import celery_app 是相对 /app）
WORKER_DIR = os.path.join(os.path.dirname(__file__), "..", "worker")
sys.path.insert(0, os.path.abspath(WORKER_DIR))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from worker import tasks as T  # noqa: E402


class TestProcessImageTask:
    def test_process_image_success(self):
        """process_image 整体成功路径。"""
        fake_result = {
            "source_url": "http://x/y.jpg",
            "result_url": "http://oss/translated/img_000.jpg",
            "ocr_blocks": 2,
            "translated_blocks": 2,
            "status": "completed",
        }
        with patch("api.services.image_translate.translate_image",
                   return_value=fake_result) as fn:
            res = T.process_image.delay("http://x/y.jpg", 5, 0).get(timeout=5)
        # Celery task 的返回应是函数结果 enriched
        assert res["status"] == "completed"
        assert res["product_id"] == 5
        assert res["image_index"] == 0
        assert res["ocr_blocks"] == 2
        fn.assert_called_once_with(image_url="http://x/y.jpg", product_id=5, image_index=0)

    def test_process_image_no_text_skipped(self):
        """OCR 无文字返回 skipped。"""
        with patch("api.services.image_translate.translate_image",
                   return_value={
                       "source_url": "http://x/y.jpg",
                       "result_url": "http://x/y.jpg",
                       "ocr_blocks": 0,
                       "translated_blocks": 0,
                       "status": "skipped",
                   }):
            res = T.process_image.delay("http://x/y.jpg", 7, 1).get(timeout=5)
        assert res["status"] == "skipped"
        assert res["result_url"] == "http://x/y.jpg"

    def test_process_image_falls_back_to_source_on_error(self):
        """translate_image 抛异常且重试耗尽时降级返回原图 (status=failed)。"""
        with patch("api.services.image_translate.translate_image",
                   side_effect=RuntimeError("boom")):
            # force_retries 重试计数器达到上限
            T.process_image.push_request(retries=T.process_image.max_retries)
            try:
                res = T.process_image.delay("http://x/y.jpg", 9, 0).get(timeout=10)
            finally:
                T.process_image.push_request()
        assert res["status"] == "failed"
        assert res["result_url"] == "http://x/y.jpg"
        assert "boom" in res["error"]


class TestBatchProcessImages:
    def test_batch_collects_per_image_results(self):
        """批量翻译 N 张图, 每张单进程失败不影响其他。"""
        urls = ["http://x/1.jpg", "http://x/2.jpg", "http://x/3.jpg"]
        seq = [
            {"source_url": urls[0], "result_url": "oss://1", "ocr_blocks": 2,
             "translated_blocks": 2, "status": "completed"},
            {"source_url": urls[1], "result_url": urls[1], "ocr_blocks": 0,
             "translated_blocks": 0, "status": "skipped"},
            {"source_url": urls[2], "result_url": urls[2], "ocr_blocks": 0,
             "translated_blocks": 0, "status": "failed"},
        ]
        with patch("api.services.image_translate.translate_image", side_effect=seq):
            res = T.batch_process_images.delay(urls, product_id=1).get(timeout=10)
        assert res["total"] == 3
        assert res["success"] == 2   # completed + skipped 都算 success
        assert res["failed"] == 1
        assert len(res["results"]) == 3


class TestBatchTranslate:
    def test_batch_translate_collects_results(self):
        """批量文本翻译统计成功失败各计数正确。"""
        def fake_workflow(product_id):
            if product_id == 2:
                raise RuntimeError("api error")
            return {"risk_status": "pass", "profit_margin": 15.0,
                    "title_th": "t", "desc_th": "d"}

        with patch("api.langgraph.graph.run_translation_workflow",
                   side_effect=fake_workflow):
            res = T.batch_translate.delay([1, 2, 3]).get(timeout=10)
        assert res["total"] == 3
        assert res["success"] == 2
        assert res["failed"] == 1
        assert res["details"][0]["status"] == "success"
        assert res["details"][1]["status"] == "failed"
        assert "api error" in res["details"][1]["error"]

    def test_batch_translate_task_alias_delegates(self):
        """batch_translate_task 是 batch_translate 的别名入口。"""
        with patch("api.langgraph.graph.run_translation_workflow",
                   return_value={"risk_status": "pass"}):
            res = T.batch_translate_task.delay([42]).get(timeout=10)
        assert res["total"] == 1
        assert res["success"] == 1
        assert res["details"][0]["product_id"] == 42


class TestWebhookHandlerAsync:
    def test_unknown_event_ignored(self):
        """未知事件类型被记录后忽略。"""
        res = asyncio.get_event_loop().run_until_complete(
            T.webhook_handler_async("bogus_event", {"foo": "bar"})
        )
        assert res["status"] == "processed"
        assert res["result"]["action"] == "ignored"

    def test_order_cancelled_releases_stock(self):
        """order_cancelled handler 应对每个 item 释放库存 + 置 cancelled。"""
        listing = MagicMock()
        listing.stock = 5
        listing.id = 1
        executed_result = MagicMock()
        executed_result.scalar_one_or_none.return_value = listing

        class FakeDB:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def execute(self, *args, **kwargs):
                return executed_result

            async def commit(self):
                pass

        with patch("api.database.async_session", lambda: FakeDB()):
            res = asyncio.get_event_loop().run_until_complete(
                T.webhook_handler_async("order_cancelled", {
                    "order_id": "ORD-1",
                    "cancel_reason": "user",
                    "order_items": [
                        {"item_id": "IT-1", "quantity": 3},
                        {"item_id": "IT-2", "quantity": 2},
                    ],
                })
            )
        assert res["status"] == "processed"
        assert res["result"]["order_id"] == "ORD-1"
        assert res["result"]["total_released"] == 5
        assert listing.shopee_status == "cancelled"

    def test_review_added_negative_rating_triggers_compensation(self):
        """差评触发补偿建议。"""
        res = asyncio.get_event_loop().run_until_complete(
            T.webhook_handler_async("review_added", {
                "review_id": "R-1",
                "rating": 1,
                "comment": "bad",
            })
        )
        assert res["status"] == "processed"
        assert res["result"]["action"] == "negative_review"
        assert res["result"]["compensation"] is True
        assert len(res["result"]["suggested_actions"]) > 0

    def test_review_added_positive_rating(self):
        """好评统计 compensation=False。"""
        res = asyncio.get_event_loop().run_until_complete(
            T.webhook_handler_async("review_added", {
                "review_id": "R-2",
                "rating": 5,
            })
        )
        assert res["result"]["action"] == "positive_review"
        assert res["result"]["compensation"] is False


class TestListingProduct:
    def test_listing_product_returns_shopee_item_id(self):
        """上架任务返回模拟 shopee_item_id (TODO 真实接入)。"""
        res = T.listing_product.delay(99).get(timeout=10)
        assert res["status"] == "success"
        assert res["product_id"] == 99
        assert res["shopee_item_id"].startswith("shopee-99-")
