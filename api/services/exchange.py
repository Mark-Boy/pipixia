"""
汇率服务 — 获取实时 CNY/THB 汇率

支持:
1. exchangerate API（免费，无需 key）
2. 本地缓存（避免频繁请求）
3. 硬编码回退（API 不可用时）
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional

from api.config import get_settings
from api.services.cache import cache_get, cache_set

settings = get_settings()
logger = logging.getLogger(__name__)

# 汇率缓存 TTL: 1 小时
EXCHANGE_CACHE_TTL = 3600
EXCHANGE_RATE_KEY = "exchange:CNY_THB"

# 硬编码回退汇率
DEFAULT_RATE = 5.0


def _get_cached_rate() -> Optional[float]:
    """从缓存获取汇率"""
    cached = cache_get(EXCHANGE_RATE_KEY)
    if cached:
        try:
            data = json.loads(cached)
            rate = data.get("rate")
            fetched_at = data.get("fetched_at", 0)
            # 检查缓存是否过期（双重检查）
            if time.time() - fetched_at < EXCHANGE_CACHE_TTL:
                logger.debug(f"汇率缓存命中: 1 CNY = {rate} THB")
                return rate
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
    return None


def _set_cached_rate(rate: float) -> None:
    """缓存汇率"""
    data = json.dumps({
        "rate": rate,
        "fetched_at": time.time(),
        "source": "exchangerate-api",
    })
    cache_set(EXCHANGE_RATE_KEY, data, ttl=EXCHANGE_CACHE_TTL)


def fetch_exchange_rate() -> float:
    """
    获取实时 CNY → THB 汇率
    
    优先级:
    1. 内存缓存（最快）
    2. Redis 缓存
    3. 远程 API
    4. 硬编码回退
    """
    # 检查缓存
    cached = _get_cached_rate()
    if cached:
        return cached

    # 调用远程 API
    try:
        rate = _fetch_from_api()
        if rate and rate > 0:
            _set_cached_rate(rate)
            logger.info(f"汇率获取成功: 1 CNY = {rate} THB")
            return rate
    except Exception as e:
        logger.warning(f"汇率 API 请求失败: {e}")

    # 回退到硬编码
    logger.warning(f"使用默认汇率: 1 CNY = {DEFAULT_RATE} THB")
    return DEFAULT_RATE


def _fetch_from_api() -> Optional[float]:
    """从 exchangerate API 获取汇率"""
    import httpx

    api_url = "https://api.exchangerate-api.com/v4/latest/CNY"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(api_url)
            response.raise_for_status()
            data = response.json()
            thb_rate = data.get("rates", {}).get("THB")
            if thb_rate:
                return round(thb_rate, 4)
    except Exception as e:
        logger.error(f"汇率 API 调用失败: {e}")

    return None


def get_exchange_rate() -> dict:
    """获取汇率信息（含元数据）"""
    rate = fetch_exchange_rate()
    return {
        "currency_pair": "CNY/THB",
        "rate": rate,
        "inverse_rate": round(1 / rate, 4) if rate > 0 else 0,
        "cached": _get_cached_rate() is not None,
        "last_updated": None,  # 简化版
    }


def convert_cny_to_thb(amount_cny: float) -> float:
    """CNY → THB 转换"""
    rate = fetch_exchange_rate()
    return round(amount_cny * rate, 2)


def convert_thb_to_cny(amount_thb: float) -> float:
    """THB → CNY 转换"""
    rate = fetch_exchange_rate()
    return round(amount_thb / rate, 2)
