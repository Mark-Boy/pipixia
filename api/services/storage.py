"""
对象存储服务 — 统一的 OSS/S3/MinIO 接口

支持 MinIO（开发环境）和阿里云 OSS / AWS S3（生产环境）
"""

import io
import logging
from typing import BinaryIO, Optional
from pathlib import Path

from api.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class StorageService:
    """对象存储服务"""

    def __init__(self):
        self._client = None
        self._bucket = settings.MINIO_BUCKET

    def _get_client(self):
        """懒加载 MinIO 客户端"""
        if self._client is None:
            try:
                from minio import Minio
                from minio.error import S3Error

                self._client = Minio(
                    settings.MINIO_ENDPOINT,
                    access_key=settings.MINIO_ACCESS_KEY,
                    secret_key=settings.MINIO_SECRET_KEY,
                    secure=False,  # 开发环境用 HTTP
                )

                # 确保 bucket 存在
                if not self._client.bucket_exists(self._bucket):
                    self._client.make_bucket(self._bucket)
                    logger.info(f"创建 MinIO bucket: {self._bucket}")

            except ImportError:
                logger.warning("MinIO 未安装，使用本地文件系统回退")
                self._client = "local"
            except Exception as e:
                logger.warning(f"MinIO 连接失败，使用本地文件系统回退: {e}")
                self._client = "local"

        return self._client

    def upload_file(
        self,
        file_data: bytes,
        object_key: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        上传文件
        
        Args:
            file_data: 文件二进制数据
            object_key: 对象键名（路径）
            content_type: MIME 类型
            
        Returns:
            对象 URL
        """
        client = self._get_client()

        if client == "local":
            # 本地文件系统回退
            return self._upload_local(file_data, object_key, content_type)

        try:
            from minio.error import S3Error

            import io
            stream = io.BytesIO(file_data)
            self._client.put_object(
                self._bucket,
                object_key,
                stream,
                length=len(file_data),
                content_type=content_type,
            )
            url = f"http://{settings.MINIO_ENDPOINT}/{self._bucket}/{object_key}"
            logger.info(f"文件上传成功: {object_key}")
            return url

        except S3Error as e:
            logger.error(f"MinIO 上传失败: {e}")
            raise
        except Exception as e:
            logger.error(f"文件上传失败，回退到本地: {e}")
            return self._upload_local(file_data, object_key, content_type)

    def _upload_local(self, file_data: bytes, object_key: str, content_type: str) -> str:
        """本地文件系统存储（开发回退）"""
        upload_dir = Path(__file__).parent.parent.parent / "data" / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / object_key
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(file_data)

        url = f"http://localhost:8000/data/uploads/{object_key}"
        logger.info(f"本地文件上传成功: {object_key}")
        return url

    def delete_file(self, object_key: str) -> bool:
        """删除文件"""
        client = self._get_client()

        if client == "local":
            file_path = Path(__file__).parent.parent.parent / "data" / "uploads" / object_key
            if file_path.exists():
                file_path.unlink()
                return True
            return False

        try:
            self._client.remove_object(self._bucket, object_key)
            logger.info(f"文件删除成功: {object_key}")
            return True
        except Exception as e:
            logger.error(f"文件删除失败: {e}")
            return False

    def get_presigned_url(
        self,
        object_key: str,
        expires: int = 3600,
    ) -> str:
        """
        获取预签名 URL
        
        Args:
            object_key: 对象键名
            expires: 过期时间（秒）
            
        Returns:
            预签名 URL
        """
        client = self._get_client()

        if client == "local":
            return f"http://localhost:8000/data/uploads/{object_key}"

        try:
            url = self._client.presigned_get_object(
                self._bucket,
                object_key,
                expires=expires,
            )
            return url
        except Exception as e:
            logger.error(f"获取预签名 URL 失败: {e}")
            return f"http://{settings.MINIO_ENDPOINT}/{self._bucket}/{object_key}"

    def list_files(self, prefix: str = "") -> list[str]:
        """列出指定前缀的文件"""
        client = self._get_client()

        if client == "local":
            upload_dir = Path(__file__).parent.parent.parent / "data" / "uploads"
            files = []
            for f in upload_dir.rglob("*"):
                if f.is_file():
                    rel = f.relative_to(upload_dir)
                    files.append(str(rel))
            return files

        try:
            objects = self._client.list_objects(
                self._bucket,
                prefix=prefix,
                recursive=True,
            )
            return [obj.object_name for obj in objects]
        except Exception as e:
            logger.error(f"列出文件失败: {e}")
            return []


# 全局单例
storage = StorageService()


def upload_image(
    file_data: bytes,
    product_id: Optional[int] = None,
    file_index: int = 0,
    content_type: str = "image/jpeg",
) -> str:
    """
    上传图片到 OSS
    
    Args:
        file_data: 图片二进制数据
        product_id: 商品 ID
        file_index: 图片序号（第几张图）
        content_type: MIME 类型
        
    Returns:
        对象 URL
    """
    ext = "jpg"
    if "png" in content_type:
        ext = "png"
    elif "webp" in content_type:
        ext = "webp"
    elif "gif" in content_type:
        ext = "gif"

    prefix = f"products/{product_id or 'generic'}" if product_id else "products/generic"
    object_key = f"{prefix}/img_{file_index:03d}.{ext}"

    return storage.upload_file(file_data, object_key, content_type)


def upload_batch_images(
    files: list[tuple[bytes, str]],
    product_id: Optional[int] = None,
) -> list[str]:
    """
    批量上传图片
    
    Args:
        files: [(file_data, content_type), ...]
        product_id: 商品 ID
        
    Returns:
        图片 URL 列表
    """
    urls = []
    for i, (file_data, content_type) in enumerate(files):
        url = upload_image(file_data, product_id, i, content_type)
        urls.append(url)
    return urls


def get_storage_stats() -> dict:
    """获取存储统计"""
    files = storage.list_files()
    return {
        "total_files": len(files),
        "bucket": settings.MINIO_BUCKET,
        "endpoint": settings.MINIO_ENDPOINT,
    }


def upload_image_from_url(image_url: str, product_id: Optional[int] = None) -> Optional[str]:
    """
    从 URL 下载图片并上传到对象存储

    Args:
        image_url: 图片 URL
        product_id: 商品 ID

    Returns:
        上传后的对象 URL，失败返回 None
    """
    import httpx
    from urllib.parse import urlparse

    try:
        # 下载图片
        resp = httpx.get(image_url, timeout=15.0)
        resp.raise_for_status()
        file_data = resp.content

        # 确定文件扩展名
        ext = "jpg"
        content_type = resp.headers.get("content-type", "")
        if "png" in content_type:
            ext = "png"
        elif "webp" in content_type:
            ext = "webp"
        elif "gif" in content_type:
            ext = "gif"

        # 生成 object key
        prefix = f"products/{product_id or 'generic'}" if product_id else "products/generic"
        object_key = f"{prefix}/img_{hash(image_url) % 10000:04d}.{ext}"

        return storage.upload_file(file_data, object_key, content_type)
    except Exception as e:
        logger.warning(f"图片下载上传失败 {image_url}: {e}")
        return None
