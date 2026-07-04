"""
LLM 翻译服务 — 支持 DashScope（通义千问）和本地模型

使用 LangChain + DashScope 实现中→泰电商翻译。
"""

import json
import hashlib
import logging
from typing import Optional
from pathlib import Path

from api.config import get_settings

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
    翻译文本（带缓存）
    
    Args:
        text: 源文本
        src_lang: 源语言代码
        tgt_lang: 目标语言代码
        
    Returns:
        翻译后的文本
    """
    if not text:
        return ""

    # 检查缓存
    text_hash = _text_hash(text)
    cache_key = f"{src_lang}->{tgt_lang}:{text_hash}"
    if cache_key in _translation_cache:
        logger.debug(f"翻译缓存命中: {text[:50]}...")
        return _translation_cache[cache_key]

    # 调用 LLM 翻译
    result = _call_llm_translate(text, src_lang, tgt_lang)

    # 缓存结果
    if result:
        _translation_cache[cache_key] = result
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
    生成 SEO 标签（泰语）
    
    从标题和描述中提取高频有意义的词组作为标签
    """
    if not title_th:
        return []

    # 简单分词：泰语以空格分隔，中文需要更复杂的分词
    # 暂时使用简单的空格分割，后续可接入 PyThaiNLP
    words = []
    for text in [title_th, desc_th or ""]:
        if text:
            for word in text.split():
                # 过滤太短的词
                if len(word.strip()) >= 2:
                    words.append(word.strip())

    # 去重 + 限制数量
    seen = set()
    unique_words = []
    for w in words:
        if w not in seen and len(unique_words) < 10:
            seen.add(w)
            unique_words.append(w)

    return unique_words


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
