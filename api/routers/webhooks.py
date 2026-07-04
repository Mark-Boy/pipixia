"""
Webhook 路由 — Shopee 事件接收
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.security import HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.database import async_session
from api.models.product import Product
from api.models.listing import Listing

router = APIRouter(tags=["Webhooks"])

# Webhook 签名验证 Key（从配置读取）
WEBHOOK_SECRET = "pipixia-webhook-secret"


def verify_signature(request: Request, secret: str = WEBHOOK_SECRET) -> bool:
    """验证 Webhook 签名"""
    signature = request.headers.get("X-Shopee-Signature", "")
    body = request.body()
    
    import hashlib
    import hmac
    expected = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)


@router.post("/shopee/order")
async def shopee_order_webhook(request: Request):
    """Shopee 订单 Webhook"""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="无效 JSON")

    # 验证签名
    if not verify_signature(request):
        raise HTTPException(status_code=401, detail="签名验证失败")

    event_type = body.get("type", "")
    
    # TODO: 根据 event_type 分发处理
    # order_created, order_cancelled, order_shipped, order_delivered, etc.

    # 异步更新库存
    # order_data = body.get("data", {})
    # items = order_data.get("order_items", [])
    # for item in items:
    #     shopee_item_id = item.get("shop_variation_id")
    #     # 查找本地 listing
    #     ...

    return {"status": "received", "message": f"订单事件已接收: {event_type}"}


@router.post("/shopee/chat")
async def shopee_chat_webhook(request: Request):
    """Shopee 聊天 Webhook"""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="无效 JSON")

    if not verify_signature(request):
        raise HTTPException(status_code=401, detail="签名验证失败")

    event_type = body.get("type", "")

    # TODO: 处理聊天事件
    # 新消息 → 触发 AI 自动回复
    # 订单状态变更通知

    return {"status": "received", "message": f"聊天事件已接收: {event_type}"}


@router.post("/shopee/review")
async def shopee_review_webhook(request: Request):
    """Shopee 评价 Webhook"""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="无效 JSON")

    if not verify_signature(request):
        raise HTTPException(status_code=401, detail="签名验证失败")

    event_type = body.get("type", "")
    review_data = body.get("data", {})

    # TODO: 处理评价事件
    # 负面评价 → 触发补偿/跟进
    # 正面评价 → 统计评分

    # 更新商品评分
    if "product_id" in review_data:
        product_id = review_data["product_id"]
        async with async_session() as db:
            result = await db.execute(select(Product).where(Product.id == product_id))
            product = result.scalar_one_or_none()
            if product:
                # 更新平均评分（需要额外字段）
                pass

    return {"status": "received", "message": f"评价事件已接收: {event_type}"}


@router.post("/shopee/inventory")
async def shopee_inventory_webhook(request: Request):
    """Shopee 库存 Webhook"""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="无效 JSON")

    if not verify_signature(request):
        raise HTTPException(status_code=401, detail="签名验证失败")

    event_type = body.get("type", "")
    inventory_data = body.get("data", {})

    # TODO: 处理库存事件
    # 库存低于阈值 → 触发补货提醒

    return {"status": "received", "message": f"库存事件已接收: {event_type}"}


@router.get("/shopee/callback-url")
async def get_callback_url():
    """获取 Shopee 回调 URL 配置"""
    return {
        "callback_url": "https://api.pipixia.com/webhook/shopee/order",
        "events": [
            "ORDER_STATUS_UPDATED",
            "ORDER_CANCELLED",
            "NEW_MESSAGE",
            "PRODUCT_REVIEW",
            "INVENTORY_ALERT",
        ],
    }
