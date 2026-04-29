"""
Risk Service - Business logic for risk scoring and analysis.
Wraps the RiskScorerTool for use outside the agent context.
"""

from typing import Optional
from backend.database.models import Order, RiskLevel


RISK_THRESHOLDS = {
    RiskLevel.LOW: (0, 30),
    RiskLevel.MEDIUM: (30, 60),
    RiskLevel.HIGH: (60, 80),
    RiskLevel.CRITICAL: (80, 100),
}


def score_to_risk_level(score: float) -> RiskLevel:
    """Convert a numeric risk score to a RiskLevel enum."""
    if score < 30:
        return RiskLevel.LOW
    elif score < 60:
        return RiskLevel.MEDIUM
    elif score < 80:
        return RiskLevel.HIGH
    else:
        return RiskLevel.CRITICAL


def get_risk_color(risk_level: RiskLevel) -> str:
    """Return a hex color for UI display."""
    colors = {
        RiskLevel.LOW: "#27ae60",
        RiskLevel.MEDIUM: "#f39c12",
        RiskLevel.HIGH: "#e74c3c",
        RiskLevel.CRITICAL: "#8e44ad",
    }
    return colors.get(risk_level, "#95a5a6")


def describe_risk_factors(risk_factors: list) -> str:
    """Turn a list of risk factors into a human-readable string."""
    if not risk_factors:
        return "No specific risk factors identified."
    return "; ".join(risk_factors)


def estimate_financial_impact(order: Order) -> dict:
    """Estimate the financial impact if this order becomes an RTO."""
    forward = order.forward_shipping_cost or 80
    reverse = forward  # Assume symmetric
    order_value = order.total_amount or 0
    total_loss = forward + reverse

    return {
        "forward_shipping": forward,
        "reverse_shipping": reverse,
        "total_shipping_loss": total_loss,
        "order_value_at_risk": order_value,
        "total_exposure": order_value + total_loss,
        "loss_as_pct_of_order": round((total_loss / max(order_value, 1)) * 100, 1),
    }
