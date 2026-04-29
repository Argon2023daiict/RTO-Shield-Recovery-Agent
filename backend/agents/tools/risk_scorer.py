"""
Risk Scoring Engine
Computes a composite risk score for COD orders using multiple weighted signals.
This is the core decision-making tool for the Shield Agent.
"""

import json
import math
from typing import ClassVar
from typing import Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class RiskScorerTool(BaseTool):
    name: str = "risk_scorer"
    description: str = (
        "Calculates a comprehensive RTO risk score (0-100) for a COD order based on "
        "customer behavior, address quality, order characteristics, and temporal patterns. "
        "Input should be a JSON string with customer and order data."
    )

    # Weights for different risk categories (sum to 1.0)
    WEIGHTS: ClassVar[dict] = {
        "customer_history": 0.30,
        "address_quality": 0.25,
        "order_characteristics": 0.20,
        "behavioral_signals": 0.15,
        "temporal_patterns": 0.10,
    }

    def _run(self, data_json: str) -> str:
        """Calculate risk score from order and customer data."""
        try:
            data = json.loads(data_json) if isinstance(data_json, str) else data_json

            risk_breakdown = {}
            risk_factors = []

            # ====== 1. Customer History Score (0-100, higher = more risky) ======
            customer = data.get("customer", {})
            history_score = self._score_customer_history(customer, risk_factors)
            risk_breakdown["customer_history"] = {
                "score": history_score,
                "weight": self.WEIGHTS["customer_history"],
                "weighted_score": history_score * self.WEIGHTS["customer_history"],
            }

            # ====== 2. Address Quality Score ======
            address = data.get("address_validation", {})
            address_score = self._score_address_quality(address, risk_factors)
            risk_breakdown["address_quality"] = {
                "score": address_score,
                "weight": self.WEIGHTS["address_quality"],
                "weighted_score": address_score * self.WEIGHTS["address_quality"],
            }

            # ====== 3. Order Characteristics Score ======
            order = data.get("order", {})
            order_score = self._score_order_characteristics(order, risk_factors)
            risk_breakdown["order_characteristics"] = {
                "score": order_score,
                "weight": self.WEIGHTS["order_characteristics"],
                "weighted_score": order_score * self.WEIGHTS["order_characteristics"],
            }

            # ====== 4. Behavioral Signals Score ======
            behavioral_score = self._score_behavioral_signals(customer, risk_factors)
            risk_breakdown["behavioral_signals"] = {
                "score": behavioral_score,
                "weight": self.WEIGHTS["behavioral_signals"],
                "weighted_score": behavioral_score * self.WEIGHTS["behavioral_signals"],
            }

            # ====== 5. Temporal Patterns Score ======
            temporal_score = self._score_temporal_patterns(data, risk_factors)
            risk_breakdown["temporal_patterns"] = {
                "score": temporal_score,
                "weight": self.WEIGHTS["temporal_patterns"],
                "weighted_score": temporal_score * self.WEIGHTS["temporal_patterns"],
            }

            # ====== Compute Final Score ======
            final_score = sum(
                cat["weighted_score"] for cat in risk_breakdown.values()
            )
            final_score = round(min(100, max(0, final_score)), 2)

            # ====== Risk Level Classification ======
            if final_score <= 25:
                risk_level = "LOW"
                recommended_action = "APPROVE"
                action_detail = "Green-light for dispatch. Low probability of RTO."
            elif final_score <= 50:
                risk_level = "MEDIUM"
                recommended_action = "FLAG_FOR_REVIEW"
                action_detail = (
                    "Initiate partial prepayment request via WhatsApp. "
                    "Request a token amount of ₹49-99 to validate purchase intent."
                )
            elif final_score <= 75:
                risk_level = "HIGH"
                recommended_action = "REQUEST_PREPAYMENT"
                action_detail = (
                    "Strong RTO indicators detected. Request significant partial prepayment "
                    "(30-50% of order value) or consider converting to full prepaid."
                )
            else:
                risk_level = "CRITICAL"
                recommended_action = "RECOMMEND_CANCELLATION"
                action_detail = (
                    "Very high RTO probability. Recommend immediate cancellation "
                    "to avoid forward + reverse shipping losses."
                )

            result = {
                "risk_score": final_score,
                "risk_level": risk_level,
                "recommended_action": recommended_action,
                "action_detail": action_detail,
                "risk_breakdown": risk_breakdown,
                "risk_factors": risk_factors,
                "confidence": self._calculate_confidence(data),
            }

            return json.dumps(result, indent=2)

        except Exception as e:
            return json.dumps({
                "error": str(e),
                "risk_score": 50,
                "risk_level": "MEDIUM",
                "recommended_action": "FLAG_FOR_REVIEW",
                "action_detail": "Unable to compute full risk score. Flagging for manual review.",
                "risk_factors": [f"Scoring error: {str(e)}"],
            })

    def _score_customer_history(self, customer: dict, factors: list) -> float:
        """Score based on customer's order and RTO history."""
        score = 0.0

        total_orders = customer.get("total_orders", 0)
        rto_count = customer.get("rto_count", 0)
        successful = customer.get("successful_deliveries", 0)

        # New customer with no history is risky
        if total_orders == 0:
            score += 60
            factors.append("NEW_CUSTOMER: No purchase history - higher risk for COD")
        else:
            # RTO rate is the strongest signal
            rto_rate = rto_count / total_orders if total_orders > 0 else 0
            if rto_rate > 0.5:
                score += 80
                factors.append(f"VERY_HIGH_RTO_RATE: {rto_rate:.0%} of orders returned")
            elif rto_rate > 0.3:
                score += 60
                factors.append(f"HIGH_RTO_RATE: {rto_rate:.0%} of orders returned")
            elif rto_rate > 0.15:
                score += 35
                factors.append(f"MODERATE_RTO_RATE: {rto_rate:.0%} of orders returned")
            elif rto_rate > 0.05:
                score += 15
                factors.append(f"LOW_RTO_RATE: {rto_rate:.0%} of orders returned")
            else:
                score += 5  # Minimal risk

            # Absolute RTO count matters too
            if rto_count >= 5:
                score += 15
                factors.append(f"HIGH_RTO_COUNT: {rto_count} total returns")

        # Successful delivery streak
        if total_orders > 10 and successful / max(total_orders, 1) > 0.9:
            score = max(0, score - 20)
            factors.append(f"LOYAL_CUSTOMER: {successful}/{total_orders} successful deliveries")

        return min(100, score)

    def _score_address_quality(self, address_validation: dict, factors: list) -> float:
        """Score based on address validation results."""
        # If no validation data, assume medium risk
        if not address_validation:
            factors.append("NO_ADDRESS_VALIDATION: Address not yet validated")
            return 50.0

        address_score_from_tool = address_validation.get("score", 50)
        flags = address_validation.get("flags", [])

        # Invert the address validation score (high validation score = low risk)
        risk_score = 100 - address_score_from_tool

        if "PINCODE_CITY_MISMATCH" in flags:
            risk_score = min(100, risk_score + 15)
            factors.append("PINCODE_CITY_MISMATCH: Shipping pincode doesn't match city")

        if "VAGUE_ADDRESS" in flags:
            risk_score = min(100, risk_score + 10)
            vague_detail = address_validation.get("details", {}).get("vague_indicators", [])
            factors.append(f"VAGUE_ADDRESS: Address contains vague indicators: {vague_detail}")

        if "NO_STRUCTURED_ADDRESS" in flags:
            factors.append("NO_STRUCTURED_ADDRESS: No flat/house/plot number found")

        if "GEOCODING_FAILED" in flags:
            risk_score = min(100, risk_score + 5)
            factors.append("GEOCODING_FAILED: Address could not be geocoded")

        return min(100, max(0, risk_score))

    def _score_order_characteristics(self, order: dict, factors: list) -> float:
        """Score based on the order itself."""
        score = 0.0
        amount = order.get("total_amount", 0)
        item_count = order.get("item_count", 1)

        # Very high-value COD orders are risky
        if amount > 5000:
            score += 30
            factors.append(f"HIGH_VALUE_COD: Order value ₹{amount:.0f} is above ₹5000 threshold")
        elif amount > 3000:
            score += 15
            factors.append(f"MODERATE_VALUE_COD: Order value ₹{amount:.0f}")

        # Very low-value orders can be suspicious (testing the system)
        if amount < 200:
            score += 20
            factors.append(f"VERY_LOW_VALUE: Suspiciously low order value ₹{amount:.0f}")

        # High item count
        if item_count > 5:
            score += 15
            factors.append(f"HIGH_ITEM_COUNT: {item_count} items in order")

        # Product category risks could be added here
        category = order.get("category", "")
        high_risk_categories = ["electronics", "fashion", "jewelry"]
        if category.lower() in high_risk_categories:
            score += 10
            factors.append(f"HIGH_RTO_CATEGORY: {category} has historically high RTO rates")

        return min(100, score)

    def _score_behavioral_signals(self, customer: dict, factors: list) -> float:
        """Score based on behavioral red flags."""
        score = 0.0

        # Failed payment attempts (tried prepaid but couldn't)
        failed_payments = customer.get("failed_payment_attempts", 0)
        if failed_payments >= 3:
            score += 50
            factors.append(
                f"MULTIPLE_PAYMENT_FAILURES: {failed_payments} failed payment attempts - "
                "may indicate fraudulent card testing or reluctant buyer"
            )
        elif failed_payments >= 1:
            score += 20
            factors.append(f"PAYMENT_FAILURE: {failed_payments} failed payment attempt(s)")

        # Account verification
        if not customer.get("is_verified", False):
            score += 25
            factors.append("UNVERIFIED_ACCOUNT: Phone/email not verified")

        # Email presence
        if not customer.get("email"):
            score += 10
            factors.append("NO_EMAIL: No email address on file")

        # Disposable email check
        email = customer.get("email", "")
        if email:
            disposable_domains = ["tempmail.com", "throwaway.email", "guerrillamail.com", "mailinator.com"]
            domain = email.split("@")[-1] if "@" in email else ""
            if domain in disposable_domains:
                score += 30
                factors.append(f"DISPOSABLE_EMAIL: {domain} is a known disposable email service")

        # Account age
        account_age = customer.get("account_age_days", 0)
        if account_age < 7:
            score += 35
            factors.append(f"VERY_NEW_ACCOUNT: Account is only {account_age} day(s) old")
        elif account_age < 30:
            score += 20
            factors.append(f"NEW_ACCOUNT: Account is {account_age} days old")
        elif account_age < 90:
            score += 10

        return min(100, score)

    def _score_temporal_patterns(self, data: dict, factors: list) -> float:
        """Score based on timing-related patterns."""
        score = 0.0

        order = data.get("order", {})
        order_hour = order.get("order_hour")

        # Late-night orders on COD can be riskier
        if order_hour is not None:
            if 1 <= order_hour <= 5:
                score += 25
                factors.append(f"LATE_NIGHT_ORDER: Order placed at {order_hour}:00 - unusual timing")
            elif 23 <= order_hour or order_hour == 0:
                score += 15
                factors.append(f"NIGHT_ORDER: Order placed at {order_hour}:00")

        # Weekend orders (slightly higher RTO historically)
        order_day = order.get("order_day_of_week")  # 0=Monday, 6=Sunday
        if order_day is not None and order_day >= 5:
            score += 10
            factors.append("WEEKEND_ORDER: Weekend orders have slightly higher RTO rates")

        # Multiple orders in short timeframe (potential abuse)
        recent_order_count = data.get("customer", {}).get("orders_last_24h", 0)
        if recent_order_count > 3:
            score += 40
            factors.append(
                f"ORDER_VELOCITY: {recent_order_count} orders in last 24 hours - "
                "possible system abuse"
            )
        elif recent_order_count > 1:
            score += 15
            factors.append(f"MULTIPLE_RECENT_ORDERS: {recent_order_count} orders in last 24 hours")

        return min(100, score)

    def _calculate_confidence(self, data: dict) -> float:
        """
        How confident are we in this risk score?
        More data points = higher confidence.
        """
        confidence = 0.5  # Base confidence

        customer = data.get("customer", {})
        if customer.get("total_orders", 0) > 10:
            confidence += 0.2
        elif customer.get("total_orders", 0) > 3:
            confidence += 0.1

        if data.get("address_validation"):
            confidence += 0.15

        if customer.get("is_verified"):
            confidence += 0.05

        if customer.get("email"):
            confidence += 0.05

        if data.get("order", {}).get("order_hour") is not None:
            confidence += 0.05

        return min(1.0, round(confidence, 2))