"""
配置路由 — 系统设置管理
"""

import yaml
from typing import Optional, Dict, Any
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter(prefix="/settings", tags=["Settings"])

# 配置文件路径
SETTINGS_FILE = Path(__file__).parent.parent.parent / "config" / "settings.yaml"


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


@router.get("")
async def get_settings(
    credentials_str: Optional[str] = Query(None),
):
    """获取系统配置"""
    user_id = await get_user_id_from_token(credentials_str) if credentials_str else 0

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
    credentials_str: Optional[str] = Query(None),
):
    """更新系统配置"""
    user_id = await get_user_id_from_token(credentials_str) if credentials_str else 0

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
    credentials_str: Optional[str] = Query(None),
):
    """获取风控词库"""
    import json
    risk_file = Path(__file__).parent.parent.parent / "config" / "risk_words.json"
    
    if not risk_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="风控词库不存在",
        )

    with open(risk_file, "r", encoding="utf-8") as f:
        words = json.load(f)

    return words


@router.post("/risk-words/add")
async def add_risk_word(
    word: str,
    word_type: str = Query("brand"),  # brand / prohibited
    credentials_str: Optional[str] = Query(None),
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
