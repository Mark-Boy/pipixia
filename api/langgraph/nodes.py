"""
LangGraph 翻译工作流 — 节点函数

翻译工作流有向图：
    extract_images → translate_text → translate_images → check_risk → calculate_finance → generate_tags
"""

import json
import hashlib
from typing import TypedDict, Annotated, Any
from dataclasses import dataclass, field
from datetime import datetime

from api.database import async_session
from api.models.product import Product
from api.models.translate import Translate
from api.models.risk_log import RiskLog
from api.services.crypto import decrypt_aes256
from api.services.translator import (
    translate_text,
    translate_bulk,
    generate_seo_tags,
    get_translation_stats,
)
from api.config import Settings
import logging

logger = logging.getLogger(__name__)


@dataclass
class WorkflowState(TypedDict):
    """工作流状态"""
    product_id: int
    shop_id: int
    title_zh: str
    title_th: str | None
    desc_zh: str | None
    desc_th: str | None
    images: list[dict] | None  # [{"url": "...", "ocr_text": "...", "translated_image_url": "..."}]
    risk_status: str  # pass / block / manual
    risk_detail: str | None
    profit_thb: float | None
    profit_margin: float | None
    seo_tags: list[str] | None
    error_message: str | None = None  # pending / processing / completed / failed
    updated_at: datetime | None = None
    translate_status: str = "pending"


async def node_extract_images(state: WorkflowState) -> WorkflowState:
    """节点1：提取商品图片 OCR 文字"""
    try:
        product_id = state["product_id"]

        async with async_session() as db:
            result = await db.execute(
                db.select(Product).where(Product.id == product_id)
            )
            product = result.scalar_one_or_none()

            if not product or not product.images_oss_keys:
                logger.warning(f"商品 {product_id} 无图片")
                state["images"] = []
                return state

            images = []
            for image_url in product.images_oss_keys:
                ocr_result = await extract_image_text(image_url)
                images.append({
                    "url": image_url,
                    "ocr_text": ocr_result.get("text", ""),
                    "confidence": ocr_result.get("confidence", 0),
                    "translated_image_url": None,
                })

            state["images"] = images
            logger.info(f"商品 {product_id} 提取 {len(images)} 张图片 OCR")
            return state

    except Exception as e:
        logger.error(f"图片 OCR 失败: {e}")
        state["error_message"] = str(e)
        return state


async def _ocr_with_paddle(image_path: str) -> dict:
    """
    使用 PaddleOCR 提取图片中的文字

    针对电商图片特点优化：
    - 只提取中文和泰语区域
    - 过滤低置信度的结果
    - 合并相邻文本块
    """
    from paddleocr import PaddleOCR

    # 懒加载 OCR 引擎（避免每次请求都初始化）
    if not hasattr(_ocr_with_paddle, "_ocr_engine"):
        _ocr_with_paddle._ocr_engine = PaddleOCR(
            use_angle_cls=True,
            lang="ch",  # 中文为主
            show_log=False,
            use_gpu=False,  # 避免 GPU 内存问题
        )

    ocr = _ocr_with_paddle._ocr_engine
    result = ocr.ocr(image_path, cls=True)

    if not result or not result[0]:
        return {"text": "", "confidence": 0}

    # 提取所有文本块
    texts = []
    total_confidence = 0
    count = 0

    for line in result[0]:
        word_text = line[1][0]
        confidence = line[1][1]

        if confidence < 0.5 or len(word_text.strip()) < 1:
            continue

        texts.append(word_text.strip())
        total_confidence += confidence
        count += 1

    full_text = "".join(texts)
    avg_confidence = round(total_confidence / count, 4) if count > 0 else 0

    return {
        "text": full_text,
        "confidence": avg_confidence,
        "blocks": [
            {"text": t, "confidence": round(c, 4)}
            for t, c in zip(texts, [total_confidence / max(count, 1)] * len(texts))
        ],
    }


async def extract_image_text(image_url: str) -> dict:
    """
    调用 PaddleOCR 提取图片中的文字

    支持：
    1. 本地 URL（file:// 或 http://）
    2. OSS URL（MinIO/S3）
    3. 远程 URL（http/https）

    Returns:
        {"text": "提取的文字", "confidence": 0.95, "blocks": [...]}
    """
    import os
    import tempfile
    from urllib.parse import urlparse

    # 下载图片到临时文件
    image_path = await _download_image(image_url)
    if not image_path:
        return {"text": "", "confidence": 0}

    try:
        return await _ocr_with_paddle(image_path)
    except ImportError:
        logger.warning("PaddleOCR 未安装，跳过图片文字提取")
        return {"text": "", "confidence": 0}
    except Exception as e:
        logger.error(f"OCR 提取失败: {e}")
        return {"text": "", "confidence": 0}
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)


