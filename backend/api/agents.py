"""
Agent API Endpoints
Trigger agent actions and view agent history.
"""

import uuid
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from backend.database.connection import get_async_session
from backend.database.models import Order, AgentAction, OrderStatus
from backend.agents.orchestrator import AgentOrchestrator

router = APIRouter(prefix="/api/agents", tags=["Agents"])

# Initialize orchestrator (singleton pattern for production)
_orchestrator = None


def get_orchestrator() -> AgentOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator


@router.post("/assess/{order_id}", response_model=dict)
async def assess_order_risk(
    order_id: str,
    background_tasks: BackgroundTasks = None,
):
    """
    Trigger the Shield Agent to assess a COD order's RTO risk.
    This performs address validation, risk scoring, and takes autonomous action.
    """
    orchestrator = get_orchestrator()

    # Run synchronously for now (CrewAI doesn't fully support async)
    # In production, use background tasks + WebSocket for real-time updates
    result = orchestrator.process_new_order(order_id)

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Assessment failed")
        )

    return result


@router.post("/recover/{order_id}", response_model=dict)
async def recover_rto_order(
    order_id: str,
    return_reason: str = Query("Customer refused delivery", description="Reason for return"),
):
    """
    Trigger the Recovery Agent for an RTO order.
    Sends re-engagement message, generates discount, and creates payment link.
    """
    orchestrator = get_orchestrator()

    result = orchestrator.process_rto_event(order_id, return_reason)

    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Recovery failed")
        )

    return result


@router.post("/assess-batch", response_model=dict)
async def assess_pending_orders_batch(
    limit: int = Query(10, ge=1, le=50, description="Max orders to process"),
):
    """
    Batch assess all pending COD orders.
    Useful for processing a queue of incoming orders.
    """
    orchestrator = get_orchestrator()
    results = orchestrator.assess_pending_orders(limit=limit)

    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]

    return {
        "total_processed": len(results),
        "successful": len(successful),
        "failed": len(failed),
        "results": results,
    }


@router.post("/recover-batch", response_model=dict)
async def recover_rto_orders_batch(
    limit: int = Query(5, ge=1, le=20, description="Max orders to process"),
):
    """
    Batch process pending RTO recoveries.
    """
    orchestrator = get_orchestrator()
    results = orchestrator.process_pending_rto_recoveries(limit=limit)

    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]

    return {
        "total_processed": len(results),
        "successful": len(successful),
        "failed": len(failed),
        "results": results,
    }


@router.get("/actions", response_model=list)
async def get_agent_actions(
    agent_name: Optional[str] = Query(None, description="Filter by agent: shield_agent or recovery_agent"),
    order_id: Optional[str] = Query(None, description="Filter by order ID"),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_async_session)
):
    """Get agent action history / audit log."""
    query = select(AgentAction).order_by(desc(AgentAction.created_at))

    if agent_name:
        query = query.where(AgentAction.agent_name == agent_name)
    if order_id:
        query = query.where(AgentAction.order_id == uuid.UUID(order_id))

    query = query.limit(limit)
    result = await session.execute(query)
    actions = result.scalars().all()

    return [{
        "id": str(a.id),
        "order_id": str(a.order_id),
        "agent_name": a.agent_name,
        "action_type": a.action_type.value if a.action_type else "unknown",
        "reasoning_preview": (a.reasoning or "")[:300],
        "confidence_score": a.confidence_score,
        "success": a.success,
        "error_message": a.error_message,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    } for a in actions]