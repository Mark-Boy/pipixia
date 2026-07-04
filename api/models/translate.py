"""
翻译记录模型
"""

from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from api.database import Base


class Translate(Base):
    __tablename__ = "translates"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, nullable=False, index=True)
    translate_type = Column(String(20), nullable=False)  # title / description / image
    source_text_hash = Column(String(64), nullable=False, index=True)
    source_text = Column(String(5000), nullable=False)
    target_text = Column(String(5000), nullable=True)
    source_image_url = Column(String(500), nullable=True)
    target_image_url = Column(String(500), nullable=True)
    status = Column(String(20), default="pending")  # pending / success / failed
    confidence_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
