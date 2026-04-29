"""
Order Service - Business logic layer for order operations.
Keeps API routes thin by centralizing order-related logic here.
"""

from datetime import datetime, timezone
from typing import Optional, List
import random

from sqlalchemy.orm import Session
from sqlalchemy import desc

from backend.database.models import (
    Order, Customer, CustomerAddress, Product, OrderItem,
    OrderStatus, PaymentMethod, RiskLevel
)


class OrderService:
    """Handles all business logic related to orders."""

    def __init__(self, session: Session):
        self.session = session

    def get_order_by_id(self, order_id: str) -> Optional[Order]:
        return self.session.query(Order).filter(Order.id == order_id).first()

    def get_order_with_details(self, order_id: str) -> Optional[dict]:
        order = self.get_order_by_id(order_id)
        if not order:
            return None
        customer = self.session.query(Customer).filter(Customer.id == order.customer_id).first()
        address = self.session.query(CustomerAddress).filter(CustomerAddress.id == order.shipping_address_id).first()
        items = self.session.query(OrderItem).filter(OrderItem.order_id == order.id).all()
        items_list = []
        for item in items:
            product = self.session.query(Product).filter(Product.id == item.product_id).first()
            items_list.append({
                "product_name": product.name if product else "Unknown",
                "sku": product.sku if product else "",
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total_price": item.total_price,
            })
        return {"order": order, "customer": customer, "address": address, "items": items_list}

    def list_orders(self, status=None, risk_level=None, payment_method=None, limit=50, offset=0) -> List[Order]:
        query = self.session.query(Order).order_by(desc(Order.created_at))
        if status:
            try:
                query = query.filter(Order.status == OrderStatus(status))
            except ValueError:
                pass
        if risk_level:
            try:
                query = query.filter(Order.risk_level == RiskLevel(risk_level))
            except ValueError:
                pass
        if payment_method:
            try:
                query = query.filter(Order.payment_method == PaymentMethod(payment_method))
            except ValueError:
                pass
        return query.limit(limit).offset(offset).all()

    def get_pending_cod_orders(self, limit: int = 50) -> List[Order]:
        return (self.session.query(Order)
                .filter(Order.payment_method == PaymentMethod.COD,
                        Order.status == OrderStatus.PENDING,
                        Order.risk_score.is_(None))
                .order_by(Order.created_at).limit(limit).all())

    def get_rto_orders_pending_recovery(self, limit: int = 20) -> List[Order]:
        return (self.session.query(Order)
                .filter(Order.status.in_([OrderStatus.RTO_RECEIVED, OrderStatus.RTO_IN_TRANSIT]),
                        Order.recovery_attempted == False)
                .order_by(Order.rto_initiated_at).limit(limit).all())

    def simulate_rto(self, order_id: str) -> Optional[Order]:
        order = self.get_order_by_id(order_id)
        if not order:
            return None
        order.status = OrderStatus.RTO_RECEIVED
        order.rto_initiated_at = datetime.now(timezone.utc)
        order.reverse_shipping_cost = round(random.uniform(40, 120), 2)
        order.total_rto_cost = (order.forward_shipping_cost or 0) + order.reverse_shipping_cost
        self.session.commit()
        return order

    def get_order_stats(self) -> dict:
        total = self.session.query(Order).count()
        cod = self.session.query(Order).filter(Order.payment_method == PaymentMethod.COD).count()
        flagged = self.session.query(Order).filter(Order.status == OrderStatus.FLAGGED).count()
        cancelled = self.session.query(Order).filter(Order.status == OrderStatus.CANCELLED).count()
        recovered = self.session.query(Order).filter(Order.recovery_successful == True).count()
        return {"total_orders": total, "cod_orders": cod, "flagged_orders": flagged,
                "cancelled_orders": cancelled, "recovered_orders": recovered}
