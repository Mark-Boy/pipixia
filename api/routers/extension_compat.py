"""
扩展兼容端点 - 供 Chrome 扩展回传采集数据
路径前缀: /api/v1/open/... (匹配扩展 formatUrl 行为)
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
import json
import logging

from api.routers.products import collect_from_extension
from api.database import async_session
from api.models.product import Product
from api.models.shop import Shop
from api.models.user import User
from api.services.auth import get_current_user_async
from sqlalchemy import select

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/open", tags=["Extension Compatibility"])


class ExtensionCollectItem(BaseModel):
    """扩展端采集单品数据结构"""
    pageContent: str = ""
    itemId: str = ""
    source: str = "yangkeduo"
    afterUrl: str = ""
    productExtInfo: Optional[Dict[str, Any]] = None


@router.post("/fetch/pfti")
async def extension_fetch_pfti(
    data: ExtensionCollectItem,
    shop_id: int = Query(..., description="目标店铺 ID"),
    current_user: User = Depends(get_current_user_async),
):
    """
    兼容扩展自动采集回传路径: POST /open/fetch/pfti
    扩展发送: {pageContent, itemId, source, afterUrl, productExtInfo}
    """
    return await collect_from_extension(data, shop_id, current_user)


@router.post("/niu/push_collect_box")
async def extension_push_collect_box(
    payload: Dict[str, Any],
    shop_id: int = Query(..., description="目标店铺 ID"),
    current_user: User = Depends(get_current_user_async),
):
    """
    兼容扩展批量采集箱回传路径: POST /open/niu/push_collect_box
    扩展发送: {isAutoPublish: 1, itemSimpleDetails: "{...}"}
    """
    item_simple_details = payload.get("itemSimpleDetails")
    if not item_simple_details:
        raise HTTPException(status_code=400, detail="缺少 itemSimpleDetails")

    try:
        items = json.loads(item_simple_details) if isinstance(item_simple_details, str) else item_simple_details
    except Exception:
        raise HTTPException(status_code=400, detail="itemSimpleDetails 解析失败")

    results = []
    for item_key, item_data in items.items():
        item_url = item_data.get("itemUrl")
        if not item_url:
            continue
        try:
            collect_data = ExtensionCollectItem(
                pageContent="",
                itemId=item_data.get("itemId", ""),
                source=item_data.get("source", "yangkeduo"),
                afterUrl=item_url,
            )
            result = await collect_from_extension(collect_data, shop_id, current_user)
            results.append({"itemId": item_data.get("itemId"), "result": result})
        except Exception as e:
            results.append({"itemId": item_data.get("itemId"), "error": str(e)})

    return {
        "status": "completed",
        "collected": len([r for r in results if r.get("result", {}).get("status") == "success"]),
        "total": len(results),
        "details": results,
    }


@router.get("/niu/check_login")
async def extension_check_login(
    current_user: User = Depends(get_current_user_async),
):
    """
    兼容扩展检查登录状态: GET /open/niu/check_login
    扩展用此判断用户是否已在 pipixia 登录
    """
    return {
        "result": "success",
        "shopInfo": {
            "id": current_user.id,
            "name": current_user.username,
            "platform": "pipixia",
        }
    }


@router.get("/niu/get_auth_url")
async def extension_get_auth_url(
    current_user: User = Depends(get_current_user_async),
):
    """
    兼容扩展获取授权 URL: GET /open/niu/get_auth_url
    扩展用此引导用户登录 pipixia
    """
    # 前端登录页 URL
    frontend_url = "http://localhost:9000/login"
    return {
        "result": "success",
        "authUrl": frontend_url,
    }