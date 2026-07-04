"""
报告路由
"""

from fastapi import APIRouter

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/daily")
async def get_daily_report():
    """日报"""
    # TODO: 实现
    raise NotImplementedError("日报功能待实现")


@router.get("/finance")
async def get_finance_report():
    """财务对账报表"""
    # TODO: 实现
    raise NotImplementedError("财务报表功能待实现")


@router.get("/profit-calibration")
async def get_profit_calibration():
    """利润校准报告"""
    # TODO: 实现
    raise NotImplementedError("利润校准功能待实现")
