"""
Webhook 路由
"""

from fastapi import APIRouter, Request

router = APIRouter(tags=["Webhooks"])


@router.post("/shopee/order")
async def shopee_order_webhook(request: Request):
    """Shopee 订单 Webhook"""
    # TODO: 实现
    raise NotImplementedError("订单 Webhook 功能待实现")


@router.post("/shopee/chat")
async def shopee_chat_webhook(request: Request):
    """Shopee 聊天 Webhook"""
    # TODO: 实现
    raise NotImplementedError("聊天 Webhook 功能待实现")


@router.post("/shopee/review")
async def shopee_review_webhook(request: Request):
    """Shopee 评价 Webhook"""
    # TODO: 实现
    raise NotImplementedError("评价 Webhook 功能待实现")
