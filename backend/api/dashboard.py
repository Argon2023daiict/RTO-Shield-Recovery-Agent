"""
Agentic Dashboard API
Natural language query interface + analytics endpoints.
"""

from typing import Optional
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from pydantic import BaseModel

from backend.database.connection import get_async_session
from backend.database.models import (
    Order, Customer, AgentAction, OrderStatus, RiskLevel, PaymentMethod
)
from backend.agents.orchestrator import AgentOrchestrator

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

_orchestrator = None


def get_orchestrator() -> AgentOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator


class ChatQuery(BaseModel):
    message: str


@router.post("/chat", response_model=dict)
async def chat_with_dashboard(query: ChatQuery):
    """
    Natural language interface for the merchant dashboard.
    Ask questions like:
    - "What are my top 5 high-risk COD orders today?"
    - "How much have I lost to RTO this month?"
    - "Which customers have the highest return rates?"
    - "Show me the recovery success rate"
    """
    orchestrator = get_orchestrator()
    result = orchestrator.query_dashboard(query.message)
    return result


@router.get("/analytics/summary", response_model=dict)
async def get_analytics_summary(
    session: AsyncSession = Depends(get_async_session)
):
    """Get comprehensive analytics summary for the dashboard."""

    # Order counts
    total_orders = await session.execute(select(func.count(Order.id)))
    total_count = total_orders.scalar() or 0

    cod_orders = await session.execute(
        select(func.count(Order.id)).where(Order.payment_method == PaymentMethod.COD)
    )
    cod_count = cod_orders.scalar() or 0

    # Revenue
    total_revenue = await session.execute(select(func.sum(Order.total_amount)))
    revenue = total_revenue.scalar() or 0

    # RTO stats
    rto_statuses = [
        OrderStatus.RTO_INITIATED, OrderStatus.RTO_IN_TRANSIT,
        OrderStatus.RTO_RECEIVED, OrderStatus.RECOVERY_INITIATED,
    ]
    rto_count_result = await session.execute(
        select(func.count(Order.id)).where(Order.status.in_(rto_statuses))
    )
    rto_count = rto_count_result.scalar() or 0

    rto_cost_result = await session.execute(
        select(func.sum(Order.total_rto_cost)).where(Order.status.in_(rto_statuses))
    )
    rto_cost = rto_cost_result.scalar() or 0

    rto_revenue_result = await session.execute(
        select(func.sum(Order.total_amount)).where(Order.status.in_(rto_statuses))
    )
    rto_revenue_lost = rto_revenue_result.scalar() or 0

    # Risk distribution
    risk_distribution = {}
    for level in RiskLevel:
        count_result = await session.execute(
            select(func.count(Order.id)).where(Order.risk_level == level)
        )
        count = count_result.scalar() or 0
        risk_distribution[level.value] = count

    # Status distribution
    status_distribution = {}
    for status in OrderStatus:
        count_result = await session.execute(
            select(func.count(Order.id)).where(Order.status == status)
        )
        count = count_result.scalar() or 0
        if count > 0:
            status_distribution[status.value] = count

    # Recovery stats
    recovery_attempted_result = await session.execute(
        select(func.count(Order.id)).where(Order.recovery_attempted == True)
    )
    recovery_attempted = recovery_attempted_result.scalar() or 0

    recovery_success_result = await session.execute(
        select(func.count(Order.id)).where(Order.recovery_successful == True)
    )
    recovery_successful = recovery_success_result.scalar() or 0

    # Agent activity
    agent_actions_count = await session.execute(
        select(func.count(AgentAction.id))
    )
    total_actions = agent_actions_count.scalar() or 0

    shield_actions = await session.execute(
        select(func.count(AgentAction.id)).where(AgentAction.agent_name == "shield_agent")
    )
    shield_count = shield_actions.scalar() or 0

    recovery_actions = await session.execute(
        select(func.count(AgentAction.id)).where(AgentAction.agent_name == "recovery_agent")
    )
    recovery_action_count = recovery_actions.scalar() or 0

    # Orders blocked/saved
    cancelled_result = await session.execute(
        select(func.count(Order.id)).where(Order.status == OrderStatus.CANCELLED)
    )
    blocked_count = cancelled_result.scalar() or 0

    # Estimated savings (blocked orders * avg shipping cost)
    avg_shipping = 100  # Average ₹100 per shipment
    estimated_savings = blocked_count * avg_shipping * 2  # Forward + reverse

    return {
        "orders": {
            "total": total_count,
            "cod": cod_count,
            "cod_percentage": round((cod_count / max(total_count, 1)) * 100, 1),
            "total_revenue": round(revenue, 2),
        },
        "rto": {
            "total_rto_orders": rto_count,
            "rto_rate": round((rto_count / max(cod_count, 1)) * 100, 1),
            "total_shipping_lost": round(rto_cost, 2),
            "total_revenue_at_risk": round(rto_revenue_lost, 2),
        },
        "risk_distribution": risk_distribution,
        "status_distribution": status_distribution,
        "recovery": {
            "attempted": recovery_attempted,
            "successful": recovery_successful,
            "success_rate": round(
                (recovery_successful / max(recovery_attempted, 1)) * 100, 1
            ),
        },
        "shield_performance": {
            "orders_assessed": shield_count,
            "orders_blocked": blocked_count,
            "estimated_savings": round(estimated_savings, 2),
        },
        "agent_activity": {
            "total_actions": total_actions,
            "shield_agent_actions": shield_count,
            "recovery_agent_actions": recovery_action_count,
        },
    }


