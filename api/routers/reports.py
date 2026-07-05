"""
报告路由 — 日报 + 财务报表 + 利润校准
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func

from api.database import async_session
from api.models.product import Product
from api.models.listing import Listing
from api.models.profit_calibration import ProfitCalibration
from api.models.user import User
from api.services.auth import get_current_user_async

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/daily")
async def get_daily_report(
    date: str = Query(None),  # format: YYYY-MM-DD
    current_user: User = Depends(get_current_user_async),
):
    """日报"""
    async with async_session() as db:
        # 统计今日数据
        from datetime import datetime, timedelta
        today = datetime.strptime(date, "%Y-%m-%d").date() if date else datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        tomorrow_start = today_start + timedelta(days=1)

        # 商品统计
        total_products = await db.execute(
            select(func.count()).select_from(Product)
        )
        total_products = total_products.scalar() or 0

        pending = await db.execute(
            select(func.count()).where(Product.status == "pending")
        )
        pending = pending.scalar() or 0

        audited = await db.execute(
            select(func.count()).where(Product.status == "audited")
        )
        audited = audited.scalar() or 0

        # 上架统计
        new_listings = await db.execute(
            select(func.count()).where(
                Listing.created_at >= today_start,
                Listing.created_at < tomorrow_start,
            )
        )
        new_listings = new_listings.scalar() or 0

        success_listings = await db.execute(
            select(func.count()).where(
                Listing.created_at >= today_start,
                Listing.created_at < tomorrow_start,
                Listing.shopee_status == "success",
            )
        )
        success_listings = success_listings.scalar() or 0

        # 汇率
        exchange_rate = 5.0  # 实际应查询实时汇率

    return {
        "report_date": today.isoformat(),
        "statistics": {
            "total_products": total_products,
            "pending_review": pending,
            "audited": audited,
            "new_listings_today": new_listings,
            "successful_listings": success_listings,
        },
        "exchange_rate": {
            "cny_to_thb": exchange_rate,
        },
    }


@router.get("/finance")
async def get_finance_report(
    start_date: str = Query("2024-01-01"),
    end_date: str = Query(None),
    current_user: User = Depends(get_current_user_async),
):
    """财务对账报表"""
    async with async_session() as db:
        from datetime import datetime
        end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.now()
        start = datetime.strptime(start_date, "%Y-%m-%d")

        # 汇总财务数据
        result = await db.execute(
            select(
                func.sum(Product.price_thb).label("total_revenue"),
                func.sum(Product.cost_cny * 5).label("total_cost"),  # CNY * 5 = THB
                func.count(Product.id).label("product_count"),
            ).where(
                Product.created_at >= start,
                Product.created_at <= end,
            )
        )
        row = result.fetchone()

        total_revenue = row.total_revenue or 0
        total_cost = row.total_cost or 0
        product_count = row.product_count or 0
        profit = total_revenue - total_cost

    return {
        "period": {
            "start": start_date,
            "end": end.isoformat(),
        },
        "summary": {
            "total_products": product_count,
            "total_revenue_thb": round(total_revenue, 2),
            "total_cost_thb": round(total_cost, 2),
            "gross_profit_thb": round(profit, 2),
            "profit_margin": round((profit / total_revenue * 100) if total_revenue > 0 else 0, 2),
            "exchange_rate": 5.0,
        },
    }


@router.get("/profit-calibration", response_model=dict)
async def get_profit_calibration(
    shop_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user_async),
):
    """利润校准报告"""
    async with async_session() as db:
        query = select(ProfitCalibration)
        if shop_id:
            query = query.where(ProfitCalibration.shop_id == shop_id)

        # 总数
        count_result = await db.execute(select(func.count()).select_from(query.subquery()))
        total = count_result.scalar() or 0

        # 分页
        query = query.order_by(ProfitCalibration.created_at.desc())
        query = query.offset((page - 1) * size).limit(size)
        result = await db.execute(query)
        calibrations = result.scalars().all()

    return {
        "total": total,
        "page": page,
        "size": size,
        "calibrations": [
            {
                "id": cal.id,
                "shop_id": cal.shop_id,
                "category_id": cal.category_id,
                "estimated_profit": cal.estimated_profit,
                "actual_profit": cal.actual_profit,
                "deviation": cal.deviation,
                "created_at": cal.created_at.isoformat() if cal.created_at else None,
            }
            for cal in calibrations
        ],
    }


@router.get("/summary")
async def get_summary(
    current_user: User = Depends(get_current_user_async),
):
    """Dashboard 汇总数据"""
    async with async_session() as db:
        # 总体统计
        total_products_result = await db.execute(select(func.count()).select_from(Product))
        total_products = total_products_result.scalar() or 0

        pending_result = await db.execute(
            select(func.count()).where(Product.status == "pending")
        )
        pending = pending_result.scalar() or 0

        # 最近7天上架趋势
        from datetime import datetime, timedelta
        week_ago = datetime.now() - timedelta(days=7)
        recent_listings_result = await db.execute(
            select(func.count()).where(Listing.created_at >= week_ago)
        )
        recent_listings = recent_listings_result.scalar() or 0

    return {
        "total_products": total_products,
        "pending_review": pending,
        "recent_listings_7d": recent_listings,
    }
