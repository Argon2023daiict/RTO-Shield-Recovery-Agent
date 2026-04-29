"""
Recovery Service - Business logic for RTO recovery operations.
Tracks recovery attempts and success rates.
"""

from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import Session

from backend.database.models import Order, Customer, DiscountCode, OrderStatus


class RecoveryService:
    """Manages recovery attempts and tracks outcomes."""

    def __init__(self, session: Session):
        self.session = session

    def get_recovery_stats(self) -> dict:
        attempted = (self.session.query(Order)
                     .filter(Order.recovery_attempted == True).count())
        successful = (self.session.query(Order)
                      .filter(Order.recovery_successful == True).count())
        pending = (self.session.query(Order)
                   .filter(Order.status == OrderStatus.RECOVERY_INITIATED,
                           Order.recovery_successful == False).count())
        rate = round((successful / max(attempted, 1)) * 100, 1)
        return {
            "attempted": attempted,
            "successful": successful,
            "pending": pending,
            "success_rate_pct": rate,
        }

    def mark_recovery_successful(self, order_id: str) -> bool:
        order = self.session.query(Order).filter(Order.id == order_id).first()
        if not order:
            return False
        order.recovery_successful = True
        order.status = OrderStatus.RECOVERED
        customer = self.session.query(Customer).filter(Customer.id == order.customer_id).first()
        if customer:
            customer.successful_deliveries += 1
        self.session.commit()
        return True

    def get_active_discount_codes(self, customer_id: str) -> List[DiscountCode]:
        now = datetime.now(timezone.utc)
        return (self.session.query(DiscountCode)
                .filter(DiscountCode.customer_id == customer_id,
                        DiscountCode.is_used == False,
                        DiscountCode.expires_at > now)
                .all())

    def validate_discount_code(self, code: str) -> Optional[DiscountCode]:
        now = datetime.now(timezone.utc)
        return (self.session.query(DiscountCode)
                .filter(DiscountCode.code == code,
                        DiscountCode.is_used == False,
                        DiscountCode.expires_at > now)
                .first())

    def redeem_discount_code(self, code: str) -> bool:
        discount = self.validate_discount_code(code)
        if not discount:
            return False
        discount.is_used = True
        discount.used_at = datetime.now(timezone.utc)
        self.session.commit()
        return True
