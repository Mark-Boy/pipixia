"""
媒体路由 — 图片上传/下载/删除（OSS）
"""

import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, status, UploadFile, File, Query, Depends
from sqlalchemy import select

from api.database import async_session
from api.models.product import Product
from api.models.user import User
from api.services.auth import get_current_user_async
from api.services.storage import upload_image, get_storage_stats

router = APIRouter(prefix="/media", tags=["Media"])


@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
    product_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user_async),
):
    """上传图片到 OSS（返回 URL）"""
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

    # 上传到 OSS
    try:
        oss_url = upload_image(
            file_data=content,
            product_id=product_id,
            content_type=file.content_type,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"图片上传失败: {str(e)}",
        )

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
        "url": oss_url,
    }


@router.post("/upload/batch")
async def upload_batch_media(
    files: list[UploadFile] = File(...),
    product_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user_async),
):
    """批量上传图片"""
    urls = []
    for i, file in enumerate(files):
        content = await file.read()
        try:
            url = upload_image(
                file_data=content,
                product_id=product_id,
                file_index=i,
                content_type=file.content_type,
            )
            urls.append({"index": i, "url": url, "filename": file.filename})
        except Exception as e:
            urls.append({"index": i, "url": None, "filename": file.filename, "error": str(e)})

    # 更新产品图片列表
    if product_id and urls:
        async with async_session() as db:
            result = await db.execute(select(Product).where(Product.id == product_id))
            product = result.scalar_one_or_none()
            if product:
                existing = product.images_oss_keys or []
                new_urls = [u["url"] for u in urls if u["url"]]
                product.images_oss_keys = existing + new_urls
                await db.commit()

    return {
        "status": "success",
        "uploaded": len([u for u in urls if u["url"]]),
        "total": len(urls),
        "files": urls,
    }


@router.delete("")
async def delete_media(
    url: str = Query(..., description="图片 URL"),
    current_user: User = Depends(get_current_user_async),
):
    """删除 OSS 图片"""
    from api.services.storage import storage

    # 从 URL 提取 object_key
    parts = url.split("/")
    if len(parts) >= 5:
        object_key = "/".join(parts[-3:])
    else:
        object_key = url

    storage.delete_file(object_key)

    return {
        "status": "success",
        "message": "图片已删除",
    }


@router.get("/presigned-url")
async def get_presigned_url(
    url: str = Query(..., description="图片 URL"),
    expires: int = Query(3600, ge=60, le=86400),
    current_user: User = Depends(get_current_user_async),
):
    """获取图片临时访问 URL"""
    from api.services.storage import storage

    parts = url.split("/")
    if len(parts) >= 5:
        object_key = "/".join(parts[-3:])
    else:
        object_key = url

    presigned_url = storage.get_presigned_url(object_key, expires)

    return {
        "url": presigned_url,
        "expires_in": expires,
    }


@router.get("/stats")
async def get_media_stats(
    current_user: User = Depends(get_current_user_async),
):
    """获取存储统计"""
    return get_storage_stats()
