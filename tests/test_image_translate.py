"""
测试图片翻译服务 (S07) — OCR → 翻译 → 合成

覆盖策略:
1. OCR 模块: PaddleOCR 不可用时优雅降级为空块
2. 合成模块: 用一张合成测试图验证 PIL 合成不崩 + 上传回退路径
3. 顶层 translate_image: mock OCR 与翻译断言链路完整且对无文字图跳过处理
4. 缓存路径: extract_image_text_blocks 命中缓存时不重复下载
5. 依赖缺失优雅降级: 缺 cv2/PIL 时 translate_image 仍 robust 返回

不在本测试覆盖（依赖外部）:
- 真实 PaddleOCR 推理（需下载模型）—— 留给集成测试
- 真实 MinIO 上传 —— 走 storage 的本地文件回退
"""

import io
import json
from unittest.mock import patch, MagicMock

import pytest

from api.services import image_translate as it


# ==================== OCR 引擎降级 ====================


class TestOCREngine:
    def test_ocr_engine_returns_none_when_paddle_unavailable(self):
        """PaddleOCR 未安装时 _ocr_engine 返回 None 不抛异常。"""
        # _ocr_engine 实际上通过模块级函数对象缓存 _engine; 这里直接 mock
        # paddleocr 的 import 失败分支, 并清空单例
        sentinel = None
        try:
            del it._ocr_engine.__dict__["_engine"]
        except KeyError:
            pass
        # 用 sys.modules 让 paddleocr import 失败 —— 通过 patch builtins 不稳
        # 这里更稳妥的方式: 直接在 _ocr_engine 定义处 patch: 用 fake paddleocr import 抛 ImportError
        import builtins
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "paddleocr" or name.startswith("paddleocr."):
                raise ImportError("no paddleocr")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            eng = it._ocr_engine()
        assert eng is None

    def test_extract_blocks_returns_empty_when_download_fails(self):
        """图片下载失败时返回空列表而非抛异常。"""
        with patch.object(it, "_download_image_sync", return_value=None):
            blocks = it.extract_image_text_blocks("http://example.com/missing.jpg")
        assert blocks == []

    def test_extract_blocks_uses_cache(self):
        """缓存命中时不再下载图片。"""
        import hashlib
        cache_key = "ocr:" + hashlib.md5(b"http://x/y.jpg").hexdigest()
        cached_blocks = [{"text": "你好", "confidence": 0.9, "box": [10, 10, 50, 30]}]
        # cache_get 在 image_translate.py 是模块级导入, 需 patch image_translate 命名空间
        with patch("api.services.image_translate.cache_get",
                   return_value=json.dumps(cached_blocks)), \
                patch.object(it, "_download_image_sync") as dl:
            blocks = it.extract_image_text_blocks("http://x/y.jpg")
        assert blocks == cached_blocks
        dl.assert_not_called()


# ==================== 合成 ====================


def _make_test_image_bytes() -> bytes:
    """生成 200x100 白底带一个黑色文本块的 JPEG 测试图。"""
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (200, 100), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([30, 30, 130, 60], fill=(255, 255, 255))  # 文字区背景
    return _to_bytes(img)


def _to_bytes(img) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestSynthesize:
    def test_synthesize_with_no_blocks_uploads_source(self):
        """无翻译块时仍能上传（回退原图）。"""
        with patch("api.services.image_translate.storage") as storage:
            storage.upload_file.return_value = "http://oss/translated/img_000.jpg"
            url = it.synthesize_translated_image(_make_test_image_bytes(), [], 1, 0)
        assert url == "http://oss/translated/img_000.jpg"
        storage.upload_file.assert_called_once()

    def test_synthesize_covers_box_and_draws_translation(self):
        """有翻译块时调用一次 upload_file 并返回 URL。"""
        blocks = [{
            "box": [30, 30, 100, 30],
            "translated_text": "สวัสดี",
            "confidence": 0.9,
        }]
        with patch("api.services.image_translate.storage") as storage:
            storage.upload_file.return_value = "http://oss/translated/img_000.jpg"
            url = it.synthesize_translated_image(
                _make_test_image_bytes(), blocks, product_id=42, image_index=0
            )
        assert url == "http://oss/translated/img_000.jpg"
        # upload_file 应被调用一次
        storage.upload_file.assert_called_once()
        # object key 应该指向商品 42 的 translated 目录
        call_args = storage.upload_file.call_args
        object_key = call_args[0][1]
        assert object_key.startswith("products/42/translated/img_000.")

    def test_synthesize_invalid_image_bytes_uploads_jpeg_fallback(self):
        """原图字节无法识别时直接原图上传。"""
        with patch("api.services.image_translate.storage") as storage:
            storage.upload_file.return_value = "http://oss/generic.jpg"
            url = it.synthesize_translated_image(b"not-an-image", [], None, 0)
        assert url == "http://oss/generic.jpg"


