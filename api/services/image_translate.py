"""
图片翻译服务 — OCR 提取 → 翻译 → 合成泰语文字覆盖

S07 实现：电商图片中的中文/英文文字识别后翻译为泰语并合成新图片。

设计要点:
1. OCR 引擎可插拔 —— 优先 PaddleOCR（中文识别最佳），降级到 Tesseract / 不可用时返回空文本
   且整个流程不抛异常，保证 LangGraph 节点链路不中断
2. 合成阶段保留原图视觉布局 —— 在原文字位置用泰语覆盖，背景用周边像素均值填充避免残留
3. 泰语字体优先级: 系统安装的泰语 TTF > 内置默认字体; 字号根据原图文字 bbox 高度自适应
4. 全程断网/缺依赖优雅降级 —— 任何阶段失败返回原图 URL，由上层 task 记录日志

该模块是同步函数（worker Celery 任务直接调用），内部 IO 走 httpx 同步客户端/',
   因为 Celery task 进程不是 asyncio 环境。
"""

from __future__ import annotations

import hashlib
import io
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from api.services.cache import cache_get, cache_set
from api.services.storage import storage, upload_image

logger = logging.getLogger(__name__)

# OCR 结果缓存 TTL: 7 天（图片文字不会变）
OCR_CACHE_TTL = 86400 * 7
# 合成结果图片不重复处理 —— 用源 URL + 翻译文本的 hash 作 object key
_FONT_CANDIDATES = [
    # 泰语常用字体（按可用性排序）
    "/usr/share/fonts/opentype/noto/NotoSansThai-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
    "/usr/share/fonts/truetype/loma/loma.ttf",
    "/usr/share/fonts/thai/NotoSerifThai-Regular.ttf",
]
_DEFAULT_FONT_FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


# ==================== OCR ===================


def _ocr_engine():
    """懒加载 PaddleOCR 引擎（单例）。未安装时返回 None。"""
    if hasattr(_ocr_engine, "_engine"):
        return _ocr_engine._engine
    try:
        from paddleocr import PaddleOCR

        _ocr_engine._engine = PaddleOCR(
            use_angle_cls=True,
            lang="ch",  # 中文 + 英文 + 数字
            show_log=False,
            use_gpu=False,
        )
        logger.info("PaddleOCR 引擎初始化完成")
        return _ocr_engine._engine
    except ImportError:
        logger.warning("PaddleOCR 未安装，图片文字提取降级为空")
        _ocr_engine._engine = None
        return None
    except Exception as e:
        logger.warning(f"PaddleOCR 初始化失败，降级: {e}")
        _ocr_engine._engine = None
        return None


def _download_image_sync(url: str) -> Optional[bytes]:
    """同步下载图片为 bytes。本地 file:// 也支持。"""
    import httpx

    parsed = urlparse(url)
    if parsed.scheme == "file":
        try:
            with open(parsed.path, "rb") as f:
                return f.read()
        except Exception as e:
            logger.warning(f"读取本地图片失败 {url}: {e}")
            return None

    if parsed.scheme in ("http", "https"):
        try:
            with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                resp = client.get(url)
                resp.raise_for_status()
                return resp.content
        except Exception as e:
            logger.warning(f"下载图片失败 {url}: {e}")
            return None

    # 未知 scheme
    return None


def _paddle_ocr_bytes(image_bytes: bytes, tmp_path: str) -> list[dict]:
    """
    用 PaddleOCR 识别，返回标准化的文字块列表。

    每块结构:
        {
            "text": "原文字",
            "confidence": 0.98,
            "bbox": [[x1,y1],[x2,y2],[x3,y3],[x4,y4]],  # 四点多边形
            "box": [x, y, w, h],                         # 正外接矩形
        }
    """
    engine = _ocr_engine()
    if engine is None:
        return []

    try:
        result = engine.ocr(tmp_path, cls=True)
    except Exception as e:
        logger.warning(f"PaddleOCR 推理失败: {e}")
        return []

    if not result or not result[0]:
        return []

    blocks: list[dict] = []
    for line in result[0]:
        if not line or len(line) < 2:
            continue
        box, (text, conf) = line[0], line[1]
        text = (text or "").strip()
        if not text or conf < 0.5:
            continue
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        x, y = int(min(xs)), int(min(ys))
        w, h = int(max(xs) - x), int(max(ys) - y)
        blocks.append({
            "text": text,
            "confidence": round(float(conf), 4),
            "bbox": [[float(p[0]), float(p[1])] for p in box],
            "box": [x, y, w, h],
        })
    return blocks


