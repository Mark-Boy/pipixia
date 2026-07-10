"""
Celery 任务定义 — 翻译/上架/财务/库存等后台任务
"""

import logging
import time
from datetime import datetime, timedelta

from celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="worker.tasks.translate_product",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def translate_product(self, product_id: int) -> dict:
    """
    翻译商品（LangGraph 工作流）
    
    Args:
        product_id: 商品 ID
        
    Returns:
        翻译结果
    """
    try:
        logger.info(f"🔄 开始翻译商品 #{product_id}")

        # 导入 LangGraph 工作流
        from api.langgraph.graph import run_translation_workflow

        # 运行翻译工作流
        result = run_translation_workflow(product_id=product_id)

        logger.info(f"✅ 商品 #{product_id} 翻译完成")
        return {
            "product_id": product_id,
            "status": "completed",
            "risk_status": result.get("risk_status"),
            "profit_margin": result.get("profit_margin"),
            "title_th": result.get("title_th"),
            "desc_th": result.get("desc_th"),
        }

    except Exception as e:
        logger.error(f"❌ 商品 #{product_id} 翻译失败: {e}")
        # 重试
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        return {
            "product_id": product_id,
            "status": "failed",
            "error": str(e),
        }


@celery_app.task(
    name="worker.tasks.batch_translate_task",
    bind=True,
    max_retries=2,
)
def batch_translate_task(self, product_ids: list[int]) -> dict:
    """
    批量翻译（别名，供 router 调用）
    
    注意: 这是 batch_translate 的别名，保持向后兼容
    """
    return batch_translate(*product_ids)


@celery_app.task(
    name="worker.tasks.batch_translate",
    bind=True,
    max_retries=2,
)
def batch_translate(self, product_ids: list[int]) -> dict:
    """
    批量翻译
    
    Args:
        product_ids: 商品 ID 列表
        
    Returns:
        批量翻译结果
    """
    results = {
        "total": len(product_ids),
        "success": 0,
        "failed": 0,
        "details": [],
    }

    for pid in product_ids:
        try:
            from api.langgraph.graph import run_translation_workflow
            result = run_translation_workflow(product_id=pid)
            results["success"] += 1
            results["details"].append({
                "product_id": pid,
                "status": "success",
                "risk_status": result.get("risk_status"),
            })
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "product_id": pid,
                "status": "failed",
                "error": str(e),
            })
        # 简单的速率限制
        time.sleep(0.5)

    return results


