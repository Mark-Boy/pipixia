"""
货源平台爬虫 — 1688 / 拼多多商品详情抓取
"""

from .base import BaseCrawler
from .alibaba_1688 import Alibaba1688Crawler
from .pinduoduo import PinduoduoCrawler

__all__ = ["BaseCrawler", "Alibaba1688Crawler", "PinduoduoCrawler"]
