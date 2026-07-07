"""
配置路由 — 系统设置管理
"""

import yaml
import json
from typing import Optional, Dict, Any
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func

from api.database import async_session
from api.models.product import Product
from api.models.risk_log import RiskLog
from api.models.user import User
from api.services.auth import get_current_user_async

router = APIRouter(prefix="/settings", tags=["Settings"])

# 配置文件路径
SETTINGS_FILE = Path(__file__).parent.parent.parent / "config" / "settings.yaml"


@router.get("")
async def get_settings(
    current_user: User = Depends(get_current_user_async),
):
    """获取系统配置"""
    if not SETTINGS_FILE.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配置文件不存在",
        )

    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        settings = yaml.safe_load(f)

    # 隐藏敏感字段（生产环境）
    if "llm" in settings and settings["llm"].get("api_key"):
        settings["llm"]["api_key"] = settings["llm"]["api_key"][:6] + "****"

    return settings


@router.put("")
async def update_settings(
    data: Dict[str, Any],
    current_user: User = Depends(get_current_user_async),
):
    """更新系统配置"""
    if not SETTINGS_FILE.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="配置文件不存在",
        )

    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        settings = yaml.safe_load(f) or {}

    # 更新配置
    for key, value in data.items():
        if isinstance(value, dict) and key in settings:
            settings[key].update(value)
        else:
            settings[key] = value

    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        yaml.dump(settings, f, allow_unicode=True, default_flow_style=False)

    return {
        "status": "updated",
        "message": "配置已更新",
    }


@router.get("/risk-words")
async def get_risk_words(
    current_user: User = Depends(get_current_user_async),
):
    """获取风控词库"""
    risk_file = Path(__file__).parent.parent.parent / "config" / "risk_words.json"
    
    if not risk_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="风控词库不存在",
        )

    with open(risk_file, "r", encoding="utf-8") as f:
        words = json.load(f)

    return words


@router.get("/exchange-rate")
async def get_exchange_rate(
    force_refresh: bool = Query(False, description="强制刷新汇率"),
    current_user: User = Depends(get_current_user_async),
):
    """获取汇率（CNY → THB）"""
    try:
        from api.services.exchange import fetch_exchange_rate, get_exchange_rate as get_rate_info
        if force_refresh:
            # 清除缓存后重新获取
            from api.services.cache import cache_delete
            cache_delete("exchange:CNY_THB")
        rate_info = get_rate_info()
        rate_info["forced_refresh"] = force_refresh
        return rate_info
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"汇率服务不可用: {str(e)}",
        )


@router.get("/circuit-breaker/status")
async def get_circuit_breaker_status(
    current_user: User = Depends(get_current_user_async),
):
    """获取熔断状态（哪些商品被拦截及原因）"""
    async with async_session() as db:
        # 查询被拦截的商品
        result = await db.execute(
            select(Product).where(
                Product.risk_status == "block",
                Product.status != "removed",
            ).order_by(Product.created_at.desc())
        )
        blocked = result.scalars().all()

        # 查询低利润商品
        low_profit_result = await db.execute(
            select(Product).where(
                Product.profit_margin != None,
                Product.profit_margin < 10.0,
                Product.status == "audited",
            ).order_by(Product.profit_margin.asc())
        )
        low_profit = low_profit_result.scalars().all()

    return {
        "blocked_products": [
            {
                "id": p.id,
                "title": p.title_zh,
                "risk_status": p.risk_status,
                "profit_margin": p.profit_margin,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in blocked
        ],
        "low_profit_products": [
            {
                "id": p.id,
                "title": p.title_zh,
                "profit_margin": p.profit_margin,
                "threshold": 10.0,
            }
            for p in low_profit
        ],
        "summary": {
            "total_blocked": len(blocked),
            "total_low_profit": len(low_profit),
        },
    }


@router.post("/risk-words/add")
async def add_risk_word(
    word: str = Query(..., description="风控词"),
    word_type: str = Query("brand", description="词类型: brand / prohibited"),
    current_user: User = Depends(get_current_user_async),
):
    """添加风控词"""
    risk_file = Path(__file__).parent.parent.parent / "config" / "risk_words.json"
    
    if not risk_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="风控词库不存在",
        )

    with open(risk_file, "r", encoding="utf-8") as f:
        words = json.load(f)

    if word_type == "prohibited":
        if word not in words.get("prohibited_words", []):
            words.setdefault("prohibited_words", []).append(word)
    elif word_type == "brand":
        if word not in words.get("brand_keywords", []):
            words.setdefault("brand_keywords", []).append(word)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的词类型",
        )

    with open(risk_file, "w", encoding="utf-8") as f:
        json.dump(words, f, ensure_ascii=False, indent=2)

    return {"status": "added", "message": f"已添加 {word_type}: {word}"}


@router.get("/risk-logs")
async def get_risk_logs(
    risk_type: Optional[str] = Query(None, description="风险类型: brand / profit / category"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user_async),
):
    """获取风控日志"""
    async with async_session() as db:
        query = select(RiskLog)
        if risk_type:
            query = query.where(RiskLog.risk_type == risk_type)

        # 总数
        count_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar() or 0

        # 分页
        query = query.order_by(RiskLog.created_at.desc())
        query = query.offset((page - 1) * size).limit(size)
        result = await db.execute(query)
        logs = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "size": size,
        "logs": [
            {
                "id": log.id,
                "product_id": log.product_id,
                "risk_type": log.risk_type,
                "risk_detail": log.risk_detail,
                "action_taken": log.action_taken,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
    }
