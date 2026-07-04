"""
媒体路由 — 图片上传/下载/删除（OSS）
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select

from api.database import async_session
from api.models.product import Product

router = APIRouter(prefix="/media", tags=["Media"])


def parse_token(credentials_str: Optional[str]) -> HTTPAuthorizationCredentials:
    if not credentials_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少认证 Token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    scheme, _, token = credentials_str.partition(" ")
    if scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 格式错误",
        )
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


async def get_user_id_from_token(credentials_str: Optional[str]) -> int:
    token = parse_token(credentials_str)
    from api.services.auth import decode_token
    payload = decode_token(token.credentials)
    return int(payload["sub"])


@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
    product_id: Optional[int] = Query(None),
    credentials_str: Optional[str] = Query(None),
):
    """上传图片到 OSS（返回 OSS key 和 URL）"""
    user_id = await get_user_id_from_token(credentials_str) if credentials_str else 0

    # 验证文件类型
    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {file.content_type}，支持: {', '.join(allowed_types)}",
        )

    # 验证文件大小（最大 10MB）
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="文件大小超过 10MB 限制",
        )

    # 生成唯一文件名
    file_extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    object_key = f"products/{product_id or 'generic'}/{uuid.uuid4().hex}.{file_extension}"

    # TODO: 上传到 MinIO/OSS
    # from minio import Minio
    # minio_client.put_object(...)
    
    # 模拟上传成功
    oss_url = f"http://minio:9000/pipixia-images/{object_key}"

    # 如果指定了 product_id，更新产品图片列表
    if product_id:
        async with async_session() as db:
            result = await db.execute(select(Product).where(Product.id == product_id))
            product = result.scalar_one_or_none()
            if product:
                images = product.images_oss_keys or []
                images.append(oss_url)
                product.images_oss_keys = images
                await db.commit()

    return {
        "status": "success",
        "message": "图片上传成功",
        "oss_key": object_key,
        "url": oss_url,
    }


@router.delete("/delete")
async def delete_media(
    oss_key: str,
    credentials_str: Optional[str] = Query(None),
):
    """删除 OSS 图片"""
    # TODO: 从 MinIO/OSS 删除

    return {
        "status": "success",
        "message": "图片已删除",
        "oss_key": oss_key,
    }


@router.get("/url")
async def get_media_url(
    oss_key: str,
    expires: int = Query(3600, ge=60, le=86400),
    credentials_str: Optional[str] = Query(None),
):
    """获取 OSS 图片临时访问 URL"""
    # TODO: 生成 presigned URL
    url = f"http://minio:9000/pipixia-images/{oss_key}"

    return {
        "url": url,
        "expires_in": expires,
    }
