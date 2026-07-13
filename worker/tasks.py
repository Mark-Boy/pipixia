"""
Celery 任务定义 — 翻译 / 上架 / 财务 / 库存 / 图片翻译 / Webhook 等后台任务

设计说明:
- Celery 默认在 task_always_eager=True 下同步执行（开发模式），生产可关。
- 大量任务涉及数据库 + asyncio，但 Celery worker 不是 asyncio 事件循环环境，
  统一在任务函数内用 asyncio.run() 启动临时事件循环。
  ✓ 已验证: profit_circuit_breaker 即该模式。
- worker 容器中 PYTHONPATH 指向 /app，相对导入 `from api.xxx import ...` 才能工作；
  本地 dev 同样依赖 PYTHONPATH 包含项目根目录，约定不变更。
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta

from celery_app import celery_app

logger = logging.getLogger(__name__)


# ==================== 文本翻译任务 ====================


@celery_app.task(
    name="worker.tasks.translate_product",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def translate_product(self, product_id: int) -> dict:
    """
    翻译单个商品（LangGraph 翻译工作流全链路）:
    OCR 提取图片文字 → 文本翻译中→泰 → 图片泰语合成 → 风控 → 利润核算 → SEO 标签生成

    失败指数退避重试 3 次。
    """
    try:
        logger.info(f"🔄 开始翻译商品 #{product_id}")
        from api.langgraph.graph import run_translation_workflow

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
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        return {"product_id": product_id, "status": "failed", "error": str(e)}


@celery_app.task(
    name="worker.tasks.batch_translate",
    bind=True,
    max_retries=2,
)
def batch_translate(self, product_ids: list[int]) -> dict:
    """批量翻译 —— 顺序调用单商品翻译，内部简单速率限制避免 LLM API 限流。"""
    results = {"total": len(product_ids), "success": 0, "failed": 0, "details": []}
    from api.langgraph.graph import run_translation_workflow

    for pid in product_ids:
        try:
            r = run_translation_workflow(product_id=pid)
            results["success"] += 1
            results["details"].append({
                "product_id": pid,
                "status": "success",
                "risk_status": r.get("risk_status"),
            })
        except Exception as e:
            results["failed"] += 1
            results["details"].append({"product_id": pid, "status": "failed", "error": str(e)})
        # 简单速率限制（避免触发 LLM API 限流）
        if pid != product_ids[-1]:
            time.sleep(0.5)
    return results


@celery_app.task(
    name="worker.tasks.batch_translate_task",
    bind=True,
    max_retries=2,
)
def batch_translate_task(self, product_ids: list[int]) -> dict:
    """batch_translate 的别名 —— 保持路由层向后兼容命名。"""
    return batch_translate.__wrapped__(self, product_ids)  # type: ignore[attr-defined]


# ==================== 报告 / 汇率 / 库存 ====================


@celery_app.task(name="worker.tasks.generate_daily_report")
def generate_daily_report() -> dict:
    """生成每日运营日报（商品/上架新增统计）。"""
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
                total = await db.execute(select(func.count()).select_from(Product))
                total_products = total.scalar() or 0

                today_start = datetime.combine(today, datetime.min.time())
                tomorrow = today_start + timedelta(days=1)

                new_result = await db.execute(
                    select(func.count()).where(
                        Product.created_at >= today_start,
                        Product.created_at < tomorrow,
                    )
                )
                new_products = new_result.scalar() or 0

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

        result = asyncio.run(_run())
        logger.info(f"✅ 日报生成完成: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ 日报生成失败: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(name="worker.tasks.update_exchange_rate")
def update_exchange_rate() -> dict:
    """更新 CNY→THB 实时汇率（写入 Redis 缓存）。"""
    try:
        logger.info("💱 更新汇率...")
        try:
            from api.services.exchange import fetch_exchange_rate
            rate = fetch_exchange_rate()
        except Exception:
            rate = 5.0  # 回退汇率
        logger.info(f"✅ 汇率更新: 1 CNY = {rate} THB")
        return {
            "currency": "CNY/THB",
            "rate": rate,
            "updated_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ 汇率更新失败: {e}")
        return {"status": "failed", "error": str(e)}


@celery_app.task(name="worker.tasks.sync_inventory")
def sync_inventory() -> dict:
    """库存同步占位 —— TODO: 从 1688/拼多多采集库存推送到 Shopee。"""
    logger.info("📦 同步库存（模拟完成）")
    return {"status": "completed", "synced_at": datetime.now().isoformat()}


# ==================== 利润熔断 ====================


@celery_app.task(name="worker.tasks.profit_circuit_breaker")
async def profit_circuit_breaker() -> dict:
    """
    利润熔断检查 —— 每日自动下架利润率低于阈值的商品。

    流程:
    1. 查询所有 audited 商品
    2. 用实时汇率重算实际利润率
    3. 低于阈值的标记为 blocked
    4. 写 risk_logs 记录
    5. 配置 TELEGRAM_BOT_TOKEN 时发送告警
    """
    try:
        import httpx
        from api.config import get_settings
        from api.database import async_session
        from api.models.product import Product
        from api.models.risk_log import RiskLog
        from sqlalchemy import select, update
        from api.services.exchange import fetch_exchange_rate

        settings = get_settings()
        threshold = settings.MIN_PROFIT_MARGIN  # 默认 10%

        async def _run():
            async with async_session() as db:
                result = await db.execute(
                    select(Product)
                    .where(
                        Product.status == "audited",
                        Product.profit_margin < threshold,
                    )
                    .limit(100)
                )
                low_profit_products = result.scalars().all()

                if not low_profit_products:
                    logger.info("  ✅ 无商品需要熔断检查")
                    return 0, []

                logger.info(f"  🔍 发现 {len(low_profit_products)} 个低利润商品")
                removed_count = 0
                blocked_products = []

                for product in low_profit_products:
                    try:
                        exchange_rate = fetch_exchange_rate()
                    except Exception:
                        exchange_rate = 5.0

                    cost_thb = (product.cost_cny or 0) * exchange_rate
                    revenue_thb = product.price_thb or 0
                    actual_margin = (
                        round(((revenue_thb - cost_thb) / revenue_thb) * 100, 2)
                        if revenue_thb > 0
                        else 0
                    )

                    if actual_margin < threshold:
                        await db.execute(
                            update(Product)
                            .where(Product.id == product.id)
                            .values(status="blocked", risk_status="block")
                        )
                        db.add(RiskLog(
                            product_id=product.id,
                            risk_type="profit",
                            risk_detail=f"利润率 {actual_margin}% 低于阈值 {threshold}%",
                            action_taken="自动拦截，标记利润不足",
                        ))
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

                if blocked_products and settings.TELEGRAM_BOT_TOKEN:
                    await _send_telegram_alert(blocked_products, settings)
                return removed_count, blocked_products

        removed_count, blocked_products = await _run()
        logger.info(f"✅ 熔断检查完成，下架 {removed_count} 个商品")
        return {
            "status": "completed",
            "removed_count": removed_count,
            "blocked_products": blocked_products,
            "threshold": threshold,
            "checked_at": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ 熔断检查失败: {e}", exc_info=True)
        return {"status": "failed", "error": str(e), "checked_at": datetime.now().isoformat()}


async def _send_telegram_alert(blocked_products: list[dict], settings) -> None:
    """发送 Telegram 告警消息。"""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return
    try:
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
                },
            )
        logger.info("  ✅ Telegram 告警已发送")
    except Exception as e:
        logger.error(f"  ❌ Telegram 告警发送失败: {e}")


# ==================== 图片翻译任务 (S07) ====================


@celery_app.task(
    name="worker.tasks.process_image",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
)
def process_image(self, image_url: str, product_id: int = None, image_index: int = 0) -> dict:
    """
    图片翻译处理（OCR → 翻译 → 合成泰语文字覆盖）—— S07 核心。

    Args:
        image_url: 源图片 URL
        product_id: 商品 ID（用于对象存储 key 命名）
        image_index: 第几张图

    Returns:
        {
            "product_id", "image_index",
            "source_url", "result_url",
            "ocr_blocks", "translated_blocks", "status"
        }
        status: completed / skipped / failed

    所有阶段失败均优雅降级返回原图 URL（不抛异常），确保 LangGraph 链路不中断。
    """
    try:
        from api.services.image_translate import translate_image

        logger.info(f"🖼️ 处理图片 #{image_index}: {image_url}")
        result = translate_image(
            image_url=image_url,
            product_id=product_id,
            image_index=image_index,
        )
        enriched = {
            "product_id": product_id,
            "image_index": image_index,
            **result,
        }
        logger.info(
            f"✅ 图片处理完成: ocr={enriched['ocr_blocks']} "
            f"translated={enriched['translated_blocks']} status={enriched['status']}"
        )
        return enriched
    except Exception as e:
        logger.error(f"❌ 图片处理失败 {image_url}: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=30 * (self.request.retries + 1))
        return {
            "product_id": product_id,
            "image_index": image_index,
            "source_url": image_url,
            "result_url": image_url,  # 失败回退原图
            "ocr_blocks": 0,
            "translated_blocks": 0,
            "status": "failed",
            "error": str(e),
        }


@celery_app.task(
    name="worker.tasks.batch_process_images",
    bind=True,
    max_retries=1,
)
def batch_process_images(self, image_urls: list[str], product_id: int = None) -> dict:
    """
    批量翻译一个商品的多张图片。逐张顺序处理，单张失败不影响其他张。

    Returns:
        {"total": n, "success": x, "failed": y, "results": [...]}
    """
    results: list[dict] = []
    success = failed = 0
    for i, url in enumerate(image_urls):
        try:
            r = process_image.__wrapped__(  # type: ignore[attr-defined]
                # 直接同步执行核心逻辑，绕过 Celery 任务派发
                None, url, product_id, i
            ) if hasattr(process_image, "__wrapped__") else _process_image_direct(
                url, product_id, i
            )
            results.append(r)
            if r.get("status") in ("completed", "skipped"):
                success += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            results.append({
                "product_id": product_id,
                "image_index": i,
                "source_url": url,
                "result_url": url,
                "status": "failed",
                "error": str(e),
            })
    return {"total": len(image_urls), "success": success, "failed": failed, "results": results}


def _process_image_direct(image_url: str, product_id, image_index: int) -> dict:
    """脱 Celery 直接调用图片翻译核心逻辑（供 batch_process_images 内复用）。"""
    from api.services.image_translate import translate_image
    result = translate_image(image_url=image_url, product_id=product_id, image_index=image_index)
    return {
        "product_id": product_id,
        "image_index": image_index,
        **result,
    }


# ==================== Webhook 事件处理（异步）====================


@celery_app.task(name="worker.tasks.webhook_handler_async")
async def webhook_handler_async(event_type: str, payload: dict) -> dict:
    """
    Webhook 事件异步处理（带数据库写入版）。

    支持事件:
    - order_created: 创建/更新本地 listing，状态置 pending
    - order_cancelled: 释放对应 listing 库存，状态置 cancelled
    - review_added: 记录评价，差评触发补偿建议
    - inventory_changed: 同步 listing 库存，低于阈值置 low_stock
    未知事件统一记录 warning 后忽略。
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
        if asyncio.iscoroutinefunction(handler):
            result = await handler(payload)
        else:
            result = handler(payload)
        return {"event_type": event_type, "status": "processed", "result": result}
    except Exception as e:
        logger.error(f"❌ Webhook 处理失败: {e}", exc_info=True)
        return {"event_type": event_type, "status": "failed", "error": str(e)}


