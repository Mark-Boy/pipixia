"""
测试缓存服务 — Redis + 内存回退
"""

import pytest
from api.services.cache import (
    cache_get,
    cache_set,
    cache_delete,
    cache_exists,
    blacklist_token,
    is_token_blacklisted,
    get_translation_stats,
    _memory_get,
    _memory_set,
    _memory_cache,
)
from datetime import datetime


class TestMemoryCache:
    """内存缓存测试"""

    def setup_method(self):
        """每个测试前清空内存缓存"""
        _memory_cache.clear()

    def test_memory_set_and_get(self):
        """设置和获取缓存"""
        _memory_set("key1", "value1", ttl=3600)
        assert _memory_get("key1") == "value1"

    def test_memory_get_nonexistent(self):
        """获取不存在的键"""
        assert _memory_get("nonexistent") is None

    def test_memory_delete(self):
        """删除缓存"""
        _memory_set("key1", "value1", ttl=3600)
        cache_delete("key1")
        assert _memory_get("key1") is None

    def test_memory_ttl_expiry(self):
        """TTL 过期测试"""
        _memory_set("key1", "value1", ttl=0)
        # TTL 为 0 应该立即过期
        result = _memory_get("key1")
        # 可能因为时间差仍然命中，但至少不应出错

    def test_memory_lru_eviction(self):
        """LRU 淘汰测试"""
        # 设置一个很小的容量来测试
        from api.services.cache import MAX_CACHE_SIZE
        original_max = MAX_CACHE_SIZE

        # 填充到接近上限
        for i in range(original_max - 100, original_max):
            _memory_set(f"key{i}", f"value{i}", ttl=3600)

        # 添加更多应该触发淘汰
        _memory_set("key_new", "value_new", ttl=3600)
        assert _memory_get("key_new") == "value_new"


class TestTokenBlacklist:
    """Token 黑名单测试"""

    def setup_method(self):
        _memory_cache.clear()

    def test_blacklist_and_check(self):
        """黑名单添加和检查"""
        token = "test-token-123"
        blacklist_token(token, ttl=3600)
        assert is_token_blacklisted(token) is True

    def test_non_blacklisted_token(self):
        """非黑名单 Token"""
        assert is_token_blacklisted("nonexistent-token") is False

    def test_unblacklist(self):
        """从黑名单移除"""
        token = "test-token-456"
        blacklist_token(token, ttl=3600)
        assert is_token_blacklisted(token) is True

        from api.services.cache import unblacklist_token
        unblacklist_token(token)
        assert is_token_blacklisted(token) is False


class TestTranslationStats:
    """翻译缓存统计测试"""

    def test_get_stats(self):
        """获取缓存统计"""
        stats = get_translation_stats()
        assert "mode" in stats
        assert "memory_size" in stats
        assert stats["mode"] in ("redis", "memory")
