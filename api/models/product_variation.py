"""
商品规格模型
"""

from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, ForeignKey, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from api.database import Base


class ProductVariation(Base):
    """商品规格/变体 (Variant/SKU)"""
    __tablename__ = "product_variations"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey('shops.id'), nullable=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False, index=True)
    name = Column(String(200), nullable=True)  # 规格名称 (如 "颜色: 红色")
    sku = Column(String(100), nullable=True)  # SKU 编码
    price_add = Column(Float, nullable=True)  # 加价
    stock = Column(Integer, nullable=True)  # 库存
    weight = Column(Float, nullable=True)  # 重量 (g)
    dim_l = Column(Float, nullable=True)  # 长 (cm)
    dim_w = Column(Float, nullable=True)  # 宽 (cm)
    dim_h = Column(Float, nullable=True)  # 高 (cm)
    shopee_variation_id = Column(String(50), nullable=True)  # Shopee 规格 ID
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    shop = relationship("Shop", back_populates="variations")
    product = relationship("Product", back_populates="variations")