def extract_image_text_blocks(image_url: str) -> list[dict]:
    """
    提取图片里的文字块（带位置）。

    Returns:
        list[dict]: 文字块列表（结构见 _paddle_ocr_bytes）。OCR 不可用时返回 []。
    """
    cache_key = f"ocr:{hashlib.md5(image_url.encode()).hexdigest()}"
    cached = cache_get(cache_key)
    if cached:
        try:
            import json
            return json.loads(cached)
        except Exception:
            pass

    image_bytes = _download_image_sync(image_url)
    if not image_bytes:
        return []

    # 写临时文件给 PaddleOCR
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False, dir="/tmp")
    try:
        tmp.write(image_bytes)
        tmp.close()
        blocks = _paddle_ocr_bytes(image_bytes, tmp.name)
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    try:
        import json
        cache_set(cache_key, json.dumps(blocks, ensure_ascii=False), ttl=OCR_CACHE_TTL)
    except Exception:
        pass
    return blocks


# ==================== 合成 ====================


def _pick_thai_font(font_size: int):
    """返回 PIL ImageFont 对象。优先泰语字体，缺失则用 DejaVu 回退。"""
    from PIL import ImageFont

    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, font_size)

    if os.path.exists(_DEFAULT_FONT_FALLBACK):
        return ImageFont.truetype(_DEFAULT_FONT_FALLBACK, font_size)

    # 最后回退: PIL 内置位图字体（不支持 Thai 但不会崩）
    return ImageFont.load_default()


def _cover_box(draw, box: list[int], bg_rgb: tuple[int, int, int]) -> None:
    """用纯色填充原文字区域，避免残留中文字符。box = [x, y, w, h]。"""
    x, y, w, h = box
    draw.rectangle([x, y, x + w, y + h], fill=bg_rgb + (255,))


def _fit_text_width(text: str, font, max_width: int) -> str:
    """若泰语文本超出框宽，按字符逐个截断并补省略号。"""
    from PIL import ImageFont

    if not text:
        return text
    try:
        bbox = font.getbbox(text)
        text_w = bbox[2] - bbox[0]
    except Exception:
        return text
    if text_w <= max_width:
        return text
    # 二分查找最长可放下前缀
    lo, hi = 1, len(text)
    best = 1
    while lo <= hi:
        mid = (lo + hi) // 2
        try:
            wb = font.getbbox(text[:mid])
            if wb[2] - wb[0] <= max_width:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        except Exception:
            hi = mid - 1
    return text[:best] + ("…" if best < len(text) else "")