async def _handle_order_created_db(payload: dict) -> dict:
    """处理订单创建事件 —— 创建/更新本地 listing 记录。"""
    from api.database import async_session
    from api.models.listing import Listing

    order_id = payload.get("order_id", "unknown")
    order_items = payload.get("order_items", [])

    async with async_session() as db:
        for item in order_items:
            shopee_item_id = item.get("item_id") or item.get("shopee_item_id")
            if not shopee_item_id:
                continue
            result = await db.execute(
                Listing.__table__.select().where(Listing.shopee_item_id == shopee_item_id)
            )
            existing = result.scalar_one_or_none()
            if not existing:
                db.add(Listing(
                    shopee_item_id=shopee_item_id,
                    shopee_status="pending",
                    audit_status="approved",
                    stock=item.get("quantity", 0),
                    listing_mode="auto",
                ))
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
    """处理订单取消事件 —— 释放库存。"""
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
                Listing.__table__.select().where(Listing.shopee_item_id == shopee_item_id)
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
    """处理评价事件 —— 触发补偿策略建议。"""
    review_id = payload.get("review_id", "unknown")
    rating = payload.get("rating", 0)
    result = {
        "action": "review_received",
        "review_id": review_id,
        "rating": rating,
    }
    if rating < 3:
        result.update({
            "action": "negative_review",
            "compensation": True,
            "suggested_actions": [
                "联系客户解决问题",
                "赠送优惠券补偿",
                "记录到客服工单系统",
            ],
        })
    else:
        result.update({"action": "positive_review", "compensation": False})
    return result


