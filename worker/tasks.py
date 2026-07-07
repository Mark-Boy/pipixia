"""
Celery 任务定义 — 翻译/上架/财务/库存等后台任务
"""

import logging
import time
from datetime import datetime, timedelta

from worker.celery_app import celery_app

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


@celery_app.task(
    name="worker.tasks.listing_product",
    bind=True,
    max_retries=5,
    default_retry_delay=60,
)
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
def profit_circuit_breaker() -> dict:
    """
    利润熔断检查
    
    自动下架利润率低于阈值的商品
    """
    try:
        logger.info("⚡ 利润熔断检查...")
        
        import asyncio
        from api.database import engine, async_session
        from api.models.product import Product
        from api.models.risk_log import RiskLog
        from sqlalchemy import select, update
        from api.services.exchange import fetch_exchange_rate

        threshold = 10  # 利润率阈值 %

        async def _run():
            async with async_session() as db:
                # 查询所有 audited 状态的商品
                result = await db.execute(
                    select(Product).where(
                        Product.status == "audited",
                        Product.profit_margin < threshold,
                    )
                )
                low_profit_products = result.scalars().all()

                removed_count = 0
                for product in low_profit_products:
                    # 重新计算利润率（使用实时汇率）
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
                        # 更新状态为 blocked
                        await db.execute(
                            update(Product)
                            .where(Product.id == product.id)
                            .values(status="blocked", risk_status="block")
                        )
                        
                        # 记录风控日志
                        risk_log = RiskLog(
                            product_id=product.id,
                            risk_type="profit",
                            risk_detail=f"利润率 {actual_margin}% 低于阈值 {threshold}%",
                            action_taken="自动拦截，标记利润不足",
                        )
                        db.add(risk_log)
                        removed_count += 1
                        logger.info(f"  ⚡ 熔断: 商品 #{product.id} 利润率 {actual_margin}% < {threshold}%")

                await db.commit()
                return removed_count

        removed_count = asyncio.run(_run())
        logger.info(f"✅ 熔断检查完成，下架 {removed_count} 个商品")
        return {
            "status": "completed",
            "removed_count": removed_count,
            "threshold": threshold,
            "checked_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ 熔断检查失败: {e}")
        return {"status": "failed", "error": str(e)}


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


def _handle_order_created(payload: dict) -> dict:
    """处理订单创建事件"""
    order_id = payload.get("order_id", "unknown")
    logger.info(f"📦 新订单: {order_id}")
    return {"action": "order_received", "order_id": order_id}


def _handle_order_cancelled(payload: dict) -> dict:
    """处理订单取消事件"""
    order_id = payload.get("order_id", "unknown")
    logger.info(f"❌ 订单取消: {order_id}")
    return {"action": "order_cancelled", "order_id": order_id}


def _handle_review_added(payload: dict) -> dict:
    """处理评价事件"""
    review_id = payload.get("review_id", "unknown")
    rating = payload.get("rating", 0)
    logger.info(f"⭐ 新评价: {review_id}, 评分: {rating}")
    
    # 负面评价触发补偿策略
    if rating < 3:
        return {"action": "negative_review", "review_id": review_id, "compensation": True}
    return {"action": "positive_review", "review_id": review_id}


def _handle_inventory_changed(payload: dict) -> dict:
    """处理库存变化事件"""
    product_id = payload.get("product_id", "unknown")
    new_stock = payload.get("stock", 0)
    logger.info(f"📊 库存变化: {product_id}, 新库存: {new_stock}")
    
    if new_stock < 10:
        return {"action": "low_stock_alert", "product_id": product_id}
    return {"action": "stock_updated", "product_id": product_id}


def _handle_unknown(payload: dict) -> dict:
    """未知事件类型"""
    logger.warning(f"⚠️ 未知 Webhook 事件: {payload}")
    return {"action": "ignored", "reason": "unknown_event_type"}