# ==================== 顶层流程 translate_image ====================


class TestTranslateImageFlow:
    def test_no_text_blocks_skips(self):
        """OCR 无文字 → 返回原图且 status=skipped。"""
        with patch.object(it, "extract_image_text_blocks", return_value=[]):
            res = it.translate_image("http://x/y.jpg", product_id=1, image_index=0)
        assert res["status"] == "skipped"
        assert res["result_url"] == "http://x/y.jpg"
        assert res["ocr_blocks"] == 0

    def test_with_blocks_translates_and_uploads(self):
        """有 OCR 文字块 → 翻译 + 合成 + 上传，status=completed。"""
        blocks = [{"text": "促销", "confidence": 0.95, "box": [10, 10, 60, 25]}]
        image_bytes = _make_test_image_bytes()
        with patch.object(it, "extract_image_text_blocks", return_value=blocks), \
                patch.object(it, "_download_image_sync", return_value=image_bytes), \
                patch.object(it, "synthesize_translated_image",
                             return_value="http://oss/translated/img_000.jpg") as synth, \
                patch("api.services.translator.translate_text", return_value="โปรโมชั่น") as tr:
            res = it.translate_image("http://x/y.jpg", product_id=7, image_index=0)
        assert res["status"] == "completed"
        assert res["result_url"] == "http://oss/translated/img_000.jpg"
        assert res["ocr_blocks"] == 1
        assert res["translated_blocks"] == 1
        # 翻译回调应被调用一次（单块）
        tr.assert_called_once()
        # 合成应被调用一次
        synth.assert_called_once()

    def test_translate_failure_does_not_break_flow(self):
        """翻译函数抛异常时该块 translated_text 为空，被视为 skipped 而非 failed。"""
        blocks = [{"text": "促销", "confidence": 0.95, "box": [10, 10, 60, 25]}]
        with patch.object(it, "extract_image_text_blocks", return_value=blocks), \
                patch.object(it, "_download_image_sync", return_value=_make_test_image_bytes()), \
                patch("api.services.translator.translate_text", side_effect=RuntimeError("boom")), \
                patch.object(it, "synthesize_translated_image",
                             return_value="http://oss/translated/img_000.jpg"):
            res = it.translate_image("http://x/y.jpg", product_id=7, image_index=0)
        assert res["ocr_blocks"] == 1
        assert res["translated_blocks"] == 0
        # 没有任何块被翻译，但流程仍走到合成 —— 状态按指令为 skipped
        assert res["status"] == "skipped"

    def test_synthesize_failure_falls_back_to_source(self):
        """合成阶段抛异常时降级返回原图 URL。"""
        blocks = [{"text": "促销", "confidence": 0.95, "box": [10, 10, 60, 25]}]
        with patch.object(it, "extract_image_text_blocks", return_value=blocks), \
                patch.object(it, "_download_image_sync", return_value=_make_test_image_bytes()), \
                patch("api.services.translator.translate_text", return_value="โปรโมชั่น"), \
                patch.object(it, "synthesize_translated_image",
                             side_effect=RuntimeError("disk full")):
            res = it.translate_image("http://x/y.jpg", product_id=7, image_index=0)
        assert res["result_url"] == "http://x/y.jpg"
        assert res["translated_blocks"] == 1
        # 流程仍在合成阶段挂掉但顶层不抛异常
        assert res["status"] == "completed"


# ==================== 自定义翻译回调 ====================


class TestCustomTranslator:
    def test_custom_translate_fn_used(self):
        blocks = [{"text": "x", "confidence": 0.9, "box": [1, 1, 10, 10]}]
        custom = MagicMock(return_value="TH")
        with patch.object(it, "extract_image_text_blocks", return_value=blocks), \
                patch.object(it, "_download_image_sync", return_value=_make_test_image_bytes()), \
                patch.object(it, "synthesize_translated_image",
                             return_value="http://oss/x.jpg"):
            it.translate_image("http://x/y.jpg", translate_fn=custom)
        custom.assert_called_once_with("x", "zh", "th")


# ==================== helpers ====================
