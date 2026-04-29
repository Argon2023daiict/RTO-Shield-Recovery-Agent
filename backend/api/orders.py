"""
Order Management API Endpoints
CRUD operations for orders + webhook simulation for testing.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel, Field

from backend.database.connection import get_async_session
from backend.database.models import (
    Order, Customer, CustomerAddress, Product, OrderItem,
    OrderStatus, PaymentMethod, RiskLevel
)

router = APIRouter(prefix="/api/orders", tags=["Orders"])


# ==================== SCHEMAS ====================

class OrderItemCreate(BaseModel):
    product_sku: str
    quantity: int = 1


class OrderCreate(BaseModel):
    customer_phone: str = Field(..., description="Customer phone number")
    shipping_address_id: Optional[str] = Field(None, description="Specific address ID")
    items: List[OrderItemCreate] = Field(..., min_length=1)
    payment_method: str = Field("cod", description="Payment method: cod, prepaid")


class OrderResponse(BaseModel):
    id: str
    order_number: str
    customer_name: str
    total_amount: float
    payment_method: str
    status: str
    risk_score: Optional[float]
    risk_level: Optional[str]
    created_at: Optional[str]

    class Config:
        from_attributes = True


class OrderDetailResponse(OrderResponse):
    risk_factors: Optional[list]
    forward_shipping_cost: float
    reverse_shipping_cost: float
    total_rto_cost: float
    recovery_attempted: bool
    recovery_discount_code: Optional[str]
    recovery_payment_link: Optional[str]
    items: list
    shipping_address: dict


# ==================== ENDPOINTS ====================

@router.post("/", response_model=dict, status_code=201)
async def create_order(
    order_data: OrderCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Create a new COD order. This simulates an order webhook from an e-commerce platform.
    The order will be created in PENDING status, ready for Shield Agent assessment.
    """
    # Find customer
    result = await session.execute(
        select(Customer).where(Customer.phone == order_data.customer_phone)
    )
    customer = result.scalar_one_or_none()
    if not customer:
        raise HTTPException(status_code=404, detail=f"Customer with phone {order_data.customer_phone} not found")

    # Find shipping address
    if order_data.shipping_address_id:
        result = await session.execute(
            select(CustomerAddress).where(
                CustomerAddress.id == order_data.shipping_address_id
            )
        )
        address = result.scalar_one_or_none()
    else:
        result = await session.execute(
            select(CustomerAddress).where(
                CustomerAddress.customer_id == customer.id,
                CustomerAddress.is_default == True
            )
        )
        address = result.scalar_one_or_none()

    if not address:
        raise HTTPException(status_code=404, detail="No shipping address found for customer")

    # Resolve products and calculate total
    total_amount = 0.0
    order_items_data = []

    for item in order_data.items:
        result = await session.execute(
            select(Product).where(Product.sku == item.product_sku)
        )
        product = result.scalar_one_or_none()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product with SKU {item.product_sku} not found")

        item_total = product.price * item.quantity
        total_amount += item_total
        order_items_data.append({
            "product": product,
            "quantity": item.quantity,
            "unit_price": product.price,
            "total_price": item_total,
        })

    # Create order
    import random
    order_number = f"ORD-{random.randint(100000, 999999)}"

    payment_method_map = {
        "cod": PaymentMethod.COD,
        "prepaid": PaymentMethod.PREPAID,
        "partial_cod": PaymentMethod.PARTIAL_COD,
    }

    new_order = Order(
        order_number=order_number,
        customer_id=customer.id,
        shipping_address_id=address.id,
        total_amount=total_amount,
        payment_method=payment_method_map.get(order_data.payment_method, PaymentMethod.COD),
        status=OrderStatus.PENDING,
        forward_shipping_cost=round(random.uniform(40, 120), 2),
    )
    session.add(new_order)
    await session.flush()

    # Create order items
    for item_data in order_items_data:
        order_item = OrderItem(
            order_id=new_order.id,
            product_id=item_data["product"].id,
            quantity=item_data["quantity"],
            unit_price=item_data["unit_price"],
            total_price=item_data["total_price"],
        )
        session.add(order_item)

    # Update customer order count
    customer.total_orders += 1

    await session.commit()

    return {
        "success": True,
        "order_id": str(new_order.id),
        "order_number": order_number,
        "total_amount": total_amount,
        "status": OrderStatus.PENDING.value,
        "message": "Order created. Ready for Shield Agent assessment.",
        "next_step": f"POST /api/agents/assess/{new_order.id}",
    }


