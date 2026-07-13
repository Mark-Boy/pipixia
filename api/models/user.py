"""
用户模型
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from api.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), server_default='operator')  # admin / operator / viewer
    is_active = Column(Boolean, server_default=text('true'))
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    shops = relationship("Shop", back_populates="owner", foreign_keys="Shop.user_id", cascade="all, delete-orphan")
    pdd_accounts = relationship("PddAccount", back_populates="user", cascade="all, delete-orphan")
