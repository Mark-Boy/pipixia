"""
商品模型
"""

from sqlalchemy import Column, Integer, String, Float, JSON, DateTime
from sqlalchemy.sql import func
from api.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, nullable=False, index=True)
    source_platform = Column(String(20), nullable=False)  # 1688 / pdd
    source_item_id = Column(String(100), nullable=False)
    title_zh = Column(String(255), nullable=False)
    title_th = Column(String(500), nullable=True)
    description_zh = Column(String(5000), nullable=True)
    description_th = Column(String(5000), nullable=True)
    category_id = Column(Integer, nullable=True)
    images_oss_keys = Column(JSON, default=list)
    price_cny = Column(Float, nullable=False)
    price_thb = Column(Float, nullable=False)
    cost_cny = Column(Float, nullable=False)
    profit_margin = Column(Float, nullable=True)  # 利润率 %
    risk_status = Column(String(20), default="pending")  # pending / pass / block
    status = Column(String(20), default="pending")  # pending / auditing / listed / blocked
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
