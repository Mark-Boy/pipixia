"""
上架记录模型
"""

from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from api.database import Base


class Listing(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False, index=True)
    shop_id = Column(Integer, ForeignKey('shops.id'), nullable=False, index=True)
    shopee_item_id = Column(String(50), nullable=True)
    shopee_status = Column(String(20), nullable=True)
    listing_price_thb = Column(Float, nullable=True)
    stock = Column(Integer, nullable=True)
    variation_data = Column(JSON, default=dict)
    audit_status = Column(String(20), default="pending")
    audit_comment = Column(String(500), nullable=True)
    listing_mode = Column(String(20), default="manual")  # manual / auto
    retry_count = Column(Integer, default=0)
    last_error = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    product = relationship("Product", back_populates="listings")
    shop = relationship("Shop", back_populates="listings")