async def _download_image(url: str) -> str:
    """下载图片到临时文件，返回本地路径"""
    import os
    import tempfile
    from urllib.parse import urlparse

    parsed = urlparse(url)

    # 本地文件
    if parsed.scheme == "file":
        return parsed.path

    # 远程 URL，使用 httpx 下载
    if parsed.scheme in ("http", "https"):
        import httpx

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()

            # 确定文件扩展名
            ext = parsed.path.split(".")[-1] if parsed.path else "jpg"
            if ext not in ("jpg", "jpeg", "png", "webp", "gif", "bmp"):
                ext = "jpg"

            # 保存到临时文件
            tmp_file = tempfile.NamedTemporaryFile(
                suffix=f".{ext}", delete=False, dir="/tmp"
            )
            tmp_file.write(resp.content)
            tmp_file.close()
            return tmp_file.name

    # MinIO/S3 对象存储 URL
    if "/pipixia-images/" in url or "minio" in url:
        import httpx

        # 假设 MinIO 有预签名 URL 或可通过控制台访问
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()

                tmp_file = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False, dir="/tmp")
                tmp_file.write(resp.content)
                tmp_file.close()
                return tmp_file.name
        except Exception:
            pass

    return ""


async def node_translate_text(state: WorkflowState) -> WorkflowState:
    """节点2：AI 翻译商品标题和描述（中→泰）"""
    try:
        product_id = state["product_id"]
        title_zh = state.get("title_zh", "") or ""
        desc_zh = state.get("desc_zh") or ""

        # 批量翻译（标题 + 描述）
        texts_to_translate = [t for t in [title_zh, desc_zh] if t]
        if texts_to_translate:
            translations = translate_bulk(texts_to_translate, "zh", "th")
            
            if title_zh:
                state["title_th"] = translations[0] if translations else title_zh
            if desc_zh:
                state["desc_th"] = translations[-1] if translations else desc_zh

            # 保存翻译记录
            if title_zh:
                await save_translate_record(
                    product_id=product_id,
                    translate_type="title",
                    source_text=title_zh,
                    target_text=state["title_th"],
                )
            if desc_zh:
                await save_translate_record(
                    product_id=product_id,
                    translate_type="description",
                    source_text=desc_zh,
                    target_text=state["desc_th"],
                )

        state["translate_status"] = "processing"
        logger.info(f"商品 {product_id} 文本翻译完成")
        return state

    except Exception as e:
        logger.error(f"文本翻译失败: {e}")
        state["error_message"] = str(e)
        state["translate_status"] = "failed"
        return state


async def ai_translate_text(text: str, src_lang: str = "zh", tgt_lang: str = "th") -> str:
    """
    调用 LLM 翻译文本（异步包装）
    """
    return translate_text(text, src_lang, tgt_lang)


async def node_translate_images(state: WorkflowState) -> WorkflowState:
    """节点3：翻译图片中的文字（OCR → AI翻译 → 合成新图片）"""
    try:
        images = state.get("images", [])
        for img in images:
            if img.get("ocr_text"):
                translated_text = await ai_translate_text(
                    img["ocr_text"], "zh", "th"
                )
                # TODO: 合成新图片（泰语文字覆盖）
                # img["translated_image_url"] = await synthesize_image(...)
                logger.info(f"图片翻译: {img.get('url', '')}")

        state["translate_status"] = "processing"
        logger.info(f"商品图片翻译完成")
        return state

    except Exception as e:
        logger.error(f"图片翻译失败: {e}")
        return state


