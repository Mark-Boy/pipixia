"""
拼多多采集账号模型
"""

from sqlalchemy import Column, String, Boolean, DateTime, Text, Integer, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from api.database import Base


class PddAccount(Base):
    """拼多多采集账号表"""
    __tablename__ = "pdd_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # 账号基础信息
    account_name = Column(String(64), nullable=False, comment="账号备注名")
    phone = Column(String(11), nullable=True, comment="手机号")
    notes = Column(Text, nullable=True, comment="备注")

    # 登录状态
    login_status = Column(String(20), default="not_logged_in", nullable=False, comment="not_logged_in / logged_in / expired / error")
    storage_state = Column(Text, nullable=True, comment="Playwright storage state (JSON)，包含 cookies、localStorage 等")
    last_login_at = Column(DateTime, nullable=True, comment="最后登录时间")
    expires_at = Column(DateTime, nullable=True, comment="登录态过期时间")

    # 状态
    is_active = Column(Boolean, default=True, nullable=False)

    # 时间戳
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # 关系
    user = relationship("User", back_populates="pdd_accounts")

    def __repr__(self):
        return f"<PddAccount(id={self.id}, name='{self.account_name}', status='{self.login_status}')>"