"""
1688 商品爬虫 — 抓取阿里巴巴 1688 商品详情

支持 URL 格式：
- https://detail.1688.com/offer/{id}.html
- https://detail.1688.com/offer/{id}.htm
- https://m.1688.com/offer/detail/{id}.html
- https://m.1688.com/offer/{id}.html
"""

import logging
import re
from typing import Optional

from .base import BaseCrawler, ProductInfo, is_safe_url

logger = logging.getLogger(__name__)


class Alibaba1688Crawler(BaseCrawler):
    """1688 商品详情页爬虫"""

    platform = "1688"

    # 1688 URL 模式
    URL_PATTERNS = [
        r"https?://detail\.1688\.com/offer/(\d+)",
        r"https?://m\.1688\.com/offer/(detail/)?(\d+)",
        r"https?://(www\.)?1688\.com/offer/(\d+)",
        r"https?://(www\.)?1688\.com/offerdetail/(\d+)",
    ]

    def parse_url(self, url: str) -> tuple[str, str]:
        """解析 1688 URL，返回 (platform, item_id)"""
        if not is_safe_url(url):
            raise ValueError(f"SSRF 防护：URL 不在白名单中: {url}")

        for pattern in self.URL_PATTERNS:
            match = re.search(pattern, url)
            if match:
                # 取最后一个捕获组作为 item_id
                item_id = match.groups()[-1]
                return self.platform, item_id

        raise ValueError(f"无法解析 1688 URL: {url}")

    async def fetch_product(self, url: str) -> ProductInfo:
        """
        抓取 1688 商品详情

        策略：
        1. 尝试通过 API 接口获取 JSON 数据（更快更准）
        2. 如果 API 不可用，降级到 HTML 解析
        """
        info = ProductInfo(
            source_platform=self.platform,
            raw_url=url,
        )

        # 提取 item_id
        _, item_id = self.parse_url(url)
        info.source_item_id = item_id

        # 优先尝试 API 方式（1688 有内部 JSON API）
        try:
            info = await self._fetch_via_api(url, item_id)
            if info.title_zh:
                logger.info(f"1688 商品抓取成功 (API): {item_id} — {info.title_zh}")
                return info
        except Exception as e:
            logger.debug(f"1688 API 抓取失败: {e}，降级到 HTML 解析")

        # 降级：HTML 解析
        try:
            info = await self._fetch_via_html(url, item_id)
            if info.title_zh:
                logger.info(f"1688 商品抓取成功 (HTML): {item_id} — {info.title_zh}")
                return info
        except Exception as e:
            logger.error(f"1688 HTML 抓取失败: {e}")
            info.error_message = str(e)

        return info

    async def _fetch_via_api(self, url: str, item_id: str) -> ProductInfo:
        """
        通过 1688 内部 API 获取商品数据

        1688 有 h5api 接口返回 JSON 格式数据，比 HTML 解析更可靠
        """
        import httpx

        # 1688 h5api 接口
        api_url = f"https://h5api.m.1688.com/h5/mtop.alibaba.linkplus.product.detail.get/2.0/"

        params = {
            "data": (
                '{"offerId":"' + item_id + '",'
                '"qty":"1",'
                '"isPreSale":"false",'
                '"platformId":"linkplus",'
                '"isRetail":"false"}'
            ),
        }

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
            ),
            "Referer": "https://m.1688.com/",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(api_url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        # 解析 API 返回
        result = data.get("data", {})
        product_data = result.get("productDetailResponse", {}).get("data", {}) or {}

        info = ProductInfo(source_platform=self.platform, source_item_id=item_id, raw_url=url)

        # 标题
        info.title_zh = self.clean_text(
            product_data.get("title", "") or product_data.get("subject", "")
        )

        # 价格（取最低批发价）
        price_data = product_data.get("priceData", {})
        if price_data:
            prices = price_data.get("prices", [])
            if prices:
                # prices 可能是 [{"price": "10.00", ...}, ...]
                if isinstance(prices, list) and prices:
                    try:
                        info.price_cny = float(prices[0].get("price", 0))
                    except (ValueError, TypeError):
                        pass
                elif isinstance(price_data.get("price"), (int, float)):
                    info.price_cny = float(price_data["price"])

        # 成本价（通常取一手价）
        cost_data = product_data.get("oneStopService", {})
        if cost_data and isinstance(cost_data, dict):
            cost_price = cost_data.get("price")
            if cost_price:
                try:
                    info.cost_cny = float(cost_price)
                except (ValueError, TypeError):
                    pass

        # 图片列表
        image_urls = product_data.get("imageUrl", [])
        if isinstance(image_urls, str):
            image_urls = [image_urls]
        if image_urls:
            info.images_urls = [
                img.replace("//", "https://") if img.startswith("//") else img
                for img in image_urls
                if img
            ][:5]  # 最多 5 张

        # 详情描述
        desc = product_data.get("desc", "") or product_data.get("description", "")
        if desc:
            info.description_zh = self.clean_text(desc[:4000])

        # 规格参数
        attrs = product_data.get("attrs", [])
        if isinstance(attrs, list):
            for attr in attrs[:20]:
                if isinstance(attr, dict) and attr.get("k") and attr.get("v"):
                    info.specs[attr["k"]] = attr["v"]

        if not info.title_zh:
            raise ValueError("API 返回数据中无标题")

        return info

    async def _fetch_via_html(self, url: str, item_id: str) -> ProductInfo:
        """
        通过 HTML 解析获取 1688 商品数据

        当 API 不可用时使用此方法
        """
        page = await self._get_page(url)

        info = ProductInfo(source_platform=self.platform, source_item_id=item_id, raw_url=url)

        # 尝试从页面 JSON-LD 或全局变量中提取数据
        # 1688 通常在页面中嵌入 __INITIAL_STATE__ 或类似变量
        js_data = await page.evaluate("""
            () => {
                // 尝试多种可能的全局变量
                const keys = [
                    '__INITIAL_STATE__', '__NEXT_DATA__',
                    'productInfo', 'offerData', 'window.__INITIAL_STATE__'
                ];
                for (const key of keys) {
                    try {
                        const val = eval(key);
                        if (val && typeof val === 'object') return JSON.stringify(val);
                    } catch(e) {}
                }
                return null;
            }
        """)

        if js_data:
            import json
            try:
                data = json.loads(js_data)
                # 尝试从嵌套数据中提取
                info.title_zh = self._extract_from_json(data, ["title", "subject", "productTitle"])
                info.price_cny = self._extract_price_from_json(data, ["price", "minPrice", "offerPrice"])
                images = self._extract_from_json(data, ["imageUrl", "images", "pictures"])
                if isinstance(images, list):
                    info.images_urls = [
                        img.replace("//", "https://") if img.startswith("//") else img
                        for img in images[:5]
                    ]
            except json.JSONDecodeError:
                pass

        # 降级：直接从 DOM 元素提取
        if not info.title_zh:
            title_el = await page.locator(
                'xpath=//h1[contains(@class, "title") or contains(@class, "product-title") or contains(@class, "offer-title")]'
            ).first.text_content()
            if title_el:
                info.title_zh = self.clean_text(title_el)

        if not info.price_cny:
            price_el = await page.locator(
                'xpath=//*[contains(@class, "price") or contains(@class, "money") or contains(@class, "offer-price")]//text()'
            ).first.text_content()
            if price_el:
                info.price_cny = self.extract_price(price_el)

        # 图片
        if not info.images_urls:
            imgs = await page.locator(
                'xpath=//img[contains(@src, "alibaba.com") or contains(@src, "1688.com")]'
            ).all()
            for img in imgs[:5]:
                src = await img.get_attribute("src")
                if src and "alibaba" in src:
                    info.images_urls.append(src.replace("//", "https://"))

        # 描述
        desc_el = await page.locator(
            'xpath=//div[contains(@class, "detail") or contains(@class, "description") or contains(@class, "offer-detail")]'
        ).first.text_content()
        if desc_el:
            info.description_zh = self.clean_text(desc_el[:4000])

        await page.close()

        if not info.title_zh:
            raise ValueError("HTML 解析未找到标题")

        return info

    def _extract_from_json(self, data: dict, keys: list[str]) -> Optional[str]:
        """从嵌套 JSON 中提取字段"""
        if not isinstance(data, dict):
            return None
        for key in keys:
            if key in data and isinstance(data[key], str) and data[key].strip():
                return data[key].strip()
        # 递归搜索
        for value in data.values():
            if isinstance(value, dict):
                result = self._extract_from_json(value, keys)
                if result:
                    return result
        return None

    def _extract_price_from_json(self, data: dict, keys: list[str]) -> Optional[float]:
        """从嵌套 JSON 中提取价格"""
        if not isinstance(data, dict):
            return None
        for key in keys:
            if key in data:
                val = data[key]
                if isinstance(val, (int, float)):
                    return float(val)
                if isinstance(val, str):
                    return self.extract_price(val)
        for value in data.values():
            if isinstance(value, dict):
                result = self._extract_price_from_json(value, keys)
                if result:
                    return result
        return None