@celery_app.task(name="worker.tasks.generate_daily_report")
def generate_daily_report() -> dict:
    """生成日报"""
    try:
        logger.info("📊 生成日报...")
        
        from api.database import async_session
        from api.models.product import Product
        from api.models.listing import Listing
        from sqlalchemy import select, func
        from datetime import date

        async def _run():
            async with async_session() as db:
                today = date.today()
                
                # 商品统计
                total = await db.execute(select(func.count()).select_from(Product))
                total_products = total.scalar() or 0

                # 今日新增
                today_start = datetime.combine(today, datetime.min.time())
                tomorrow = today_start + timedelta(days=1)
                
                new_result = await db.execute(
                    select(func.count()).where(
                        Product.created_at >= today_start,
                        Product.created_at < tomorrow,
                    )
                )
                new_products = new_result.scalar() or 0

                # 上架统计
                listing_result = await db.execute(
                    select(func.count()).where(
                        Listing.created_at >= today_start,
                        Listing.created_at < tomorrow,
                    )
                )
                new_listings = listing_result.scalar() or 0

                return {
                    "date": today.isoformat(),
                    "total_products": total_products,
                    "new_products_today": new_products,
                    "new_listings_today": new_listings,
                }

        import asyncio
        result = asyncio.run(_run())
        logger.info(f"✅ 日报生成完成: {result}")
        return result

    except Exception as e:
        logger.error(f"❌ 日报生成失败: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(name="worker.tasks.update_exchange_rate")
def update_exchange_rate() -> dict:
    """更新汇率（CNY → THB）"""
    try:
        logger.info("💱 更新汇率...")
        
        # TODO: 调用真实汇率 API（如 exchangerate.host）
        try:
            from api.services.exchange import fetch_exchange_rate
            exchange_rate = fetch_exchange_rate()
        except Exception:
            exchange_rate = 5.0  # 回退汇率

        logger.info(f"✅ 汇率更新: 1 CNY = {exchange_rate} THB")
        return {
            "currency": "CNY/THB",
            "rate": exchange_rate,
            "updated_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ 汇率更新失败: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(name="worker.tasks.sync_inventory")
def sync_inventory() -> dict:
    """同步库存"""
    try:
        logger.info("📦 同步库存...")
        
        # TODO: 从货源平台同步库存到 Shopee
        # 1. 查询所有 active 商品
        # 2. 调用 1688/拼多多 API 获取库存
        # 3. 更新 Shopee 库存
        
        logger.info("✅ 库存同步完成（模拟）")
        return {
            "status": "completed",
            "synced_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ 库存同步失败: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(name="worker.tasks.profit_circuit_breaker")
async def profit_circuit_breaker() -> dict:
    """
    利润熔断检查
    
    自动下架利润率低于阈值的商品
    
    流程:
    1. 查询所有 audited 状态的商品
    2. 使用实时汇率重新计算实际利润率
    3. 利润率低于阈值的商品自动标记为 blocked
    4. 写入 risk_logs 记录
    5. 可选：发送 Telegram 告警
    
    Returns:
        熔断检查结果
    """
    try:
        import asyncio
        import httpx
        from api.config import get_settings
        from api.database import async_session
        from api.models.product import Product
        from api.models.risk_log import RiskLog
        from sqlalchemy import select, update
        from api.services.exchange import fetch_exchange_rate

        settings = get_settings()
        threshold = settings.MIN_PROFIT_MARGIN  # 从配置读取阈值，默认 10%

        async def _run():
            async with async_session() as db:
                # 1. 查询所有 audited 状态的商品
                result = await db.execute(
                    select(Product)
                    .where(
                        Product.status == "audited",
                        Product.profit_margin < threshold,
                    )
                    .limit(100)  # 每次最多检查 100 个，避免大数据量
                )
                low_profit_products = result.scalars().all()

                if not low_profit_products:
                    logger.info("  ✅ 无商品需要熔断检查")
                    return 0

                logger.info(f"  🔍 发现 {len(low_profit_products)} 个低利润商品")

                removed_count = 0
                blocked_products = []

                for product in low_profit_products:
                    # 2. 使用实时汇率重新计算实际利润率
                    try:
                        exchange_rate = fetch_exchange_rate()
                    except Exception:
                        exchange_rate = 5.0

                    cost_thb = (product.cost_cny or 0) * exchange_rate
                    revenue_thb = product.price_thb or 0

                    if revenue_thb > 0:
                        actual_margin = round(((revenue_thb - cost_thb) / revenue_thb) * 100, 2)
                    else:
                        actual_margin = 0

                    if actual_margin < threshold:
                        # 3. 更新状态为 blocked
                        await db.execute(
                            update(Product)
                            .where(Product.id == product.id)
                            .values(status="blocked", risk_status="block")
                        )

                        # 4. 记录风控日志
                        risk_log = RiskLog(
                            product_id=product.id,
                            risk_type="profit",
                            risk_detail=f"利润率 {actual_margin}% 低于阈值 {threshold}%",
                            action_taken="自动拦截，标记利润不足",
                        )
                        db.add(risk_log)
                        removed_count += 1
                        blocked_products.append({
                            "product_id": product.id,
                            "title": product.title_zh,
                            "margin": actual_margin,
                            "threshold": threshold,
                        })
                        logger.info(
                            f"  ⚡ 熔断: 商品 #{product.id} 利润率 {actual_margin}% "
                            f"< 阈值 {threshold}%"
                        )

                await db.commit()

                # 5. 发送 Telegram 告警（如果配置了）
                if blocked_products and settings.TELEGRAM_BOT_TOKEN:
                    await _send_telegram_alert(blocked_products, settings)

                return removed_count

        removed_count = await _run()
        logger.info(f"✅ 熔断检查完成，下架 {removed_count} 个商品")

        return {
            "status": "completed",
            "removed_count": removed_count,
            "threshold": threshold,
            "checked_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ 熔断检查失败: {e}", exc_info=True)
        return {"status": "failed", "error": str(e), "checked_at": datetime.now().isoformat()}


async def _send_telegram_alert(blocked_products: list[dict], settings) -> None:
    """发送 Telegram 告警消息"""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return

    try:
        # 构建告警消息
        product_list = "\n".join(
            f"  • {p['title']} (利润率 {p['margin']}% < {p['threshold']}%)"  
            for p in blocked_products
        )
        
        message = (
            f"⚡ **利润熔断告警**\n\n"
            f"检测到 {len(blocked_products)} 个商品利润率低于阈值，已自动下架：\n\n"
            f"{product_list}\n\n"
            f"阈值: {blocked_products[0]['threshold']}%\n"
            f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": settings.TELEGRAM_CHAT_ID,
                    "text": message,
                    "parse_mode": "Markdown",
                }
            )
        logger.info("  ✅ Telegram 告警已发送")

    except Exception as e:
        logger.error(f"  ❌ Telegram 告警发送失败: {e}")


@celery_app.task(name="worker.tasks.process_image")
def process_image(image_url: str, product_id: int) -> dict:
    """
    图片翻译处理（OCR → 翻译 → 合成）
    
    Args:
        image_url: 图片 URL
        product_id: 商品 ID
        
    Returns:
        处理结果
    """
    try:
        logger.info(f"🖼️ 处理图片: {image_url}")

        # TODO: 调用 PaddleOCR 提取文字
        # TODO: 调用翻译服务
        # TODO: 调用 OpenCV 合成新图片

        result_url = image_url  # 模拟：原图返回

        logger.info(f"✅ 图片处理完成")
        return {
            "product_id": product_id,
            "source_url": image_url,
            "result_url": result_url,
            "status": "completed",
        }

    except Exception as e:
        logger.error(f"❌ 图片处理失败: {e}")
        return {
            "product_id": product_id,
            "status": "failed",
            "error": str(e),
        }


@celery_app.task(name="worker.tasks.webhook_handler")
def webhook_handler(event_type: str, payload: dict) -> dict:
    """
    Webhook 事件处理
    
    Args:
        event_type: 事件类型（order_created, review, etc.）
        payload: 事件数据
        
    Returns:
        处理结果
    """
    try:
        logger.info(f"📨 处理 Webhook: {event_type}")

        handlers = {
            "order_created": _handle_order_created,
            "order_cancelled": _handle_order_cancelled,
            "review_added": _handle_review_added,
            "inventory_changed": _handle_inventory_changed,
        }

        handler = handlers.get(event_type, _handle_unknown)
        result = handler(payload)

        return {
            "event_type": event_type,
            "status": "processed",
            "result": result,
        }

    except Exception as e:
        logger.error(f"❌ Webhook 处理失败: {e}")
        return {
            "event_type": event_type,
            "status": "failed",
            "error": str(e),
        }


async def _handle_order_created_db(payload: dict) -> dict:
    """处理订单创建事件 — 数据库操作版"""
    from api.database import async_session
    from api.models.listing import Listing
    
    order_id = payload.get("order_id", "unknown")
    order_items = payload.get("order_items", [])
    
    async with async_session() as db:
        for item in order_items:
            shopee_item_id = item.get("item_id") or item.get("shopee_item_id")
            if not shopee_item_id:
                continue
            
            # 查找或创建本地 listing
            result = await db.execute(
                Listing.__table__.select().where(
                    Listing.shopee_item_id == shopee_item_id
                )
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                # 创建新的上架记录
                new_listing = Listing(
                    shopee_item_id=shopee_item_id,
                    shopee_status="pending",
                    audit_status="approved",
                    stock=item.get("quantity", 0),
                    listing_mode="auto",
                )
                db.add(new_listing)
                logger.info(f"  📦 新上架记录: shopee_item_id={shopee_item_id}")
            else:
                existing.shopee_status = "pending"
                logger.info(f"  ✅ Listing #{existing.id} 状态更新为 pending")
        
        await db.commit()
    
    return {
        "action": "order_received",
        "order_id": order_id,
        "items_processed": len(order_items),
    }


async def _handle_order_cancelled_db(payload: dict) -> dict:
    """处理订单取消事件 — 释放库存"""
    from api.database import async_session
    from api.models.listing import Listing
    
    order_id = payload.get("order_id", "unknown")
    cancel_reason = payload.get("cancel_reason", "unknown")
    order_items = payload.get("order_items", [])
    
    total_released = 0
    
    async with async_session() as db:
        for item in order_items:
            shopee_item_id = item.get("item_id") or item.get("shopee_item_id")
            if not shopee_item_id:
                continue
            
            result = await db.execute(
                Listing.__table__.select().where(
                    Listing.shopee_item_id == shopee_item_id
                )
            )
            listing = result.scalar_one_or_none()
            if listing:
                listing.stock = (listing.stock or 0) + item.get("quantity", 0)
                listing.shopee_status = "cancelled"
                total_released += item.get("quantity", 0)
                logger.info(
                    f"  ✅ Listing #{listing.id} 库存恢复: "
                    f"+{item.get('quantity', 0)} (当前: {listing.stock})"
                )
        
        await db.commit()
    
    return {
        "action": "order_cancelled",
        "order_id": order_id,
        "cancel_reason": cancel_reason,
        "total_released": total_released,
    }


async def _handle_review_added_db(payload: dict) -> dict:
    """处理评价事件 — 触发补偿策略"""
    from api.database import async_session
    from api.models.listing import Listing
    from api.models.risk_log import RiskLog
    
    review_id = payload.get("review_id", "unknown")
    rating = payload.get("rating", 0)
    comment = payload.get("comment", "")
    shopee_item_id = payload.get("item_id") or payload.get("shopee_item_id")
    
    async with async_session() as db:
        if shopee_item_id:
            result = await db.execute(
                Listing.__table__.select().where(
                    Listing.shopee_item_id == shopee_item_id
                )
            )
            listing = result.scalar_one_or_none()
            if listing:
                logger.info(f"  ⭐ 更新 Listing #{listing.id} 评价记录")
                # 这里可以存储评价信息到 listing 的 variation_data
                # 或创建新的 Review 模型
    
    result = {
        "action": "review_received",
        "review_id": review_id,
        "rating": rating,
    }
    
    if rating < 3:
        result["action"] = "negative_review"
        result["compensation"] = True
        result["suggested_actions"] = [
            "联系客户解决问题",
            "赠送优惠券补偿",
            "记录到客服工单系统",
        ]
    else:
        result["action"] = "positive_review"
        result["compensation"] = False
    
    return result


async def _handle_inventory_changed_db(payload: dict) -> dict:
    """处理库存变化事件"""
    from api.database import async_session
    from api.models.listing import Listing
    
    shopee_item_id = payload.get("item_id") or payload.get("shopee_item_id")
    current_stock = payload.get("stock", 0)
    alert_threshold = payload.get("alert_threshold", 10)
    
    async with async_session() as db:
        if shopee_item_id:
            result = await db.execute(
                Listing.__table__.select().where(
                    Listing.shopee_item_id == shopee_item_id
                )
            )
            listing = result.scalar_one_or_none()
            if listing:
                listing.stock = current_stock
                if current_stock < alert_threshold:
                    listing.shopee_status = "low_stock"
                    logger.warning(
                        f"  ⚠️ Listing #{listing.id} 库存不足: {current_stock}"
                    )
                else:
                    listing.shopee_status = "active"
                await db.commit()
    
    return {
        "action": "inventory_updated",
        "item_id": shopee_item_id,
        "current_stock": current_stock,
        "below_threshold": current_stock < alert_threshold,
    }


async def _handle_unknown(payload: dict) -> dict:
    """未知事件类型"""
    logger.warning(f"⚠️ 未知 Webhook 事件: {payload}")
    return {"action": "ignored", "reason": "unknown_event_type"}


@celery_app.task(name="worker.tasks.process_image")
def process_image(image_url: str, product_id: int) -> dict:
    """
    图片翻译处理（OCR → 翻译 → 合成）
    
    Args:
        image_url: 图片 URL
        product_id: 商品 ID
        
    Returns:
        处理结果
    """
    try:
        logger.info(f"🖼️ 处理图片: {image_url}")

        # TODO: 调用 PaddleOCR 提取文字
        # TODO: 调用翻译服务
        # TODO: 调用 OpenCV 合成新图片

        result_url = image_url  # 模拟：原图返回

        logger.info(f"✅ 图片处理完成")
        return {
            "product_id": product_id,
            "source_url": image_url,
            "result_url": result_url,
            "status": "completed",
        }

    except Exception as e:
        logger.error(f"❌ 图片处理失败: {e}")
        return {
            "product_id": product_id,
            "status": "failed",
            "error": str(e),
        }


# ==================== 异步 Webhook 处理器 ====================


@celery_app.task(name="worker.tasks.webhook_handler_async")
async def webhook_handler_async(event_type: str, payload: dict) -> dict:
    """
    Webhook 事件异步处理（数据库操作版）
    
    Args:
        event_type: 事件类型（order_created, order_cancelled, etc.）
        payload: 事件数据
        
    Returns:
        处理结果
    """
    try:
        logger.info(f"📨 处理 Webhook [async]: {event_type}")

        handlers = {
            "order_created": _handle_order_created_db,
            "order_cancelled": _handle_order_cancelled_db,
            "review_added": _handle_review_added_db,
            "inventory_changed": _handle_inventory_changed_db,
        }

        handler = handlers.get(event_type, _handle_unknown)
        result = await handler(payload)

        return {
            "event_type": event_type,
            "status": "processed",
            "result": result,
        }

    except Exception as e:
        logger.error(f"❌ Webhook 处理失败: {e}", exc_info=True)
        return {
            "event_type": event_type,
            "status": "failed",
            "error": str(e),
        }


@celery_app.task(name="worker.tasks.listing_product")
def listing_product(self, product_id: int, listing_id: int = None) -> dict:
    """
    上架商品到 Shopee

    Args:
        product_id: 商品 ID
        listing_id: 上架记录 ID

    Returns:
        上架结果
    """
    try:
        logger.info(f"📋 开始上架商品 #{product_id}")

        # TODO: 调用 Shopee API 创建商品
        # 1. 上传主图（异步模式）
        # 2. 创建商品（标题、描述、价格、变体）
        # 3. 设置库存
        # 4. 返回 shopee_item_id

        # 模拟上架成功
        shopee_item_id = f"shopee-{product_id}-{int(time.time())}"

        logger.info(f"✅ 商品 #{product_id} 上架成功: {shopee_item_id}")
        return {
            "product_id": product_id,
            "listing_id": listing_id,
            "shopee_item_id": shopee_item_id,
            "status": "success",
        }

    except Exception as e:
        logger.error(f"❌ 商品 #{product_id} 上架失败: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
        return {
            "product_id": product_id,
            "status": "failed",
            "error": str(e),
        }
