"""
媒体路由
"""

from fastapi import APIRouter, UploadFile, File

router = APIRouter(prefix="/media", tags=["Media"])


@router.post("/upload")
async def upload_media(file: UploadFile = File(...)):
    """上传图片（返回 OSS key）"""
    # TODO: 实现
    raise NotImplementedError("图片上传功能待实现")
