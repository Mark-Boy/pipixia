"""
认证服务 — JWT Token 管理
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from jose import JWTError, jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from api.models.user import User
from api.config import get_settings

settings = get_settings()
security = HTTPBearer()


# ==================== Token 创建 ====================

def create_access_token(user_id: str, role: str, expires_delta: Optional[timedelta] = None) -> str:
    """创建 Access Token（短期，2h）"""
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {
        "sub": user_id,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    return pyjwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """创建 Refresh Token（长期，7d，用于轮换）"""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    return pyjwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ==================== Token 验证 ====================

def decode_token(token: str) -> dict:
    """解码并验证 Token"""
    try:
        payload = pyjwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 格式错误",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ==================== 密码哈希 ====================

def get_password_hash(password: str) -> str:
    """BCrypt 密码哈希"""
    import bcrypt
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    import bcrypt
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


# ==================== 当前用户获取 ====================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = None,
) -> User:
    """JWT 鉴权中间件"""
    token = credentials.credentials
    payload = decode_token(token)
    
    # 只接受 access token
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 Token 类型",
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 无效",
        )
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户不存在或已禁用",
        )
    
    return user


# ==================== 权限检查 ====================

def require_role(*roles: str):
    """角色权限装饰器"""
    from functools import wraps
    from fastapi import Request
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request: Request = kwargs.get("request") or args[1]
            current_user = kwargs.get("current_user")
            if not current_user:
                # 尝试从依赖注入获取
                from fastapi import Depends
                try:
                    current_user = await get_current_user(
                        credentials=HTTPAuthorizationCredentials(
                            scheme="Bearer",
                            token=request.headers.get("Authorization", "").replace("Bearer ", "")
                        ),
                        db=kwargs.get("db"),
                    )
                except Exception:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="未授权",
                    )
            
            if current_user.role not in roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"需要角色: {'/'.join(roles)}",
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator
