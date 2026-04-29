"""
Webhook Endpoints
Receives callbacks from Razorpay, Twilio, and simulated e-commerce events.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import Depends

from backend.database.connection import get_async_session
from backend.database.models import Order, OrderStatus, DiscountCode

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


@router.post("/razorpay/payment")
async def razorpay_payment_callback(
    request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Callback when a Razorpay payment link is paid.
    Updates order status based on payment purpose (verification or recovery).
    """
    try:
        body = await request.json()
    except Exception:
        body = dict(await request.form())

    payment_link_id = body.get("razorpay_payment_link_id", "")
    payment_id = body.get("razorpay_payment_id", "")
    status = body.get("razorpay_payment_link_status", "")

    # In production, verify the signature using Razorpay SDK
    # razorpay_client.utility.verify_payment_link_signature(body)

    # Find associated order by payment link
    result = await session.execute(
        select(Order).where(Order.recovery_payment_link.contains(payment_link_id))
    )
    order = result.scalar_one_or_none()

    if order and status == "paid":
        order.recovery_successful = True
        order.status = OrderStatus.RECOVERED
        order.closed_at = datetime.now(timezone.utc)
        await session.commit()

        return {
            "success": True,
            "order_number": order.order_number,
            "status": "recovered",
            "message": "Payment received. Order recovery successful!",
        }

    return {
        "success": True,
        "message": "Webhook received",
        "payment_link_id": payment_link_id,
        "payment_id": payment_id,
    }


@router.post("/order-event")
async def simulate_order_event(
    request: Request,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Simulate e-commerce platform events for testing.
    Events: order_placed, order_dispatched, order_delivered, rto_initiated, rto_received
    """
    body = await request.json()
    event_type = body.get("event_type", "")
    order_number = body.get("order_number", "")

    result = await session.execute(
        select(Order).where(Order.order_number == order_number)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_number} not found")

    event_status_map = {
        "order_placed": OrderStatus.PENDING,
        "order_dispatched": OrderStatus.DISPATCHED,
        "order_delivered": OrderStatus.DELIVERED,
        "rto_initiated": OrderStatus.RTO_INITIATED,
        "rto_received": OrderStatus.RTO_RECEIVED,
    }

    new_status = event_status_map.get(event_type)
    if not new_status:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event type: {event_type}. "
                   f"Valid types: {list(event_status_map.keys())}"
        )

    old_status = order.status
    order.status = new_status

    if event_type == "order_dispatched":
        order.dispatched_at = datetime.now(timezone.utc)
    elif event_type == "order_delivered":
        order.delivered_at = datetime.now(timezone.utc)
    elif event_type == "rto_initiated":
        order.rto_initiated_at = datetime.now(timezone.utc)
    elif event_type == "rto_received":
        order.rto_received_at = datetime.now(timezone.utc)
        import random
        order.reverse_shipping_cost = round(random.uniform(40, 120), 2)
        order.total_rto_cost = order.forward_shipping_cost + order.reverse_shipping_cost

    await session.commit()

    return {
        "success": True,
        "order_number": order_number,
        "event": event_type,
        "old_status": old_status.value if old_status else None,
        "new_status": new_status.value,
        "message": f"Order status updated: {old_status.value if old_status else 'N/A'} → {new_status.value}",
    }