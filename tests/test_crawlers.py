"""
爬虫测试 — 1688/拼多多 URL 解析
"""

import pytest
from api.crawlers.alibaba_1688 import Alibaba1688Crawler
from api.crawlers.pinduoduo import PinduoduoCrawler
from api.crawlers.base import is_safe_url, ProductInfo


class TestURLParsing:
    """URL 解析测试"""

    def test_alibaba_1688_standard_url(self):
        """1688 标准详情页 URL"""
        crawler = Alibaba1688Crawler()
        url = "https://detail.1688.com/offer/679123456789.html"
        platform, item_id = crawler.parse_url(url)
        assert platform == "1688"
        assert item_id == "679123456789"

    def test_alibaba_1688_mobile_url(self):
        """1688 移动端 URL"""
        crawler = Alibaba1688Crawler()
        url = "https://m.1688.com/offer/detail/679123456789.html"
        platform, item_id = crawler.parse_url(url)
        assert platform == "1688"
        assert item_id == "679123456789"

    def test_alibaba_1688_old_format(self):
        """1688 旧版 URL"""
        crawler = Alibaba1688Crawler()
        url = "https://www.1688.com/offerdetail/679123456789.htm"
        platform, item_id = crawler.parse_url(url)
        assert platform == "1688"
        assert item_id == "679123456789"

    def test_alibaba_1688_invalid_url(self):
        """1688 无效 URL"""
        crawler = Alibaba1688Crawler()
        with pytest.raises(ValueError):
            crawler.parse_url("https://example.com/not-1688")

    def test_pinduoduo_item_id_param(self):
        """拼多多 item_id 参数 URL"""
        crawler = PinduoduoCrawler()
        url = "https://mobile.yangkeduo.com/proxy/apis/v5/item/detail?item_id=123456789"
        platform, item_id = crawler.parse_url(url)
        assert platform == "pdd"
        assert item_id == "123456789"

    def test_pinduoduo_groupon_url(self):
        """拼多多团购 URL"""
        crawler = PinduoduoCrawler()
        url = "https://mobile.yangkeduo.com/proxy/apis/v5/item/groupon?item_id=987654321"
        platform, item_id = crawler.parse_url(url)
        assert platform == "pdd"
        assert item_id == "987654321"

    def test_pinduoduo_invalid_url(self):
        """拼多多无效 URL"""
        crawler = PinduoduoCrawler()
        with pytest.raises(ValueError):
            crawler.parse_url("https://example.com/not-pdd")


class TestSSRFProtection:
    """SSRF 防护测试"""

    def test_safe_1688_url(self):
        assert is_safe_url("https://detail.1688.com/offer/123.html") is True
        assert is_safe_url("https://m.1688.com/offer/123.html") is True

    def test_safe_pdd_url(self):
        assert is_safe_url("https://mobile.yangkeduo.com/proxy/apis/v5/item/detail?item_id=123") is True

    def test_unsafe_url(self):
        assert is_safe_url("https://evil.com/malicious") is False
        assert is_safe_url("http://169.254.169.254/latest/meta-data") is False
        assert is_safe_url("http://192.168.1.1/admin") is False
        assert is_safe_url("http://localhost:6379/") is False


class TestProductInfo:
    """ProductInfo 数据结构测试"""

    def test_default_values(self):
        info = ProductInfo()
        assert info.title_zh == ""
        assert info.price_cny is None
        assert info.images_urls == []
        assert info.specs == {}

    def test_full_data(self):
        info = ProductInfo(
            title_zh="测试商品",
            price_cny=99.9,
            cost_cny=50.0,
            images_urls=["http://img1.jpg", "http://img2.jpg"],
            source_platform="1688",
            source_item_id="123456",
        )
        assert info.title_zh == "测试商品"
        assert info.price_cny == 99.9
        assert info.cost_cny == 50.0
        assert len(info.images_urls) == 2


class TestPriceExtraction:
    """价格提取测试"""

    def test_simple_price(self):
        crawler = Alibaba1688Crawler()
        assert crawler.extract_price("¥99.90") == 99.9
        assert crawler.extract_price("价格: 150.00") == 150.0

    def test_comma_separated(self):
        crawler = Alibaba1688Crawler()
        assert crawler.extract_price("¥1,234.56") == 1234.56

    def test_no_price(self):
        crawler = Alibaba1688Crawler()
        assert crawler.extract_price("免费") is None
        assert crawler.extract_price("") is None


class TestTextCleaning:
    """文本清洗测试"""

    def test_whitespace_cleanup(self):
        crawler = Alibaba1688Crawler()
        result = crawler.clean_text("  测试   商品  ")
        assert result == "测试 商品"

    def test_special_char_removal(self):
        crawler = Alibaba1688Crawler()
        result = crawler.clean_text("【新品】热销商品！")
        assert "新品" in result
        assert "热销" in result
