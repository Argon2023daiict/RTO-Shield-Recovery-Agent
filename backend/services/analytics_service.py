"""
Analytics Service
Provides computed metrics and insights for the dashboard.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, case

from backend.database.models import (
    Order, Customer, AgentAction, OrderStatus, RiskLevel, PaymentMethod
)


class AnalyticsService:
    """Computes business analytics from order and agent data."""

    def __init__(self, session: Session):
        self.session = session

    def get_rto_rate_by_risk_level(self) -> Dict[str, float]:
        """Calculate actual RTO rate for each risk level to validate the model."""
        results = {}
        for level in RiskLevel:
            total = self.session.query(func.count(Order.id)).filter(
                Order.risk_level == level,
                Order.payment_method == PaymentMethod.COD,
            ).scalar() or 0

            rto = self.session.query(func.count(Order.id)).filter(
                Order.risk_level == level,
                Order.status.in_([
                    OrderStatus.RTO_INITIATED,
                    OrderStatus.RTO_IN_TRANSIT,
                    OrderStatus.RTO_RECEIVED,
                    OrderStatus.RECOVERY_INITIATED,
                ]),
            ).scalar() or 0

            results[level.value] = {
                "total_orders": total,
                "rto_orders": rto,
                "rto_rate": round((rto / max(total, 1)) * 100, 2),
            }

        return results

    def get_top_rto_customers(self, limit: int = 10) -> List[dict]:
        """Get customers with highest RTO rates."""
        customers = self.session.query(Customer).filter(
            Customer.rto_count > 0
        ).order_by(desc(Customer.rto_count)).limit(limit).all()

        return [{
            "name": c.name,
            "phone": c.phone,
            "total_orders": c.total_orders,
            "rto_count": c.rto_count,
            "rto_rate": round(c.rto_rate * 100, 1),
            "is_verified": c.is_verified,
            "account_age_days": c.account_age_days,
        } for c in customers]

    def get_financial_summary(self) -> dict:
        """Get comprehensive financial impact summary."""
        total_revenue = self.session.query(
            func.sum(Order.total_amount)
        ).scalar() or 0

        delivered_revenue = self.session.query(
            func.sum(Order.total_amount)
        ).filter(Order.status == OrderStatus.DELIVERED).scalar() or 0

        rto_statuses = [
            OrderStatus.RTO_INITIATED, OrderStatus.RTO_IN_TRANSIT,
            OrderStatus.RTO_RECEIVED, OrderStatus.RECOVERY_INITIATED,
        ]

        rto_shipping_loss = self.session.query(
            func.sum(Order.total_rto_cost)
        ).filter(Order.status.in_(rto_statuses)).scalar() or 0

        rto_revenue_lost = self.session.query(
            func.sum(Order.total_amount)
        ).filter(Order.status.in_(rto_statuses)).scalar() or 0

        # Estimated savings from blocked orders
        blocked_orders = self.session.query(Order).filter(
            Order.status == OrderStatus.CANCELLED,
            Order.risk_level.in_([RiskLevel.HIGH, RiskLevel.CRITICAL]),
        ).all()

        estimated_savings = sum(
            (o.forward_shipping_cost or 80) * 2  # Saved forward + reverse
            for o in blocked_orders
        )

        # Recovery value
        recovered_revenue = self.session.query(
            func.sum(Order.total_amount)
        ).filter(Order.recovery_successful == True).scalar() or 0

        return {
            "total_order_value": round(total_revenue, 2),
            "delivered_revenue": round(delivered_revenue, 2),
            "rto_shipping_losses": round(rto_shipping_loss, 2),
            "rto_revenue_at_risk": round(rto_revenue_lost, 2),
            "orders_blocked_savings": round(estimated_savings, 2),
            "recovery_revenue": round(recovered_revenue, 2),
            "net_savings_from_agents": round(estimated_savings + recovered_revenue, 2),
        }

    def get_agent_performance(self) -> dict:
        """Get agent performance metrics."""
        shield_actions = self.session.query(func.count(AgentAction.id)).filter(
            AgentAction.agent_name == "shield_agent"
        ).scalar() or 0

        recovery_actions = self.session.query(func.count(AgentAction.id)).filter(
            AgentAction.agent_name == "recovery_agent"
        ).scalar() or 0

        successful_actions = self.session.query(func.count(AgentAction.id)).filter(
            AgentAction.success == True
        ).scalar() or 0

        total_actions = shield_actions + recovery_actions

        # Average confidence
        avg_confidence = self.session.query(
            func.avg(AgentAction.confidence_score)
        ).scalar() or 0

        return {
            "total_actions": total_actions,
            "shield_agent_actions": shield_actions,
            "recovery_agent_actions": recovery_actions,
            "success_rate": round(
                (successful_actions / max(total_actions, 1)) * 100, 1
            ),
            "average_confidence": round(avg_confidence, 2),
        }