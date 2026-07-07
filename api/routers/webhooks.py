"""
Webhook 路由 — Shopee 事件接收与处理

支持的事件类型:
- ORDER_STATUS_UPDATED: 订单状态变更
- ORDER_CANCELLED: 订单取消
- NEW_MESSAGE: 新消息
- PRODUCT_REVIEW: 商品评价
- INVENTORY_ALERT: 库存预警
"""

import hashlib
import hmac
import logging

from fastapi import APIRouter, Request, HTTPException

from api.database import async_session
from api.models.listing import Listing
from api.models.shop import Shop

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Webhooks"])

# Webhook 签名验证 Key（生产环境应从环境变量读取）
WEBHOOK_SECRET = "pipixia-webhook-secret"


def _verify_signature(body_bytes: bytes, signature: str) -> bool:
    """验证 Webhook 签名"""
    expected = hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        body_bytes,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


# ==================== 订单事件处理 ====================

async def _handle_order_status_updated(data: dict) -> dict:
    """处理订单状态变更事件"""
    order_id = data.get("order_id", "unknown")
    order_status = data.get("order_status", "")
    shopee_item_id = data.get("item_id") or data.get("shopee_item_id")

    logger.info(f"📦 订单状态变更: order_id={order_id}, status={order_status}")

    # 更新本地 listing 状态
    async with async_session() as db:
        if shopee_item_id:
            result = await db.execute(
                Listing.__table__.select().where(Listing.shopee_item_id == shopee_item_id)
            )
            listing = result.scalar_one_or_none()
            if listing:
                listing.shopee_status = order_status
                await db.commit()
                logger.info(f"  ✅ Listing #{listing.id} 状态更新为: {order_status}")

    return {
        "action": "order_status_updated",
        "order_id": order_id,
        "new_status": order_status,
    }


async def _handle_order_cancelled(data: dict) -> dict:
    """处理订单取消事件"""
    order_id = data.get("order_id", "unknown")
    cancel_reason = data.get("cancel_reason", "unknown")

    logger.info(f"❌ 订单取消: order_id={order_id}, reason={cancel_reason}")

    # 释放库存
    items = data.get("order_items", [])
    async with async_session() as db:
        for item in items:
            shopee_item_id = item.get("item_id") or item.get("shopee_item_id")
            if shopee_item_id:
                result = await db.execute(
                    Listing.__table__.select().where(Listing.shopee_item_id == shopee_item_id)
                )
                listing = result.scalar_one_or_none()
                if listing:
                    listing.stock = (listing.stock or 0) + item.get("quantity", 1)
                    listing.shopee_status = "cancelled"
                    await db.commit()
                    logger.info(f"  ✅ Listing #{listing.id} 库存已恢复: +{item.get('quantity', 1)}")

    return {
        "action": "order_cancelled",
        "order_id": order_id,
        "reason": cancel_reason,
    }


async def _handle_new_message(data: dict) -> dict:
    """处理新消息事件（触发 AI 自动回复）"""
    message_id = data.get("message_id", "unknown")
    message_text = data.get("message", {}).get("text", "")

    logger.info(f"💬 新消息: message_id={message_id}, text={message_text[:100]}")

    # TODO: 触发 AI 自动回复
    # 1. 分析客户意图
    # 2. 生成泰语回复
    # 3. 通过 Shopee API 发送

    return {
        "action": "new_message_received",
        "message_id": message_id,
        "requires_ai_reply": True,
    }


async def _handle_product_review(data: dict) -> dict:
    """处理商品评价事件"""
    review_id = data.get("review_id", "unknown")
    rating = data.get("rating", 0)

    logger.info(f"⭐ 新评价: review_id={review_id}, rating={rating}")

    # 负面评价触发补偿策略
    if rating < 3:
        logger.warning(f"  ⚠️ 负面评价触发补偿策略: review_id={review_id}")
        return {
            "action": "negative_review",
            "review_id": review_id,
            "rating": rating,
            "compensation": True,
            "suggested_actions": [
                "联系客户解决问题",
                "赠送优惠券补偿",
                "记录到客服工单系统",
            ],
        }

    # 正面评价统计
    return {
        "action": "positive_review",
        "review_id": review_id,
        "rating": rating,
        "compensation": False,
    }


