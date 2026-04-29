"""
SQLAlchemy ORM models for the RTO Shield & Recovery system.
Models capture the full lifecycle: Order → Risk Assessment → Dispatch/Block → Return → Recovery.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, Text,
    ForeignKey, Enum, JSON, Index, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from backend.database.connection import Base


# ===================== ENUMS =====================

class OrderStatus(str, PyEnum):
    PENDING = "pending"
    RISK_ASSESSED = "risk_assessed"
    APPROVED = "approved"
    FLAGGED = "flagged"
    CANCELLED = "cancelled"
    DISPATCHED = "dispatched"
    DELIVERED = "delivered"
    RTO_INITIATED = "rto_initiated"
    RTO_IN_TRANSIT = "rto_in_transit"
    RTO_RECEIVED = "rto_received"
    RECOVERY_INITIATED = "recovery_initiated"
    RECOVERED = "recovered"
    CLOSED = "closed"


class RiskLevel(str, PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PaymentMethod(str, PyEnum):
    COD = "cod"
    PREPAID = "prepaid"
    PARTIAL_COD = "partial_cod"


class AgentActionType(str, PyEnum):
    RISK_ASSESSMENT = "risk_assessment"
    ORDER_APPROVED = "order_approved"
    ORDER_FLAGGED = "order_flagged"
    ORDER_CANCELLED = "order_cancelled"
    PARTIAL_PAYMENT_REQUESTED = "partial_payment_requested"
    WHATSAPP_SENT = "whatsapp_sent"
    RECOVERY_INITIATED = "recovery_initiated"
    DISCOUNT_GENERATED = "discount_generated"
    PAYMENT_LINK_CREATED = "payment_link_created"
    INVENTORY_UPDATED = "inventory_updated"
    CUSTOMER_REENGAGED = "customer_reengaged"


class InventoryStatus(str, PyEnum):
    IN_STOCK = "in_stock"
    RESERVED = "reserved"
    DISPATCHED = "dispatched"
    IN_TRANSIT_RETURN = "in_transit_return"
    PENDING_INSPECTION = "pending_inspection"
    RESTOCKED = "restocked"
    DAMAGED = "damaged"


# ===================== MODELS =====================

class Customer(Base):
    __tablename__ = "customers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String(15), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=True)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Behavioral signals
    total_orders = Column(Integer, default=0)
    successful_deliveries = Column(Integer, default=0)
    rto_count = Column(Integer, default=0)
    failed_payment_attempts = Column(Integer, default=0)
    account_age_days = Column(Integer, default=0)
    is_verified = Column(Boolean, default=False)

    # Relationships
    addresses = relationship("CustomerAddress", back_populates="customer", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="customer", cascade="all, delete-orphan")

    @property
    def rto_rate(self) -> float:
        if self.total_orders == 0:
            return 0.0
        return self.rto_count / self.total_orders

    def __repr__(self):
        return f"<Customer {self.name} ({self.phone})>"


class CustomerAddress(Base):
    __tablename__ = "customer_addresses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    address_line_1 = Column(String(500), nullable=False)
    address_line_2 = Column(String(500), nullable=True)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    pincode = Column(String(10), nullable=False)
    landmark = Column(String(255), nullable=True)
    address_type = Column(String(50), default="home")  # home, office, other
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Validation results (populated by address intelligence)
    is_validated = Column(Boolean, default=False)
    validation_score = Column(Float, nullable=True)
    geocoded_lat = Column(Float, nullable=True)
    geocoded_lng = Column(Float, nullable=True)
    pincode_city_match = Column(Boolean, nullable=True)
    is_vague = Column(Boolean, nullable=True)
    vague_indicators = Column(JSON, nullable=True)  # List of flags

    # Relationships
    customer = relationship("Customer", back_populates="addresses")

    __table_args__ = (
        Index("idx_address_pincode", "pincode"),
        Index("idx_address_customer", "customer_id"),
    )

    def __repr__(self):
        return f"<Address {self.address_line_1}, {self.city} - {self.pincode}>"


class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(500), nullable=False)
    sku = Column(String(100), unique=True, nullable=False, index=True)
    price = Column(Float, nullable=False)
    category = Column(String(100), nullable=True)
    weight_grams = Column(Integer, nullable=True)
    inventory_status = Column(
        Enum(InventoryStatus), default=InventoryStatus.IN_STOCK
    )
    stock_quantity = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    order_items = relationship("OrderItem", back_populates="product")

    def __repr__(self):
        return f"<Product {self.name} ({self.sku})>"


class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    shipping_address_id = Column(UUID(as_uuid=True), ForeignKey("customer_addresses.id"), nullable=False)

    # Order details
    total_amount = Column(Float, nullable=False)
    payment_method = Column(Enum(PaymentMethod), default=PaymentMethod.COD)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    dispatched_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    rto_initiated_at = Column(DateTime(timezone=True), nullable=True)
    rto_received_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # Risk assessment results
    risk_score = Column(Float, nullable=True)
    risk_level = Column(Enum(RiskLevel), nullable=True)
    risk_factors = Column(JSON, nullable=True)  # Detailed breakdown
    risk_assessed_at = Column(DateTime(timezone=True), nullable=True)

    # Recovery tracking
    recovery_attempted = Column(Boolean, default=False)
    recovery_discount_code = Column(String(50), nullable=True)
    recovery_discount_percent = Column(Float, nullable=True)
    recovery_payment_link = Column(String(500), nullable=True)
    recovery_successful = Column(Boolean, default=False)

    # Financial impact
    forward_shipping_cost = Column(Float, default=0.0)
    reverse_shipping_cost = Column(Float, default=0.0)
    total_rto_cost = Column(Float, default=0.0)

    # Relationships
    customer = relationship("Customer", back_populates="orders")
    shipping_address = relationship("CustomerAddress")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    agent_actions = relationship("AgentAction", back_populates="order", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("total_amount >= 0", name="check_positive_amount"),
        Index("idx_order_status_date", "status", "created_at"),
        Index("idx_order_risk", "risk_level", "risk_score"),
    )

    def __repr__(self):
        return f"<Order {self.order_number} - {self.status.value}>"


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

    def __repr__(self):
        return f"<OrderItem {self.product_id} x {self.quantity}>"


class AgentAction(Base):
    """
    Audit log of every action taken by AI agents.
    Critical for transparency, debugging, and compliance.
    """
    __tablename__ = "agent_actions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    agent_name = Column(String(100), nullable=False)  # "shield_agent" or "recovery_agent"
    action_type = Column(Enum(AgentActionType), nullable=False)
    action_details = Column(JSON, nullable=True)
    reasoning = Column(Text, nullable=True)  # LLM's reasoning for the action
    confidence_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    order = relationship("Order", back_populates="agent_actions")

    __table_args__ = (
        Index("idx_action_agent_type", "agent_name", "action_type"),
        Index("idx_action_order", "order_id"),
    )

    def __repr__(self):
        return f"<AgentAction {self.agent_name}:{self.action_type.value}>"


class DiscountCode(Base):
    """Tracks discount codes generated by the Recovery Agent."""
    __tablename__ = "discount_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False, index=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False)
    original_order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    discount_percent = Column(Float, nullable=False)
    max_discount_amount = Column(Float, nullable=True)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    used_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    customer = relationship("Customer")
    original_order = relationship("Order")

    def __repr__(self):
        return f"<DiscountCode {self.code} - {self.discount_percent}%>"