"""
Shopee 自动同步定时调度器

每分钟执行一次:
1. 检查待上架商品，自动上架
2. 同步库存到 Shopee
3. 同步商品列表 (每 5 分钟)
4. 生成进度报告

不包含报关功能
"""

import logging
import asyncio
import time
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import async_sessionmaker

from api.services.shopee_sync import ShopeeSyncService
from api.services.shopee_v2 import create_shopee_client
from api.services.crypto import decrypt_aes256
from api.config import get_settings
from api.database import async_session

logger = logging.getLogger(__name__)
settings = get_settings()


class ShopeeScheduler:
    """
    Shopee 定时同步调度器

    执行频率:
    - 自动上架: 每分钟
    - 库存同步: 每分钟
    - 商品列表同步: 每 5 分钟
    - 进度报告: 每分钟 (Telegram / 控制台)
    """

    def __init__(self):
        self.running = False
        self.last_sync_time: Optional[datetime] = None
        self.stats = {
            "total_runs": 0,
            "total_products_synced": 0,
            "total_products_failed": 0,
            "last_error": None,
            "last_run_at": None,
        }
        self.sync_interval = 60  # 秒
        self.listing_interval = 60  # 自动上架间隔
        self.sync_list_interval = 300  # 商品列表同步间隔 (5分钟)
        self.last_listing_sync = datetime.utcnow()
        self._last_report = datetime.utcnow()

    async def run_cycle(self):
        """执行一个同步周期"""
        self.stats["total_runs"] += 1
        self.stats["last_run_at"] = datetime.utcnow().isoformat()
        start_time = time.time()

        logger.info("=" * 60)
        logger.info(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Shopee 同步周期开始")

        try:
            # 1. 自动上架待处理商品
            await self._auto_list()

            # 2. 同步库存
            await self._sync_stock()

            # 3. 同步商品列表 (每 5 分钟)
            await self._sync_product_list()

            # 4. 获取状态
            status = await self._get_status()

            elapsed = time.time() - start_time
            status["elapsed_seconds"] = round(elapsed, 2)
            status["stats"] = self.stats

            # 5. 发送进度报告
            await self._send_report(status)

            self.stats["last_error"] = None
            logger.info(f"同步周期完成，耗时 {elapsed:.1f}s")

        except Exception as e:
            self.stats["last_error"] = str(e)
            logger.error(f"同步周期失败: {e}", exc_info=True)
            await self._send_error_report(str(e))

    async def _auto_list(self):
        """自动上架待处理商品"""
        try:
            async with async_session() as db:
                service = ShopeeSyncService(db)
                result = service.auto_list_all(max_products=20, marketplace="shopee_th")

                if result.get("success", 0) > 0:
                    self.stats["total_products_synced"] += result.get("success", 0)
                    logger.info(f"自动上架: {result['success']} 个商品成功")
                if result.get("failed", 0) > 0:
                    self.stats["total_products_failed"] += result.get("failed", 0)
                    logger.warning(f"自动上架: {result['failed']} 个商品失败")

        except Exception as e:
            logger.error(f"自动上架失败: {e}")

    async def _sync_stock(self):
        """同步库存"""
        try:
            async with async_session() as db:
                service = ShopeeSyncService(db)
                result = service.auto_update_stock(shop_id=1, marketplace="shopee_th")
                if result.get("updated", 0) > 0:
                    logger.info(f"库存同步: {result['updated']} 个商品库存更新")

        except Exception as e:
            logger.error(f"库存同步失败: {e}")

    async def _sync_product_list(self):
        """同步商品列表 (每 5 分钟)"""
        if (datetime.utcnow() - self.last_listing_sync).seconds < self.sync_list_interval:
            return

        self.last_listing_sync = datetime.utcnow()

        try:
            async with async_session() as db:
                service = ShopeeSyncService(db)
                result = service.sync_product_list(shop_id=1, marketplace="shopee_th")
                if result.get("total_synced", 0) > 0:
                    logger.info(f"商品列表同步: {result['total_synced']} 个商品")

        except Exception as e:
            logger.error(f"商品列表同步失败: {e}")

    async def _get_status(self) -> dict:
        """获取同步状态"""
        try:
            async with async_session() as db:
                service = ShopeeSyncService(db)
                return service.get_sync_status()
        except Exception as e:
            logger.error(f"获取状态失败: {e}")
            return {"error": str(e)}

    async def _send_report(self, status: dict):
        """发送进度报告"""
        report = self._format_report(status)
        logger.info(report)

        # Telegram 告警 (可选)
        if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
            await self._send_telegram(report)

    def _format_report(self, status: dict) -> str:
        """格式化进度报告"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        pending = status.get("pending_products", 0)
        listed = status.get("listed_products", 0)
        failed = status.get("failed_products", 0)
        shops = status.get("active_shops", 0)
        elapsed = status.get("elapsed_seconds", 0)

        report_lines = [
            f"📊 Shopee 同步进度报告 [{now}]",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"⏱️  运行时长: {elapsed}s",
            f"📦 待上架商品: {pending} 个",
            f"✅ 已上架商品: {listed} 个",
            f"❌ 失败商品: {failed} 个",
            f"🏪 活跃店铺: {shops} 个",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]

        if self.stats["last_error"]:
            report_lines.append(f"🔴 上次错误: {self.stats['last_error']}")
        else:
            report_lines.append("🟢 上次运行正常")

        report_lines.append(f"📈 累计同步: {self.stats['total_products_synced']} 个")
        report_lines.append(f"💥 累计失败: {self.stats['total_products_failed']} 个")
        report_lines.append(f"🔄 总运行次数: {self.stats['total_runs']}")

        return "\n".join(report_lines)

    async def _send_telegram(self, message: str):
        """发送 Telegram 报告"""
        import httpx

        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": settings.TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    logger.info("Telegram 报告发送成功")
        except Exception as e:
            logger.error(f"Telegram 发送失败: {e}")

    async def _send_error_report(self, error: str):
        """发送错误报告"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        msg = (
            f"🔴 Shopee 同步错误 [{now}]\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"❌ 错误信息: {error}\n"
            f"🔄 已运行 {self.stats['total_runs']} 次\n"
            f"📦 累计同步 {self.stats['total_products_synced']} 个商品"
        )
        logger.warning(msg)
        if settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID:
            await self._send_telegram(msg)

    async def start(self):
        """启动调度器"""
        self.running = True
        logger.info("🚀 Shopee 同步调度器启动")
        logger.info(f"  - 自动上架间隔: {self.listing_interval}s")
        logger.info(f"  - 库存同步间隔: {self.sync_interval}s")
        logger.info(f"  - 商品列表同步间隔: {self.sync_list_interval}s")
        logger.info(f"  - 不包含报关功能")

        while self.running:
            try:
                await self.run_cycle()
            except Exception as e:
                logger.error(f"调度器异常: {e}", exc_info=True)

            # 等待下一个周期
            await asyncio.sleep(self.sync_interval)

    def stop(self):
        """停止调度器"""
        self.running = False
        logger.info("Shopee 同步调度器停止")

    def get_stats(self) -> dict:
        """获取调度器统计"""
        return {
            "running": self.running,
            **self.stats,
            "last_report": self._format_report({
                "pending_products": 0,
                "listed_products": 0,
                "failed_products": 0,
                "active_shops": 0,
            }),
        }


# 全局调度器实例
_scheduler: Optional[ShopeeScheduler] = None


def get_scheduler() -> ShopeeScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = ShopeeScheduler()
    return _scheduler


def start_scheduler():
    """启动调度器 (后台任务)"""
    scheduler = get_scheduler()
    asyncio.create_task(scheduler.start())
    logger.info("Shopee 同步调度器已在后台启动")