async def _handle_inventory_alert(data: dict) -> dict:
    """处理库存预警事件"""
    shopee_item_id = data.get("item_id") or data.get("shopee_item_id")
    current_stock = data.get("stock", 0)
    alert_threshold = data.get("alert_threshold", 10)

    logger.info(f"📊 库存预警: item_id={shopee_item_id}, stock={current_stock}")

    # 更新本地库存
    async with async_session() as db:
        if shopee_item_id:
            result = await db.execute(
                Listing.__table__.select().where(Listing.shopee_item_id == shopee_item_id)
            )
            listing = result.scalar_one_or_none()
            if listing:
                listing.stock = current_stock
                if current_stock < alert_threshold:
                    listing.shopee_status = "low_stock"
                    logger.warning(f"  ⚠️ Listing #{listing.id} 库存不足: {current_stock}")
                else:
                    listing.shopee_status = "active"
                await db.commit()

    return {
        "action": "inventory_updated",
        "item_id": shopee_item_id,
        "current_stock": current_stock,
        "below_threshold": current_stock < alert_threshold,
    }


# ==================== Webhook 端点 ====================

@router.post("/shopee/order")
async def shopee_order_webhook(request: Request):
    """Shopee 订单 Webhook"""
    try:
        body_bytes = await request.body()
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="无效 JSON")

    # 验证签名
    signature = request.headers.get("X-Shopee-Signature", "")
    if not _verify_signature(body_bytes, signature):
        raise HTTPException(status_code=401, detail="签名验证失败")

    event_type = body.get("type", "")
    event_data = body.get("data", {})

    handlers = {
        "ORDER_STATUS_UPDATED": _handle_order_status_updated,
        "ORDER_CANCELLED": _handle_order_cancelled,
    }

    handler = handlers.get(event_type)
    if not handler:
        logger.warning(f"未知的订单事件类型: {event_type}")
        return {"status": "received", "message": f"未知事件类型: {event_type}"}

    try:
        result = await handler(event_data)
        return {"status": "processed", "result": result}
    except Exception as e:
        logger.error(f"订单事件处理失败: {e}")
        return {"status": "error", "error": str(e)}


@router.post("/shopee/chat")
async def shopee_chat_webhook(request: Request):
    """Shopee 聊天 Webhook"""
    try:
        body_bytes = await request.body()
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="无效 JSON")

    if not _verify_signature(body_bytes, request.headers.get("X-Shopee-Signature", "")):
        raise HTTPException(status_code=401, detail="签名验证失败")

    event_type = body.get("type", "")
    event_data = body.get("data", {})

    handlers = {
        "NEW_MESSAGE": _handle_new_message,
    }

    handler = handlers.get(event_type)
    if not handler:
        logger.warning(f"未知的聊天事件类型: {event_type}")
        return {"status": "received", "message": f"未知事件类型: {event_type}"}

    try:
        result = await handler(event_data)
        return {"status": "processed", "result": result}
    except Exception as e:
        logger.error(f"聊天事件处理失败: {e}")
        return {"status": "error", "error": str(e)}


@router.post("/shopee/review")
async def shopee_review_webhook(request: Request):
    """Shopee 评价 Webhook"""
    try:
        body_bytes = await request.body()
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="无效 JSON")

    if not _verify_signature(body_bytes, request.headers.get("X-Shopee-Signature", "")):
        raise HTTPException(status_code=401, detail="签名验证失败")

    event_data = body.get("data", {})

    try:
        result = await _handle_product_review(event_data)
        return {"status": "processed", "result": result}
    except Exception as e:
        logger.error(f"评价事件处理失败: {e}")
        return {"status": "error", "error": str(e)}


@router.post("/shopee/inventory")
async def shopee_inventory_webhook(request: Request):
    """Shopee 库存 Webhook"""
    try:
        body_bytes = await request.body()
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="无效 JSON")

    if not _verify_signature(body_bytes, request.headers.get("X-Shopee-Signature", "")):
        raise HTTPException(status_code=401, detail="签名验证失败")

    event_data = body.get("data", {})

    try:
        result = await _handle_inventory_alert(event_data)
        return {"status": "processed", "result": result}
    except Exception as e:
        logger.error(f"库存事件处理失败: {e}")
        return {"status": "error", "error": str(e)}


@router.get("/shopee/callback-url")
async def get_callback_url():
    """获取 Shopee 回调 URL 配置"""
    return {
        "callback_url": "https://api.pipixia.com/webhook/shopee",
        "events": [
            "ORDER_STATUS_UPDATED",
            "ORDER_CANCELLED",
            "NEW_MESSAGE",
            "PRODUCT_REVIEW",
            "INVENTORY_ALERT",
        ],
        "signature_method": "HMAC-SHA256",
    }
