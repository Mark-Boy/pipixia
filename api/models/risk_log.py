"""
风控日志模型
"""

from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from api.database import Base


class RiskLog(Base):
    __tablename__ = "risk_logs"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False, index=True)
    risk_type = Column(String(20), nullable=False)  # brand / prohibited / profit / category
    risk_detail = Column(String(500), nullable=False)
    action_taken = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    product = relationship("Product", back_populates="risk_logs")