@router.get("/analytics/high-risk-orders", response_model=list)
async def get_high_risk_orders(
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_async_session)
):
    """Get top high-risk orders sorted by risk score."""
    result = await session.execute(
        select(Order).where(
            Order.risk_level.in_([RiskLevel.HIGH, RiskLevel.CRITICAL]),
            Order.payment_method == PaymentMethod.COD,
        ).order_by(desc(Order.risk_score)).limit(limit)
    )
    orders = result.scalars().all()

    response = []
    for order in orders:
        cust_result = await session.execute(
            select(Customer).where(Customer.id == order.customer_id)
        )
        customer = cust_result.scalar_one_or_none()

        response.append({
            "order_number": order.order_number,
            "customer_name": customer.name if customer else "Unknown",
            "customer_phone": customer.phone if customer else "",
            "amount": order.total_amount,
            "risk_score": order.risk_score,
            "risk_level": order.risk_level.value if order.risk_level else "unknown",
            "risk_factors": order.risk_factors or [],
            "status": order.status.value,
            "created_at": order.created_at.isoformat() if order.created_at else None,
        })

    return response


@router.get("/analytics/rto-timeline", response_model=list)
async def get_rto_timeline(
    days: int = Query(30, ge=1, le=90),
    session: AsyncSession = Depends(get_async_session)
):
    """Get RTO events timeline for chart visualization."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    rto_statuses = [
        OrderStatus.RTO_INITIATED, OrderStatus.RTO_IN_TRANSIT,
        OrderStatus.RTO_RECEIVED, OrderStatus.RECOVERY_INITIATED,
    ]

    result = await session.execute(
        select(Order).where(
            Order.status.in_(rto_statuses),
            Order.created_at >= cutoff,
        ).order_by(Order.created_at)
    )
    orders = result.scalars().all()

    return [{
        "order_number": o.order_number,
        "amount": o.total_amount,
        "rto_cost": o.total_rto_cost,
        "status": o.status.value,
        "created_at": o.created_at.isoformat() if o.created_at else None,
        "rto_initiated_at": o.rto_initiated_at.isoformat() if o.rto_initiated_at else None,
        "recovery_attempted": o.recovery_attempted,
    } for o in orders]