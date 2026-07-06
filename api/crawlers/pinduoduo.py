"""
拼多多商品爬虫 — 抓取拼多多商品详情

支持 URL 格式：
- https://mobile.yangkeduo.com/proxy/apis/v5/item/search?page=&page_size=20&item_ids=xxx
- https://mobile.yangkeduo.com/proxy/apis/v5/item/detail?item_id=xxx
- https://mobile.yangkeduo.com/proxy/apis/v5/item/groupon?item_id=xxx
- 各种 pinduoduo.com 短链
"""

import logging
import re
import json
from typing import Optional

from .base import BaseCrawler, ProductInfo, is_safe_url

logger = logging.getLogger(__name__)


class PinduoduoCrawler(BaseCrawler):
    """拼多多商品详情页爬虫"""

    platform = "pdd"

    # 拼多多 URL 模式
    URL_PATTERNS = [
        r"[?&]item_id=(\d+)",
        r"[?&]id=(\d+)",
        r"/proxy/apis/v5/item/\w+\?item_id=(\d+)",
        r"/proxy/apis/v5/item/\w+/(\d+)",
    ]

    def parse_url(self, url: str) -> tuple[str, str]:
        """解析拼多多 URL，返回 (platform, item_id)"""
        if not is_safe_url(url):
            raise ValueError(f"SSRF 防护：URL 不在白名单中: {url}")

        # 优先匹配 item_id
        match = re.search(r"[?&]item_id=(\d+)", url)
        if match:
            return self.platform, match.group(1)

        # 其次匹配 id=
        match = re.search(r"[?&]id=(\d+)", url)
        if match:
            return self.platform, match.group(1)

        # 最后匹配路径中的数字
        match = re.search(r"/(\d+)", url)
        if match:
            return self.platform, match.group(1)

        raise ValueError(f"无法解析拼多多 URL: {url}")

    async def fetch_product(self, url: str) -> ProductInfo:
        """
        抓取拼多多商品详情

        策略：
        1. 尝试通过 API 接口获取 JSON 数据（yangkedoo API）
        2. 如果 API 不可用，降级到 HTML 解析
        """
        info = ProductInfo(
            source_platform=self.platform,
            raw_url=url,
        )

        # 提取 item_id
        _, item_id = self.parse_url(url)
        info.source_item_id = item_id

        # 优先尝试 API 方式
        try:
            info = await self._fetch_via_api(item_id, url)
            if info.title_zh:
                logger.info(f"拼多多商品抓取成功 (API): {item_id} — {info.title_zh}")
                return info
        except Exception as e:
            logger.debug(f"拼多多 API 抓取失败: {e}，降级到 HTML 解析")

        # 降级：HTML 解析
        try:
            info = await self._fetch_via_html(url, item_id)
            if info.title_zh:
                logger.info(f"拼多多商品抓取成功 (HTML): {item_id} — {info.title_zh}")
                return info
        except Exception as e:
            logger.error(f"拼多多 HTML 抓取失败: {e}")
            info.error_message = str(e)

        return info

    async def _fetch_via_api(self, item_id: str, original_url: str) -> ProductInfo:
        """
        通过拼多多内部 API 获取商品数据

        拼多多的移动端 API 返回 JSON 格式数据
        """
        import httpx

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 14; Pixel 8) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Mobile Safari/537.36"
            ),
            "Accept": "application/json",
            "Referer": "https://mobile.yangkeduo.com/",
        }

        # 尝试多个 API 端点
        api_endpoints = [
            f"https://mobile.yangkeduo.com/proxy/apis/v5/item/detail?item_id={item_id}",
            f"https://mobile.yangkeduo.com/proxy/apis/v5/item/groupon?item_id={item_id}",
            f"https://mobile.yangkeduo.com/proxy/apis/v5/item/info?item_id={item_id}",
        ]

        for api_url in api_endpoints:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(api_url, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        info = self._parse_api_response(data, item_id, original_url)
                        if info.title_zh:
                            return info
            except Exception as e:
                logger.debug(f"API 端点 {api_url} 失败: {e}")
                continue

        raise ValueError("所有 API 端点均失败")

    def _parse_api_response(self, data: dict, item_id: str, url: str) -> ProductInfo:
        """解析拼多多 API 返回的数据"""
        info = ProductInfo(
            source_platform=self.platform,
            source_item_id=item_id,
            raw_url=url,
        )

        # 尝试多种可能的数据路径
        # 路径1: data.item / data.goods_info
        item_data = (
            data.get("item", {}) or
            data.get("goods_info", {}) or
            data.get("groupon", {}) or
            data.get("result", {}).get("item", {}) or
            data.get("result", {}).get("goods_info", {})
        )

        if not item_data and isinstance(data, dict):
            # 扁平化搜索
            item_data = self._find_item_data(data)

        if not item_data:
            return info

        # 标题
        info.title_zh = self.clean_text(
            item_data.get("item_name", "") or
            item_data.get("goods_name", "") or
            item_data.get("title", "") or
            item_data.get("group_title", "") or
            ""
        )

        # 价格
        price_data = item_data.get("price", 0) or item_data.get("normal_price", 0)
        if price_data:
            try:
                info.price_cny = float(price_data) / 100  # 拼多多以分为单位
            except (ValueError, TypeError):
                pass

        # 最低价
        min_price = item_data.get("min_group_price", 0) or item_data.get("min_normal_price", 0)
        if min_price and not info.price_cny:
            try:
                info.price_cny = float(min_price) / 100
            except (ValueError, TypeError):
                pass

        # 成本价（如果有批发价）
        wholesale_prices = item_data.get("batch_price_list", []) or item_data.get("wholesale_prices", [])
        if wholesale_prices and isinstance(wholesale_prices, list) and wholesale_prices:
            try:
                info.cost_cny = float(wholesale_prices[0].get("price", 0)) / 100
            except (ValueError, TypeError):
                pass

        # 图片列表
        image_urls = (
            item_data.get("images", {}) or
            item_data.get("slide_image_ids", []) or
            item_data.get("goods_thumbnail_urls", []) or
            item_data.get("goods_gallery_urls", [])
        )

        if isinstance(image_urls, dict):
            keys = ["main", "primary", "thumb", "main_image", "image"]
            for k in keys:
                if k in image_urls:
                    val = image_urls[k]
                    if isinstance(val, str):
                        image_urls = [val]
                        break
                    elif isinstance(val, list) and val:
                        image_urls = val
                        break
            else:
                image_urls = []

        if isinstance(image_urls, list):
            info.images_urls = [
                img if img.startswith(("http", "https")) else f"https:{img}"
                for img in image_urls[:5]
                if img
            ]

        # 描述
        desc = (
            item_data.get("detail_desc", "") or
            item_data.get("goods_desc", "") or
            item_data.get("description", "") or
            ""
        )
        if desc:
            info.description_zh = self.clean_text(desc[:4000])

        # 规格
        specs_data = item_data.get("sku_list", []) or item_data.get("spec_list", [])
        if isinstance(specs_data, list):
            for spec in specs_data[:10]:
                if isinstance(spec, dict):
                    spec_name = spec.get("spec_name", "") or spec.get("name", "")
                    spec_value = spec.get("spec_value", "") or spec.get("value", "")
                    if spec_name and spec_value:
                        info.specs[f"{spec_name}:{spec_value}"] = ""

        return info

    def _find_item_data(self, data: dict, depth: int = 0) -> Optional[dict]:
        """递归查找包含商品数据的嵌套字典"""
        if depth > 5:
            return None

        # 检查当前字典是否包含关键字段
        key_indicators = ["item_name", "goods_name", "title", "price", "images"]
        if any(k in data for k in key_indicators):
            return data

        # 递归搜索子字典
        for value in data.values():
            if isinstance(value, dict):
                result = self._find_item_data(value, depth + 1)
                if result:
                    return result
            elif isinstance(value, list) and value:
                for item in value[:3]:  # 最多检查前3个
                    if isinstance(item, dict):
                        result = self._find_item_data(item, depth + 1)
                        if result:
                            return result

        return None

    async def _fetch_via_html(self, url: str, item_id: str) -> ProductInfo:
        """
        通过 HTML 解析获取拼多多商品数据

        当 API 不可用时使用此方法
        """
        page = await self._get_page(url)

        info = ProductInfo(
            source_platform=self.platform,
            source_item_id=item_id,
            raw_url=url,
        )

        # 尝试从页面中提取 __NEXT_DATA__ 或 window.__INITIAL_STATE__
        js_data = await page.evaluate("""
            () => {
                try {
                    if (window.__INITIAL_STATE__) return JSON.stringify(window.__INITIAL_STATE__);
                    if (window.__NEXT_DATA__) return JSON.stringify(window.__NEXT_DATA__);
                    const el = document.querySelector('script[type="application/json"]');
                    if (el) return el.textContent;
                } catch(e) {}
                return null;
            }
        """)

        if js_data:
            try:
                data = json.loads(js_data)
                info.title_zh = self._extract_from_json(data, ["item_name", "goods_name", "title", "name"])
                info.price_cny = self._extract_price_from_json(data, ["price", "min_price", "normal_price"])

                images = self._extract_from_json(data, ["images", "slide_image_ids", "goods_thumbnail_urls"])
                if isinstance(images, list):
                    info.images_urls = [
                        img if img.startswith(("http", "https")) else f"https:{img}"
                        for img in images[:5]
                    ]
            except json.JSONDecodeError:
                pass

        # 降级：从 DOM 提取
        if not info.title_zh:
            title_selectors = [
                'xpath=//h1[contains(@class, "title") or contains(@class, "goods-name")]',
                'xpath=//div[contains(@class, "title")]/text()',
            ]
            for selector in title_selectors:
                try:
                    el = await page.locator(selector).first.text_content()
                    if el:
                        info.title_zh = self.clean_text(el)
                        break
                except Exception:
                    continue

        if not info.price_cny:
            try:
                price_el = await page.locator(
                    'xpath=//*[contains(@class, "price") or contains(@class, "goods-price")]//text()'
                ).first.text_content()
                if price_el:
                    info.price_cny = self.extract_price(price_el)
            except Exception:
                pass

        # 图片
        if not info.images_urls:
            try:
                imgs = await page.locator('xpath=//img[contains(@class, "goods-image") or contains(@class, "slide-img")]').all()
                for img in imgs[:5]:
                    src = await img.get_attribute("src")
                    if src:
                        info.images_urls.append(src if src.startswith(("http", "https")) else f"https:{src}")
            except Exception:
                pass

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
                    return float(val) / 100 if val > 100 else float(val)  # 可能是分
                if isinstance(val, str):
                    return self.extract_price(val)
        for value in data.values():
            if isinstance(value, dict):
                result = self._extract_price_from_json(value, keys)
                if result:
                    return result
        return None
