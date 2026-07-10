"""
店铺模型
"""

from sqlalchemy import Column, Integer, String, Boolean, JSON, DateTime, ForeignKey, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from api.database import Base


class Shop(Base):
    __tablename__ = "shops"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    shop_name = Column(String(100), nullable=False)
    platform = Column(String(20), server_default='shopee_th')  # shopee_th, shopee_vn, shopee_sg, shopee_my, shopee_id, shopee_ph
    shop_token_encrypted = Column(String(500), nullable=False)
    shop_id = Column(String(50), nullable=True)  # Shopee 店铺 ID
    is_active = Column(Boolean, server_default=text('true'))
    config = Column(JSON, server_default=text("'{}'::json"))  # 店铺配置
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    owner = relationship("User", back_populates="shops")
    products = relationship("Product", back_populates="shop", cascade="all, delete-orphan")
    listings = relationship("Listing", back_populates="shop", cascade="all, delete-orphan")
    variations = relationship(
        "ProductVariation",
        back_populates="shop",
        cascade="all, delete-orphan",
        primaryjoin="ProductVariation.shop_id == Shop.id",  # type: ignore
    )
    profit_calibrations = relationship("ProfitCalibration", back_populates="shop", cascade="all, delete-orphan")
