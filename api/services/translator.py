"""
LLM 翻译服务 — 支持 DashScope（通义千问）和本地模型

使用 LangChain + DashScope 实现中→泰电商翻译。
集成 Redis 缓存（自动回退到内存）。
"""

import json
import hashlib
import logging
from typing import Optional
from pathlib import Path

from api.config import get_settings
from api.services.cache import (
    cache_get,
    cache_set,
    get_translation_stats,
)

settings = get_settings()
logger = logging.getLogger(__name__)

# 缓存翻译结果 {source_text_hash: translated_text}
_translation_cache: dict[str, str] = {}


def _text_hash(text: str) -> str:
    """文本 SHA-256 哈希（用于缓存）"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_cache() -> None:
    """从文件加载翻译缓存（持久化）"""
    cache_file = Path(__file__).parent.parent.parent / "config" / "translation_cache.json"
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                global _translation_cache
                _translation_cache = json.load(f)
        except Exception:
            _translation_cache = {}


def _save_cache() -> None:
    """保存翻译缓存到文件"""
    cache_file = Path(__file__).parent.parent.parent / "config" / "translation_cache.json"
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(_translation_cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"翻译缓存保存失败: {e}")


# 初始化缓存
_load_cache()


def translate_text(text: str, src_lang: str = "zh", tgt_lang: str = "th") -> str:
    """
    翻译文本（带 Redis/内存缓存）
    
    Args:
        text: 源文本
        src_lang: 源语言代码
        tgt_lang: 目标语言代码
        
    Returns:
        翻译后的文本
    """
    if not text:
        return ""

    # 检查 Redis 缓存
    cached = cache_get(f"translation:{src_lang}->{tgt_lang}:{hashlib.md5(text.encode()).hexdigest()}")
    if cached:
        logger.debug(f"翻译缓存命中 (Redis): {text[:50]}...")
        return cached

    # 检查内存缓存
    text_hash = _text_hash(text)
    cache_key = f"{src_lang}->{tgt_lang}:{text_hash}"
    if cache_key in _translation_cache:
        logger.debug(f"翻译缓存命中 (内存): {text[:50]}...")
        return _translation_cache[cache_key]

    # 调用 LLM 翻译
    result = _call_llm_translate(text, src_lang, tgt_lang)

    # 缓存结果
    if result and not result.startswith("[待翻译]"):
        _translation_cache[cache_key] = result
        cache_set(cache_key, result, ttl=86400 * 30)
        _save_cache()

    return result


def translate_title(title: str) -> str:
    """翻译商品标题（中→泰）"""
    return translate_text(title, "zh", "th")


def translate_description(description: str) -> str:
    """翻译商品描述（中→泰）"""
    return translate_text(description, "zh", "th")


def translate_keywords(keywords: list[str]) -> list[str]:
    """翻译关键词列表"""
    return [translate_text(kw, "zh", "th") for kw in keywords if kw]


def generate_seo_tags(title_th: str, desc_th: str) -> list[str]:
    """
    生成 SEO 标签（泰语）—— S09 实现

    泰语是无空格分隔的连续书写语言，单纯 split() 无法分词。
    使用 PyThaiNLP 进行泰语分词 + TF 频次过滤生成标签。

    流程:
    1. PyThaiNLP 优先（不可用时降级到空格分词 + 逗号/中点切分）
    2. 过滤停用词、过短词、纯数字、纯标点
    3. 以词频排序，最多保留 10 个，去重保留首次出现顺序
    4. 标题词权重 *3，描述词权重 *1，体现 SEO 优先级
    """
    if not title_th:
        return []

    tokens = _thai_tokenize(title_th + " " + (desc_th or ""))

    # 标题分词集合（用于权重提升）
    title_tokens = set(_thai_tokenize(title_th))

    stop = _thai_stopwords()

    freq: dict[str, int] = {}
    for tok in tokens:
        tok = tok.strip()
        if not tok:
            continue
        if len(tok) < 2:                      # 单字词一般无 SEO 价值
            continue
        if tok.isdigit():                     # 纯数字跳过
            continue
        if tok in stop:                       # 停用词跳过
            continue
        if _is_punct_only(tok):               # 纯标点跳过
            continue
        weight = 3 if tok in title_tokens else 1
        freq[tok] = freq.get(tok, 0) + weight

    # 按权重倒序，相同权重保留首次出现顺序
    ordered = sorted(freq.items(), key=lambda kv: (-kv[1],))
    unique: list[str] = []
    for tok, _ in ordered:
        if tok not in unique:
            unique.append(tok)
        if len(unique) >= 10:
            break
    return unique


def _thai_tokenize(text: str) -> list[str]:
    """泰语分词 —— 优先 PyThaiNLP，降级空格/标点切分。"""
    if not text:
        return []
    try:
        from pythainlp.tokenize import word_tokenize
        # engine="newmm" 是 PyThaiNLP 默认且最稳定的字典分词引擎
        return [w for w in word_tokenize(text, engine="newmm") if w.strip()]
    except ImportError:
        logger.debug("PyThaiNLP 未安装，降级空格分词")
    except Exception as e:
        logger.debug(f"PyThaiNLP 分词失败，降级: {e}")
    # 降级: 空格 + 常见标点切分
    import re
    return [w for w in re.split(r"[\s,，。、|/]+", text) if w.strip()]


def _thai_stopwords() -> set[str]:
    """加载泰语停用词；PyThaiNLP 不可用时返回最小内置集。"""
    try:
        from pythainlp.corpus import thai_stopwords
        return set(thai_stopwords())
    except Exception:
        pass
    # 最小内置泰语/电商常见无 SEO 价值词
    return {
        "และ", "หรือ", "ของ", "ที่", "ใน", "เป็น", "ได้", "มี",
        "ไม่", "จะ", "แล้ว", "ก็", "ให้", "นี้", "ไป", "มา",
        "กับ", "the", "a", "an", "and", "or", "of", "in", "on",
    }


def _is_punct_only(token: str) -> bool:
    """判别纯标点字符的 token。"""
    import re
    return bool(re.fullmatch(r"[\W_]+", token))


def _call_llm_translate(text: str, src_lang: str, tgt_lang: str) -> str:
    """
    调用 LLM 进行翻译
    
    优先使用 DashScope（通义千问），降级为本地模型或直接返回原文
    """
    # 尝试 DashScope
    if settings.DASHSCOPE_API_KEY:
        try:
            return _call_dashscope_translate(text, src_lang, tgt_lang)
        except Exception as e:
            logger.warning(f"DashScope 翻译失败，降级: {e}")

    # 降级：返回原文（标记待翻译）
    logger.warning(f"LLM 翻译不可用，返回原文: {text[:100]}")
    return f"[待翻译] {text}"


def _call_dashscope_translate(text: str, src_lang: str, tgt_lang: str) -> str:
    """
    调用 DashScope（通义千问）翻译
    
    使用 qwen-plus 模型进行高质量翻译
    """
    import dashscope
    from dashscope import Generation

    dashscope.api_key = settings.DASHSCOPE_API_KEY

    prompt = (
        f"你是一个专业的跨境电商翻译助手。请将以下{src_lang}文本翻译为{tgt_lang}，"
        f"要求：\n"
        f"1. 保持电商商品描述风格\n"
        f"2. 使用泰国当地常用的电商用语\n"
        f"3. 不要翻译品牌名（除非是通用词）\n"
        f"4. 只输出翻译结果，不要输出其他内容\n"
        f"5. 如果原文已经是{tgt_lang}，直接返回原文\n\n"
        f"原文：{text}\n\n"
        f"翻译："
    )

    response = Generation.call(
        model=settings.LLM_MODEL or "qwen-plus",
        prompt=prompt,
        temperature=0.3,
        max_tokens=2048,
    )

    if response.status_code == 200:
        result = response.output.text.strip()
        # 清理可能的多余内容
        result = result.replace("翻译：", "").strip()
        return result
    else:
        raise Exception(f"DashScope API 错误: {response.code} - {response.message}")


def translate_bulk(texts: list[str], src_lang: str = "zh", tgt_lang: str = "th") -> list[str]:
    """
    批量翻译（带速率限制）
    
    Args:
        texts: 待翻译文本列表
        src_lang: 源语言
        tgt_lang: 目标语言
        
    Returns:
        翻译结果列表
    """
    results = []
    for i, text in enumerate(texts):
        try:
            result = translate_text(text, src_lang, tgt_lang)
            results.append(result)
        except Exception as e:
            logger.error(f"批量翻译失败 [{i}]: {e}")
            results.append(f"[翻译失败] {text}")
        # 简单的速率限制（避免触发 API 限流）
        if i < len(texts) - 1:
            import time
            time.sleep(0.5)

    return results


def get_translation_stats() -> dict:
    """获取翻译缓存统计"""
    return {
        "cache_size": len(_translation_cache),
        "cache_file": str(Path(__file__).parent.parent.parent / "config" / "translation_cache.json"),
    }


def clear_translation_cache() -> None:
    """清空翻译缓存"""
    global _translation_cache
    _translation_cache = {}
    _save_cache()
    logger.info("翻译缓存已清空")
