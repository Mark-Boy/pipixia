"""
拼多多爬虫代理路由 — 后端代理请求拼多多 API，解决 CORS + 反爬问题

核心策略：
1. 使用 Playwright 浏览器模拟用户搜索（因为搜索结果通过异步加载）
2. 从页面中提取 __CHUNK_DATA__ 中的商品数据
3. 支持搜索和商品详情两种模式
4. 在线程池中运行同步 Playwright API，避免与 asyncio 冲突
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import re
from typing import Optional
from fastapi import APIRouter, Query, HTTPException
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pdd", tags=["Pinduoduo Crawler Proxy"])

# 线程池用于运行同步 Playwright 调用
_pdd_executor = ThreadPoolExecutor(max_workers=2)


def _parse_pdd_price(price_val) -> float:
    """解析拼多多价格（可能是分或元）"""
    if price_val is None:
        return 0.0
    try:
        num = float(price_val)
        return num / 100 if num > 100 else num
    except (ValueError, TypeError):
        return 0.0


def _do_search_sync(keyword: str, page_size: int) -> list:
    """同步执行拼多多搜索（在线程池中运行）"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("Playwright 未安装")
        return []

    all_items = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Linux; Android 14; Pixel 8) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Mobile Safari/537.36"
            ),
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN',
        )
        page = context.new_page()

        # 忽略拼多多后台请求失败（phantom session、本地端口等）
        page.on("requestfailed", lambda req: logger.debug(f"请求失败(忽略): {req.url}"))

        try:
            # 先访问首页获取 cookie
            logger.info("正在加载拼多多首页...")
            page.goto('https://mobile.yangkeduo.com/', wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(2000)

            # 执行搜索
            search_url = f"https://mobile.yangkeduo.com/search.html?search_key={keyword}"
            logger.info(f"正在搜索: {keyword}")
            page.goto(search_url, wait_until='domcontentloaded', timeout=30000)

            # 等待异步数据加载完成
            try:
                page.wait_for_function(
                    "() => { const gd = window.__CHUNK_DATA__?.['goodsListStore']?.data; return gd && gd.goods && gd.goods.length > 0; }",
                    timeout=15000,
                )
            except Exception as e:
                logger.warning(f"等待商品数据加载超时: {e}")
                return []

            goods_data = page.evaluate(
                "() => { const gd = window.__CHUNK_DATA__?.['goodsListStore']?.data; return gd && gd.goods ? gd.goods : []; }"
            )

            if not isinstance(goods_data, list):
                logger.warning("goods_data 不是列表")
                return []

            items = []
            for g in goods_data:
                if not isinstance(g, dict):
                    continue

                goods_id = str(g.get('goods_id', '') or g.get('item_id', ''))
                if not goods_id:
                    continue

                group = g.get('group', {})
                if not isinstance(group, dict):
                    group = {}

                normal_price = g.get('normal_price', 0) or 0
                group_price = group.get('price', 0) or 0
                final_price = group_price if group_price > 0 else normal_price

                item = {
                    'goods_id': goods_id,
                    'goods_name': g.get('goods_name', g.get('item_name', '')),
                    'normal_price': normal_price,
                    'group_price': group_price,
                    'final_price_cny': _parse_pdd_price(final_price),
                    'cnt': g.get('cnt', g.get('sales_hint', 0)),
                    'thumb_url': g.get('thumb_url', ''),
                    'hd_url': g.get('hd_url', ''),
                    'slide_image_urls': g.get('slide_image_urls', []) or [],
                    'detail_url': f"https://mobile.yangkeduo.com/goods.html?goods_id={goods_id}",
                }
                items.append(item)

            all_items.extend(items)

            # 如果第一页结果不足，尝试翻页
            if len(all_items) < page_size:
                for p_num in range(2, min(page_size // 20 + 2, 5)):
                    try:
                        next_url = f"https://mobile.yangkeduo.com/search.html?search_key={keyword}&page={p_num}"
                        page.goto(next_url, wait_until='domcontentloaded', timeout=15000)
                        page.wait_for_timeout(2000)
                        more_goods = page.evaluate(
                            "() => { const gd = window.__CHUNK_DATA__?.['goodsListStore']?.data; return gd && gd.goods ? gd.goods : []; }"
                        )
                        if not more_goods or not isinstance(more_goods, list):
                            break
                        for g in more_goods:
                            if not isinstance(g, dict):
                                continue
                            goods_id = str(g.get('goods_id', '') or g.get('item_id', ''))
                            if not goods_id:
                                continue
                            group = g.get('group', {})
                            if not isinstance(group, dict):
                                group = {}
                            normal_price = g.get('normal_price', 0) or 0
                            group_price = group.get('price', 0) or 0
                            final_price = group_price if group_price > 0 else normal_price
                            item = {
                                'goods_id': goods_id,
                                'goods_name': g.get('goods_name', g.get('item_name', '')),
                                'normal_price': normal_price,
                                'group_price': group_price,
                                'final_price_cny': _parse_pdd_price(final_price),
                                'cnt': g.get('cnt', g.get('sales_hint', 0)),
                                'thumb_url': g.get('thumb_url', ''),
                                'hd_url': g.get('hd_url', ''),
                                'slide_image_urls': g.get('slide_image_urls', []) or [],
                                'detail_url': f"https://mobile.yangkeduo.com/goods.html?goods_id={goods_id}",
                            }
                            all_items.append(item)
                            if len(all_items) >= page_size:
                                break
                        if len(all_items) >= page_size:
                            break
                    except Exception as e:
                        logger.debug(f"翻页 {p_num} 失败: {e}")
                        break

            total = len(all_items)
            all_items = all_items[:page_size]
            logger.info(f"搜索 '{keyword}' 成功，共找到 {total} 个商品")

        finally:
            browser.close()

    return all_items


def _do_item_detail_sync(item_id: str) -> dict:
    """同步执行商品详情获取（在线程池中运行）"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("Playwright 未安装")
        raise HTTPException(status_code=500, detail="Playwright 未安装")

    detail_url = f"https://mobile.yangkeduo.com/goods.html?goods_id={item_id}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Linux; Android 14; Pixel 8) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Mobile Safari/537.36"
            ),
            viewport={'width': 1920, 'height': 1080},
            locale='zh-CN',
        )
        page = context.new_page()

        # 忽略拼多多后台请求失败（phantom session、本地端口等）
        page.on("requestfailed", lambda req: logger.debug(f"请求失败(忽略): {req.url}"))

        try:
            page.goto('https://mobile.yangkeduo.com/', wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(2000)

            logger.info(f"正在获取商品详情: {item_id}")
            page.goto(detail_url, wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(3000)

            item_data = page.evaluate(
                """() => {
                    const gd = window.__CHUNK_DATA__?.['goodsDetailStore']?.data;
                    if (gd) return { type: 'chunk', data: gd };
                    try {
                        const scripts = document.querySelectorAll('script');
                        for (const s of scripts) {
                            const t = s.textContent;
                            if (t.includes('rawData')) {
                                const m = t.match(/window\\.rawData\\s*=\\s*(\\{.*?\\});\\s*window\\.__SSR__/);
                                if (m) {
                                    const data = JSON.parse(m[1]);
                                    const store = data.stores?.store;
                                    if (store) return { type: 'rawData', data: store };
                                }
                            }
                        }
                    } catch(e) {}
                    return { type: 'none' };
                }"""
            )

            def _extract_result(data_dict):
                goods_info = data_dict.get('goodsInfo', {}) or data_dict.get('goods', {}) or {}
                group = goods_info.get('group', {})
                if not isinstance(group, dict):
                    group = {}
                normal_price = goods_info.get('normal_price', 0) or 0
                group_price = group.get('price', 0) or 0
                final_price = group_price if group_price > 0 else normal_price
                slide_images = goods_info.get('slide_image_urls', []) or []
                if isinstance(slide_images, dict):
                    slide_images = [v for v in slide_images.values() if v]
                return {
                    'goods_id': str(goods_info.get('goods_id', item_id)),
                    'goods_name': goods_info.get('goods_name', goods_info.get('item_name', '')),
                    'normal_price': normal_price,
                    'group_price': group_price,
                    'final_price_cny': _parse_pdd_price(final_price),
                    'cnt': goods_info.get('cnt', goods_info.get('sales_hint', 0)),
                    'thumb_url': goods_info.get('thumb_url', ''),
                    'hd_url': goods_info.get('hd_url', ''),
                    'slide_image_urls': slide_images[:10],
                    'detail_desc': goods_info.get('detail_desc', goods_info.get('description', '')),
                    'sku_list': goods_info.get('sku_list', []) or [],
                    'batch_price_list': goods_info.get('batch_price_list', []) or [],
                }

            if item_data.get('type') == 'chunk':
                return _extract_result(item_data['data'])
            elif item_data.get('type') == 'rawData':
                return _extract_result(item_data['data'])
            else:
                # 降级：从 DOM 提取
                title = ""
                try:
                    title = page.locator('xpath=//h1[contains(@class, "title") or contains(@class, "goods-name")]').first.text_content()
                except Exception:
                    pass
                price_text = ""
                try:
                    price_text = page.locator('xpath=//*[contains(@class, "price") or contains(@class, "goods-price")]//text()').first.text_content()
                except Exception:
                    pass
                return {
                    'goods_id': item_id,
                    'goods_name': title or '',
                    'final_price_cny': _parse_pdd_price(price_text),
                    'slide_image_urls': [],
                }
        finally:
            browser.close()


@router.get("/search")
async def pdd_search(
    keyword: str = Query(..., description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=50, description="每页数量"),
):
    """
    搜索拼多多商品（通过 Playwright 浏览器模拟）

    由于拼多多搜索结果通过异步加载，无法直接通过 HTTP API 获取，
    需要使用浏览器渲染页面后提取数据。
    """
    try:
        loop = asyncio.get_running_loop()
        items = await loop.run_in_executor(
            _pdd_executor, _do_search_sync, keyword, page_size
        )
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        raise HTTPException(status_code=502, detail=f"搜索失败: {str(e)}")

    return {
        'total': len(items),
        'page': page,
        'page_size': page_size,
        'keyword': keyword,
        'goods': items,
    }


@router.get("/item/detail")
async def pdd_item_detail(
    item_id: str = Query(..., description="商品 ID (goods_id / item_id)"),
):
    """
    获取拼多多商品详情（通过 Playwright 浏览器模拟）
    """
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            _pdd_executor, _do_item_detail_sync, item_id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"商品详情获取失败: {e}")
        raise HTTPException(status_code=502, detail=f"商品详情获取失败: {str(e)}")

    return result