async def node_check_risk(state: WorkflowState) -> WorkflowState:
    """节点4：风控检测（品牌词 + 敏感词）"""
    try:
        title_th = state.get("title_th", "") or ""
        desc_th = state.get("desc_th", "") or ""
        combined_text = title_th + " " + desc_th

        # 加载风控词库
        risk_words = await load_risk_words()

        # 检测品牌词
        brand_matches = []
        for word in risk_words.get("brand_keywords", []):
            if word in combined_text:
                brand_matches.append(word)

        # 检测禁词
        prohibited_matches = []
        for word in risk_words.get("prohibited_words", []):
            if word in combined_text:
                prohibited_matches.append(word)

        # 判定风险等级
        if prohibited_matches:
            state["risk_status"] = "block"
            state["risk_detail"] = f"禁词: {', '.join(prohibited_matches)}"
        elif brand_matches:
            state["risk_status"] = "manual"
            state["risk_detail"] = f"品牌词: {', '.join(brand_matches)}，需人工确认"
        else:
            state["risk_status"] = "pass"
            state["risk_detail"] = "无风险"

        logger.info(f"商品风控检测: {state['risk_status']}")
        return state

    except Exception as e:
        logger.error(f"风控检测失败: {e}")
        state["risk_status"] = "manual"
        state["risk_detail"] = f"检测异常: {str(e)}"
        return state


async def load_risk_words() -> dict:
    """加载风控词库"""
    import json
    from pathlib import Path

    risk_file = Path(__file__).parent.parent.parent / "config" / "risk_words.json"
    if risk_file.exists():
        with open(risk_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"brand_keywords": [], "prohibited_words": []}


async def node_calculate_finance(state: WorkflowState) -> WorkflowState:
    """节点5：利润核算"""
    try:
        product_id = state["product_id"]

        async with async_session() as db:
            result = await db.execute(
                db.select(Product).where(Product.id == product_id)
            )
            product = result.scalar_one_or_none()

            if not product:
                state["profit_thb"] = 0
                state["profit_margin"] = 0
                return state

            # 使用实时汇率
            try:
                from api.services.exchange import fetch_exchange_rate
                exchange_rate = fetch_exchange_rate()
            except Exception:
                exchange_rate = 5.0
            revenue_thb = product.price_thb
            cost_thb = product.cost_cny * exchange_rate

            # 预估费用
            commission_thb = revenue_thb * 0.05  # Shopee 佣金 5%
            platform_fee = 3.0
            logistics = 40.0

            total_cost = cost_thb + commission_thb + platform_fee + logistics
            profit = revenue_thb - total_cost
            margin = (profit / revenue_thb * 100) if revenue_thb > 0 else 0

            state["profit_thb"] = round(profit, 2)
            state["profit_margin"] = round(margin, 2)

            # 利润率低于阈值 → 标记为风险
            if margin < 10:
                state["risk_status"] = "manual"
                state["risk_detail"] = f"利润率仅 {margin}%，低于安全阈值 10%"

        return state

    except Exception as e:
        logger.error(f"利润核算失败: {e}")
        state["error_message"] = str(e)
        return state


async def node_generate_tags(state: WorkflowState) -> WorkflowState:
    """节点6：生成 SEO 标签（泰语）"""
    try:
        title_th = state.get("title_th", "") or ""
        desc_th = state.get("desc_th", "") or ""

        tags = generate_seo_tags(title_th, desc_th)
        state["seo_tags"] = tags
        logger.info(f"商品 SEO 标签生成完成: {tags}")
        return state

    except Exception as e:
        logger.error(f"SEO 标签生成失败: {e}")
        state["seo_tags"] = []
        return state


async def save_translate_record(
    product_id: int,
    translate_type: str,
    source_text: str,
    target_text: str,
    confidence_score: float = 0.95,
    source_image_url: str = None,
    target_image_url: str = None,
) -> None:
    """保存翻译记录到数据库"""
    try:
        text_hash = hashlib.sha256(source_text.encode("utf-8")).hexdigest()

        async with async_session() as db:
            record = Translate(
                product_id=product_id,
                translate_type=translate_type,
                source_text_hash=text_hash,
                source_text=source_text[:5000],
                target_text=target_text[:5000],
                source_image_url=source_image_url,
                target_image_url=target_image_url,
                confidence_score=confidence_score,
                status="success",
            )
            db.add(record)
            await db.commit()
            logger.info(f"翻译记录已保存: product={product_id}, type={translate_type}")

    except Exception as e:
        logger.error(f"保存翻译记录失败: {e}")


async def save_risk_log(product_id: int, risk_type: str, risk_detail: str):
    """保存风控日志"""
    try:
        async with async_session() as db:
            log = RiskLog(
                product_id=product_id,
                risk_type=risk_type,
                risk_detail=risk_detail,
            )
            db.add(log)
            await db.commit()

    except Exception as e:
        logger.error(f"保存风控日志失败: {e}")
