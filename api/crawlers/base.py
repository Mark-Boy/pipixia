"""
爬虫基类 — 封装 Playwright 浏览器管理、SSRF 校验、反爬策略
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class ProductInfo:
    """商品信息数据结构"""
    title_zh: str = ""
    title_th: Optional[str] = None
    description_zh: Optional[str] = None
    price_cny: Optional[float] = None
    cost_cny: Optional[float] = None
    images_urls: list[str] = field(default_factory=list)
    specs: dict[str, str] = field(default_factory=dict)
    source_platform: str = ""
    source_item_id: str = ""
    raw_url: str = ""
    error_message: Optional[str] = None


# SSRF 白名单域名
SSRF_WHITELIST = {
    "1688.com", "www.1688.com", "detail.1688.com", "m.1688.com",
    "mobile.yangkeduo.com", "m.pinduoduo.com", "pinduoduo.com",
}


def is_safe_url(url: str) -> bool:
    """SSRF 防护：校验 URL 是否在白名单内"""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        return hostname in SSRF_WHITELIST
    except Exception:
        return False


class BaseCrawler(ABC):
    """爬虫基类 — 所有平台爬虫继承此类"""

    platform: str = "base"  # 子类覆盖
    _browser = None
    _page = None

    @abstractmethod
    def parse_url(self, url: str) -> tuple[str, str]:
        """
        解析 URL，返回 (platform, item_id)
        """
        ...

    @abstractmethod
    async def fetch_product(self, url: str) -> ProductInfo:
        """
        抓取商品详情
        """
        ...

    async def _ensure_browser(self):
        """懒加载 Playwright 浏览器实例"""
        from playwright.async_api import async_playwright

        if self._browser is None:
            pw = await async_playwright().start()
            self._browser = await pw.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                ],
            )
            logger.info("Playwright 浏览器已启动")
        return self._browser

    async def _get_page(self, url: str):
        """获取浏览器 page 并导航到目标 URL"""
        browser = await self._ensure_browser()
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
        )
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        # 等待关键元素加载
        await page.wait_for_timeout(2000)
        return page

    async def close(self):
        """关闭浏览器"""
        if self._browser:
            await self._browser.close()
            self._browser = None
            logger.info("Playwright 浏览器已关闭")

    def extract_price(self, text: str) -> Optional[float]:
        """从文本中提取价格数字"""
        match = re.search(r"[\d,]+\.?\d*", text.replace(",", ""))
        if match:
            return float(match.group())
        return None

    def clean_text(self, text: str) -> str:
        """清洗文本：去除多余空白和特殊字符"""
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"[^\w\s\u4e00-\u9fff\u0e00-\u0e7f]", " ", text)
        return text.strip()