@router.get("/", response_model=List[OrderResponse])
async def list_orders(
    status: Optional[str] = Query(None, description="Filter by status"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_async_session)
):
    """List orders with optional filtering."""
    query = select(Order).order_by(desc(Order.created_at))

    if status:
        try:
            status_enum = OrderStatus(status)
            query = query.where(Order.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    if risk_level:
        try:
            risk_enum = RiskLevel(risk_level)
            query = query.where(Order.risk_level == risk_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid risk level: {risk_level}")

    query = query.limit(limit).offset(offset)
    result = await session.execute(query)
    orders = result.scalars().all()

    response = []
    for order in orders:
        cust_result = await session.execute(
            select(Customer).where(Customer.id == order.customer_id)
        )
        customer = cust_result.scalar_one_or_none()

        response.append(OrderResponse(
            id=str(order.id),
            order_number=order.order_number,
            customer_name=customer.name if customer else "Unknown",
            total_amount=order.total_amount,
            payment_method=order.payment_method.value if order.payment_method else "unknown",
            status=order.status.value if order.status else "unknown",
            risk_score=order.risk_score,
            risk_level=order.risk_level.value if order.risk_level else None,
            created_at=order.created_at.isoformat() if order.created_at else None,
        ))

    return response


@router.get("/{order_id}", response_model=dict)
async def get_order_detail(
    order_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """Get detailed order information including risk assessment and recovery data."""
    result = await session.execute(
        select(Order).where(Order.id == uuid.UUID(order_id))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Fetch customer
    cust_result = await session.execute(
        select(Customer).where(Customer.id == order.customer_id)
    )
    customer = cust_result.scalar_one_or_none()

    # Fetch address
    addr_result = await session.execute(
        select(CustomerAddress).where(CustomerAddress.id == order.shipping_address_id)
    )
    address = addr_result.scalar_one_or_none()

    # Fetch items
    items_result = await session.execute(
        select(OrderItem).where(OrderItem.order_id == order.id)
    )
    order_items = items_result.scalars().all()

    items_list = []
    for item in order_items:
        prod_result = await session.execute(
            select(Product).where(Product.id == item.product_id)
        )
        product = prod_result.scalar_one_or_none()
        items_list.append({
            "product_name": product.name if product else "Unknown",
            "sku": product.sku if product else "",
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "total_price": item.total_price,
        })

    return {
        "id": str(order.id),
        "order_number": order.order_number,
        "customer": {
            "name": customer.name if customer else "Unknown",
            "phone": customer.phone if customer else "",
            "email": customer.email if customer else None,
            "total_orders": customer.total_orders if customer else 0,
            "rto_count": customer.rto_count if customer else 0,
        },
        "shipping_address": {
            "address_line_1": address.address_line_1 if address else "",
            "city": address.city if address else "",
            "state": address.state if address else "",
            "pincode": address.pincode if address else "",
        },
        "items": items_list,
        "total_amount": order.total_amount,
        "payment_method": order.payment_method.value if order.payment_method else "unknown",
        "status": order.status.value if order.status else "unknown",
        "risk_assessment": {
            "risk_score": order.risk_score,
            "risk_level": order.risk_level.value if order.risk_level else None,
            "risk_factors": order.risk_factors,
            "assessed_at": order.risk_assessed_at.isoformat() if order.risk_assessed_at else None,
        },
        "rto_details": {
            "forward_shipping_cost": order.forward_shipping_cost,
            "reverse_shipping_cost": order.reverse_shipping_cost,
            "total_rto_cost": order.total_rto_cost,
            "rto_initiated_at": order.rto_initiated_at.isoformat() if order.rto_initiated_at else None,
        },
        "recovery": {
            "attempted": order.recovery_attempted,
            "discount_code": order.recovery_discount_code,
            "discount_percent": order.recovery_discount_percent,
            "payment_link": order.recovery_payment_link,
            "successful": order.recovery_successful,
        },
        "created_at": order.created_at.isoformat() if order.created_at else None,
    }


@router.post("/{order_id}/simulate-rto", response_model=dict)
async def simulate_rto(
    order_id: str,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Simulate an RTO event for testing.
    Moves an order to RTO_RECEIVED status, ready for recovery.
    """
    result = await session.execute(
        select(Order).where(Order.id == uuid.UUID(order_id))
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    import random
    order.status = OrderStatus.RTO_RECEIVED
    order.rto_initiated_at = datetime.now(timezone.utc)
    order.reverse_shipping_cost = round(random.uniform(40, 120), 2)
    order.total_rto_cost = order.forward_shipping_cost + order.reverse_shipping_cost

    await session.commit()

    return {
        "success": True,
        "order_number": order.order_number,
        "status": order.status.value,
        "total_rto_cost": order.total_rto_cost,
        "message": "RTO simulated. Ready for Recovery Agent.",
        "next_step": f"POST /api/agents/recover/{order.id}",
    }