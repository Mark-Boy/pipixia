"""
利润校准模型
"""

from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from api.database import Base


class ProfitCalibration(Base):
    __tablename__ = "profit_calibration"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, nullable=False, index=True)
    category_id = Column(Integer, nullable=True)
    estimated_profit = Column(Float, nullable=False)
    actual_profit = Column(Float, nullable=True)
    deviation = Column(Float, nullable=True)  # 偏差
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    shop = relationship("Shop", back_populates="profit_calibrations")
