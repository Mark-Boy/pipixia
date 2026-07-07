"""
Redis 缓存服务 — 翻译缓存、Token 黑名单、Celery Broker

支持两种模式:
1. Redis 模式（生产/推荐）
2. 内存回退模式（开发/无 Redis 时）
"""

import json
import logging
from typing import Optional
from datetime import datetime, timedelta

from api.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# 缓存 TTL（秒）
TRANSLATION_CACHE_TTL = 86400 * 30       # 30 天
TOKEN_BLACKLIST_TTL = 604800              # 7 天（refresh token 有效期）
MAX_CACHE_SIZE = 10000                    # 内存缓存最大条目数

# 内存缓存（Redis 不可用时的回退）
_memory_cache: dict[str, tuple[str, float]] = {}  # key -> (value, expire_time)


def _get_redis_client():
    """获取 Redis 客户端（懒加载）"""
    try:
        import redis
        client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
        client.ping()
        return client
    except Exception as e:
        logger.warning(f"Redis 连接失败，使用内存缓存: {e}")
        return None


_redis_client = None


def _get_client():
    """获取 Redis 客户端（带懒加载和缓存）"""
    global _redis_client
    if _redis_client is None:
        _redis_client = _get_redis_client()
    return _redis_client


def cache_get(key: str) -> Optional[str]:
    """从缓存获取值"""
    client = _get_client()
    if client:
        try:
            return client.get(key)
        except Exception:
            pass

    # 回退到内存缓存
    return _memory_get(key)


def cache_set(key: str, value: str, ttl: int = TRANSLATION_CACHE_TTL) -> None:
    """设置缓存值"""
    client = _get_client()
    if client:
        try:
            client.setex(key, ttl, value)
            return
        except Exception:
            pass

    # 回退到内存缓存
    _memory_set(key, value, ttl)


def cache_delete(key: str) -> None:
    """删除缓存"""
    client = _get_client()
    if client:
        try:
            client.delete(key)
        except Exception:
            pass
    _memory_delete(key)


def cache_exists(key: str) -> bool:
    """检查键是否存在"""
    client = _get_client()
    if client:
        try:
            return bool(client.exists(key))
        except Exception:
            pass
    return _memory_exists(key)


# ==================== 内存缓存实现 ====================

def _memory_get(key: str) -> Optional[str]:
    if key in _memory_cache:
        value, expire_time = _memory_cache[key]
        if datetime.now().timestamp() < expire_time:
            return value
        del _memory_cache[key]
    return None


def _memory_set(key: str, value: str, ttl: int) -> None:
    global _memory_cache
    # LRU 淘汰：超出容量时删除最旧的 10%
    if len(_memory_cache) >= MAX_CACHE_SIZE:
        sorted_keys = sorted(_memory_cache.keys(), key=lambda k: _memory_cache[k][1])
        for k in sorted_keys[:MAX_CACHE_SIZE // 10]:
            del _memory_cache[k]
        logger.info(f"内存缓存已满 ({MAX_CACHE_SIZE})，淘汰了 {MAX_CACHE_SIZE // 10} 条旧记录")

    expire_time = datetime.now().timestamp() + ttl
    _memory_cache[key] = (value, expire_time)


def _memory_delete(key: str) -> None:
    _memory_cache.pop(key, None)


def _memory_exists(key: str) -> bool:
    if key in _memory_cache:
        _, expire_time = _memory_cache[key]
        if datetime.now().timestamp() < expire_time:
            return True
        del _memory_cache[key]
    return False


# ==================== Token 黑名单 ====================

def blacklist_token(token: str, ttl: int = TOKEN_BLACKLIST_TTL) -> None:
    """将 Token 加入黑名单"""
    key = f"token:blacklist:{token}"
    cache_set(key, "1", ttl)


def is_token_blacklisted(token: str) -> bool:
    """检查 Token 是否在黑名单中"""
    key = f"token:blacklist:{token}"
    return cache_exists(key)


def unblacklist_token(token: str) -> None:
    """从黑名单移除 Token"""
    key = f"token:blacklist:{token}"
    cache_delete(key)


# ==================== 翻译缓存 ====================

def get_translation_cache(source_text: str, src_lang: str, tgt_lang: str) -> Optional[str]:
    """获取翻译缓存"""
    key = f"translation:{src_lang}->{tgt_lang}:{hash(source_text)}"
    cached = cache_get(key)
    if cached:
        try:
            data = json.loads(cached)
            return data.get("text")
        except (json.JSONDecodeError, TypeError):
            pass
    return None


def set_translation_cache(
    source_text: str,
    src_lang: str,
    tgt_lang: str,
    translated_text: str,
) -> None:
    """设置翻译缓存"""
    key = f"translation:{src_lang}->{tgt_lang}:{hash(source_text)}"
    data = json.dumps({
        "source": source_text,
        "translated": translated_text,
        "src_lang": src_lang,
        "tgt_lang": tgt_lang,
        "cached_at": datetime.now().isoformat(),
    })
    cache_set(key, data, TRANSLATION_CACHE_TTL)


def get_translation_stats() -> dict:
    """获取翻译缓存统计"""
    stats = {
        "mode": "redis" if _get_client() else "memory",
        "memory_size": len(_memory_cache),
        "max_cache_size": MAX_CACHE_SIZE,
    }
    if _get_client():
        try:
            info = _get_client().info("memory")
            stats["redis_used_memory"] = info.get("used_memory_human", "N/A")
        except Exception:
            pass
    return stats


# ==================== 通用工具 ====================

def set_json(key: str, data: dict, ttl: int = 3600) -> None:
    """存储 JSON 数据"""
    cache_set(key, json.dumps(data), ttl)


def get_json(key: str) -> Optional[dict]:
    """获取 JSON 数据"""
    value = cache_get(key)
    if value:
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def clear_all() -> None:
    """清空所有缓存（调试用）"""
    client = _get_client()
    if client:
        try:
            client.flushdb()
        except Exception:
            pass
    _memory_cache.clear()
    logger.info("所有缓存已清空")
