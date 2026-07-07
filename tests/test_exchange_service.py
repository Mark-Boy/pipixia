"""
测试汇率服务
"""

import pytest
from unittest.mock import patch, MagicMock
from api.services.exchange import (
    fetch_exchange_rate,
    get_exchange_rate,
    convert_cny_to_thb,
    convert_thb_to_cny,
    _get_cached_rate,
    _set_cached_rate,
)


class TestExchangeRate:
    """汇率服务测试"""

    def test_default_rate_when_no_api(self):
        """API 不可用时返回默认汇率"""
        # 清除缓存
        from api.services.cache import _memory_cache
        _memory_cache.clear()

        # Mock API 调用失败
        with patch('api.services.exchange._fetch_from_api', return_value=None):
            rate = fetch_exchange_rate()
            assert rate == 5.0  # 默认汇率

    def test_fetch_from_mocked_api(self):
        """模拟 API 返回汇率"""
        from api.services.cache import _memory_cache
        _memory_cache.clear()

        with patch('api.services.exchange._fetch_from_api', return_value=4.8521):
            rate = fetch_exchange_rate()
            assert rate == 4.8521

    def test_cached_rate_returns_fast(self):
        """缓存命中时直接返回"""
        from api.services.cache import _memory_cache
        _memory_cache.clear()

        # 先设置一个缓存值
        _set_cached_rate(4.9)

        cached = _get_cached_rate()
        assert cached == 4.9

    def test_convert_cny_to_thb(self):
        """CNY → THB 转换"""
        from api.services.cache import _memory_cache
        _memory_cache.clear()

        with patch('api.services.exchange._fetch_from_api', return_value=4.85):
            result = convert_cny_to_thb(100)
            assert result == 485.0

    def test_convert_thb_to_cny(self):
        """THB → CNY 转换"""
        from api.services.cache import _memory_cache
        _memory_cache.clear()

        with patch('api.services.exchange._fetch_from_api', return_value=4.85):
            result = convert_thb_to_cny(485)
            assert abs(result - 100.0) < 0.1

    def test_get_exchange_rate_info(self):
        """获取汇率信息"""
        from api.services.cache import _memory_cache
        _memory_cache.clear()

        with patch('api.services.exchange._fetch_from_api', return_value=4.8521):
            info = get_exchange_rate()
            assert info["currency_pair"] == "CNY/THB"
            assert info["rate"] == 4.8521
            assert info["inverse_rate"] == pytest.approx(0.2061, abs=0.001)
            assert info["cached"] is True