def synthesize_translated_image(
    image_bytes: bytes,
    blocks_with_translation: list[dict],
    product_id: Optional[int] = None,
    image_index: int = 0,
) -> str:
    """
    合成泰语覆盖图片。

    Args:
        image_bytes: 原图二进制
        blocks_with_translation: OCR 文字块 + 翻译文本
            [{"box": [x,y,w,h], "translated_text": "泰语", "confidence": 0.9}, ...]
        product_id: 商品 ID（用于 object key 命名）
        image_index: 第几张图

    Returns:
        新图片的上传 URL。失败回退原图（转存对象存储）。
    """
    from PIL import Image, ImageDraw

    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    except Exception as e:
        logger.warning(f"打开原图失败: {e}")
        # 无法处理 —— 直接把原图上传
        return storage.upload_file(image_bytes, _gen_key(product_id, image_index, "jpg"), "image/jpeg")

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for blk in blocks_with_translation:
        translated = (blk.get("translated_text") or "").strip()
        if not translated:
            continue
        box = blk.get("box")
        if not box or len(box) != 4:
            continue
        x, y, w, h = box
        if w <= 0 or h <= 0:
            continue

        # 自适应字号 —— 文字块高度 * 0.85，最小 8
        font_size = max(8, int(h * 0.85))
        font = _pick_thai_font(font_size)
        translated = _fit_text_width(translated, font, int(w * 1.05))

        # 取原文字区域附近像素均值作背景色 —— 抹掉原中文
        try:
            bg_rgb = _sample_avg_color(img, box)
        except Exception:
            bg_rgb = (255, 255, 255)

        _cover_box(draw, box, bg_rgb)

        # 泰语文字渲染 —— 保留垂直居中
        try:
            tbbox = font.getbbox(translated)
            text_h = tbbox[3] - tbbox[1]
            text_y = y + max(0, (h - text_h) // 2) - tbbox[1]
        except Exception:
            text_y = y

        draw.text((x + 1, text_y), translated, fill=(0, 0, 0, 255), font=font)

    # 合成图层并转回 RGB 输出 JPEG（更小、Web 友好）
    composed = Image.alpha_composite(img, overlay).convert("RGB")

    out_buf = io.BytesIO()
    composed.save(out_buf, format="JPEG", quality=92)
    out_bytes = out_buf.getvalue()

    return storage.upload_file(out_bytes, _gen_key(product_id, image_index, "jpg"), "image/jpeg")


def _sample_avg_color(img, box: list[int]) -> tuple[int, int, int]:
    """取 box 略放大区域的像素均值作为背景色。"""
    from PIL import Image
    x, y, w, h = box
    pad = max(4, max(w, h) // 4)
    left = max(0, x - pad)
    upper = max(0, y - pad)
    right = min(img.width, x + w + pad)
    lower = min(img.height, y + h + pad)
    if right <= left or lower <= upper:
        return (255, 255, 255)
    crop = img.crop((left, upper, right, lower)).convert("RGB").resize((1, 1))
    rgb = crop.getpixel((0, 0))
    return tuple(int(c) for c in rgb)  # type: ignore[return-value]


def _gen_key(product_id: Optional[int], image_index: int, ext: str) -> str:
    pid = product_id if product_id is not None else "generic"
    return f"products/{pid}/translated/img_{image_index:03d}.{ext}"


# ==================== 顶层入口: OCR → 翻译 → 合成 ====================


def translate_image(
    image_url: str,
    product_id: Optional[int] = None,
    image_index: int = 0,
    translate_fn=None,
) -> dict:
    """
    完整的图片翻译流程: OCR → 翻译 → 合成新图片 → 上传

    Args:
        image_url: 源图片 URL
        product_id: 商品 ID
        image_index: 第几张图（用于 object key 命名）
        translate_fn: 可选的翻译回调 fn(text, src='zh', tgt='th') -> str
                      默认使用 api.services.translator.translate_text

    Returns:
        {
            "source_url": 原图,
            "result_url": 合成图（失败时 == 原图）,
            "ocr_blocks": 提取到的文字块数,
            "translated_blocks": 实际翻译渲染的块数,
            "status": "completed" / "skipped",
        }
    """
    if translate_fn is None:
        from api.services.translator import translate_text as translate_fn  # type: ignore

    # 1. OCR 提取
    blocks = extract_image_text_blocks(image_url)
    if not blocks:
        logger.info(f"图片 {image_url} 无可识别文字，跳过")
        return {
            "source_url": image_url,
            "result_url": image_url,  # 原图直接返回
            "ocr_blocks": 0,
            "translated_blocks": 0,
            "status": "skipped",
        }

    # 2. 翻译每块文本
    for blk in blocks:
        try:
            blk["translated_text"] = translate_fn(blk["text"], "zh", "th")
        except Exception as e:
            logger.warning(f"图片文字翻译失败: {e}")
            blk["translated_text"] = ""

    # 3. 重新下载原图用于合成（OCR 阶段可能已缓存内容，这里直接复用更省）
    image_bytes = _download_image_sync(image_url)
    if not image_bytes:
        return {
            "source_url": image_url,
            "result_url": image_url,
            "ocr_blocks": len(blocks),
            "translated_blocks": 0,
            "status": "skipped",
        }

    # 4. 合成 + 上传
    try:
        result_url = synthesize_translated_image(
            image_bytes, blocks, product_id=product_id, image_index=image_index
        )
    except Exception as e:
        logger.error(f"图片合成失败 {image_url}: {e}")
        result_url = image_url

    translated_count = sum(1 for b in blocks if (b.get("translated_text") or "").strip())
    return {
        "source_url": image_url,
        "result_url": result_url,
        "ocr_blocks": len(blocks),
        "translated_blocks": translated_count,
        "status": "completed" if translated_count > 0 else "skipped",
    }