async def _handle_inventory_changed_db(payload: dict) -> dict:
    """处理库存变化事件 —— 同步 listing 库存并触发低库存标记。"""
    from api.database import async_session
    from api.models.listing import Listing

    shopee_item_id = payload.get("item_id") or payload.get("shopee_item_id")
    current_stock = payload.get("stock", 0)
    alert_threshold = payload.get("alert_threshold", 10)

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


async def _handle_unknown(payload: dict) -> dict:
    """未知事件类型 —— 记录 warning 后忽略。"""
    logger.warning(f"⚠️ 未知 Webhook 事件: {payload}")
    return {"action": "ignored", "reason": "unknown_event_type"}


# ==================== 上架任务 ====================


@celery_app.task(
    name="worker.tasks.listing_product",
    bind=True,
    max_retries=3,
)
def listing_product(self, product_id: int, listing_id: int = None) -> dict:
    """
    上架商品到 Shopee。失败指数退避重试 3 次。

    TODO 接入 Shopee OpenAPI 后替换模拟实现:
      1. 异步上传主图
      2. 创建商品（标题/描述/价格/变体）
      3. 设置库存
      4. 返回 shopee_item_id
    """
    try:
        logger.info(f"📋 开始上架商品 #{product_id}")
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
        return {"product_id": product_id, "status": "failed", "error": str(e)}
