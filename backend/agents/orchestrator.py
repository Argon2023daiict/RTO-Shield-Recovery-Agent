"""
Agent Orchestrator - The "Director" that coordinates the Shield and Recovery agents.
Manages the full lifecycle: order intake → risk assessment → decision → recovery.
Also provides the conversational interface for the Agentic Dashboard.
"""

import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from crewai import Crew, LLM, Process  # ✅ FIX: use CrewAI native LLM
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, and_

from backend.config import get_settings
from backend.database.connection import SyncSessionLocal
from backend.database.models import (
    Order, Customer, CustomerAddress, Product, OrderItem,
    AgentAction, AgentActionType, OrderStatus, RiskLevel,
    PaymentMethod, DiscountCode
)
from backend.agents.shield_agent import ShieldAgent
from backend.agents.recovery_agent import RecoveryAgent

settings = get_settings()


class AgentOrchestrator:
    """
    Central orchestration layer that:
    1. Receives order events (new order, RTO event)
    2. Routes to the appropriate agent
    3. Records all agent actions in the database
    4. Provides a conversational query interface (Agentic Dashboard)
    """

    def __init__(self):
        self.shield_agent = ShieldAgent()
        self.recovery_agent = RecoveryAgent()
        self.llm = self._initialize_llm()

    def _initialize_llm(self) -> LLM:
        """LLM for the orchestrator's own reasoning (dashboard queries)."""
        # ────────────────────────────────────────────────────────
        # CrewAI 1.x uses its own LLM class with LiteLLM format.
        # The .call() method replaces LangChain's .invoke()
        # ────────────────────────────────────────────────────────

        if settings.llm_provider == "groq" and settings.groq_api_key:
            return LLM(
                model=f"groq/{settings.llm_model}",
                api_key=settings.groq_api_key,
                temperature=0.2,
            )
        elif settings.llm_provider == "anthropic" and settings.anthropic_api_key:
            return LLM(
                model=f"anthropic/{settings.llm_model}",
                api_key=settings.anthropic_api_key,
                temperature=0.2,
                max_tokens=4096,
            )
        elif settings.openai_api_key:
            return LLM(
                model="openai/gpt-4o",
                api_key=settings.openai_api_key,
                temperature=0.2,
                max_tokens=4096,
            )
        else:
            return LLM(
                model="openai/gpt-4o-mini",
                temperature=0.2,
            )

    # ==================== ORDER PROCESSING ====================

    def process_new_order(self, order_id: str) -> dict:
        """
        Process a new COD order through the Shield Agent.
        This is triggered when a new order webhook is received.
        """
        session = SyncSessionLocal()
        try:
            order = session.query(Order).filter(Order.id == order_id).first()
            if not order:
                return {"success": False, "error": f"Order {order_id} not found"}

            customer = session.query(Customer).filter(
                Customer.id == order.customer_id
            ).first()
            address = session.query(CustomerAddress).filter(
                CustomerAddress.id == order.shipping_address_id
            ).first()
            order_items = session.query(OrderItem).filter(
                OrderItem.order_id == order.id
            ).all()

            items_data = []
            for item in order_items:
                product = session.query(Product).filter(
                    Product.id == item.product_id
                ).first()
                items_data.append({
                    "name": product.name if product else "Unknown",
                    "sku": product.sku if product else "",
                    "price": item.unit_price,
                    "quantity": item.quantity,
                    "category": product.category if product else "",
                })

            order_data = {
                "order": {
                    "id": str(order.id),
                    "order_number": order.order_number,
                    "total_amount": order.total_amount,
                    "payment_method": order.payment_method.value,
                    "created_at": order.created_at.isoformat() if order.created_at else None,
                    "forward_shipping_cost": order.forward_shipping_cost,
                    "order_hour": order.created_at.hour if order.created_at else None,
                    "order_day_of_week": order.created_at.weekday() if order.created_at else None,
                },
                "customer": {
                    "name": customer.name,
                    "phone": customer.phone,
                    "email": customer.email,
                    "total_orders": customer.total_orders,
                    "successful_deliveries": customer.successful_deliveries,
                    "rto_count": customer.rto_count,
                    "failed_payment_attempts": customer.failed_payment_attempts,
                    "account_age_days": customer.account_age_days,
                    "is_verified": customer.is_verified,
                },
                "address": {
                    "address_line_1": address.address_line_1,
                    "address_line_2": address.address_line_2 or "",
                    "city": address.city,
                    "state": address.state,
                    "pincode": address.pincode,
                    "landmark": address.landmark or "",
                },
                "items": items_data,
            }

            assessment = self.shield_agent.assess_order(order_data)

            risk_score = assessment.get("risk_score", 50)
            risk_level_str = assessment.get("risk_level", "MEDIUM").upper()

            risk_level_map = {
                "LOW": RiskLevel.LOW,
                "MEDIUM": RiskLevel.MEDIUM,
                "HIGH": RiskLevel.HIGH,
                "CRITICAL": RiskLevel.CRITICAL,
            }

            order.risk_score = risk_score
            order.risk_level = risk_level_map.get(risk_level_str, RiskLevel.MEDIUM)
            order.risk_factors = assessment.get("risk_factors", [])
            order.risk_assessed_at = datetime.now(timezone.utc)
            order.status = OrderStatus.RISK_ASSESSED

            action = assessment.get("recommended_action", "FLAG_FOR_REVIEW")
            if action == "APPROVE":
                order.status = OrderStatus.APPROVED
            elif action in ("FLAG_FOR_REVIEW", "REQUEST_PREPAYMENT"):
                order.status = OrderStatus.FLAGGED
            elif action == "RECOMMEND_CANCELLATION":
                order.status = OrderStatus.CANCELLED

            agent_action = AgentAction(
                order_id=order.id,
                agent_name="shield_agent",
                action_type=AgentActionType.RISK_ASSESSMENT,
                action_details=assessment,
                reasoning=assessment.get("reasoning", ""),
                confidence_score=assessment.get("confidence", 0.5),
            )
            session.add(agent_action)
            session.commit()

            return {
                "success": True,
                "order_number": order.order_number,
                "risk_score": risk_score,
                "risk_level": risk_level_str,
                "recommended_action": action,
                "order_status": order.status.value,
                "assessment": assessment,
            }

        except Exception as e:
            session.rollback()
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    def process_rto_event(self, order_id: str, return_reason: str = "Unknown") -> dict:
        """
        Process an RTO event through the Recovery Agent.
        Triggered when an order is marked as returned.
        """
        session = SyncSessionLocal()
        try:
            order = session.query(Order).filter(Order.id == order_id).first()
            if not order:
                return {"success": False, "error": f"Order {order_id} not found"}

            customer = session.query(Customer).filter(
                Customer.id == order.customer_id
            ).first()
            order_items = session.query(OrderItem).filter(
                OrderItem.order_id == order.id
            ).all()

            items_data = []
            for item in order_items:
                product = session.query(Product).filter(
                    Product.id == item.product_id
                ).first()
                items_data.append({
                    "name": product.name if product else "Unknown",
                    "sku": product.sku if product else "",
                    "price": item.unit_price,
                    "quantity": item.quantity,
                })

            rto_data = {
                "order": {
                    "id": str(order.id),
                    "order_number": order.order_number,
                    "total_amount": order.total_amount,
                    "forward_shipping_cost": order.forward_shipping_cost,
                    "reverse_shipping_cost": order.reverse_shipping_cost,
                    "total_rto_cost": order.forward_shipping_cost + order.reverse_shipping_cost,
                    "rto_initiated_at": order.rto_initiated_at.isoformat() if order.rto_initiated_at else None,
                },
                "customer": {
                    "name": customer.name,
                    "phone": customer.phone,
                    "email": customer.email,
                    "total_orders": customer.total_orders,
                    "successful_deliveries": customer.successful_deliveries,
                    "rto_count": customer.rto_count,
                    "account_age_days": customer.account_age_days,
                },
                "items": items_data,
                "return_reason": return_reason,
            }

            recovery_result = self.recovery_agent.recover_order(rto_data)

            order.status = OrderStatus.RECOVERY_INITIATED
            order.recovery_attempted = True
            order.total_rto_cost = order.forward_shipping_cost + order.reverse_shipping_cost

            if recovery_result.get("discount_code"):
                order.recovery_discount_code = recovery_result["discount_code"]
            if recovery_result.get("discount_details", {}).get("percent"):
                order.recovery_discount_percent = recovery_result["discount_details"]["percent"]
            if recovery_result.get("payment_link"):
                order.recovery_payment_link = recovery_result["payment_link"]

            customer.rto_count += 1

            if recovery_result.get("discount_code"):
                discount_record = DiscountCode(
                    code=recovery_result["discount_code"],
                    customer_id=customer.id,
                    original_order_id=order.id,
                    discount_percent=recovery_result.get("discount_details", {}).get("percent", 10),
                    max_discount_amount=recovery_result.get("discount_details", {}).get("max_discount"),
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=48),
                )
                session.add(discount_record)

            agent_action = AgentAction(
                order_id=order.id,
                agent_name="recovery_agent",
                action_type=AgentActionType.RECOVERY_INITIATED,
                action_details=recovery_result,
                reasoning=recovery_result.get("recovery_strategy", ""),
                confidence_score=0.7,
            )
            session.add(agent_action)
            session.commit()

            return {
                "success": True,
                "order_number": order.order_number,
                "recovery_status": "INITIATED",
                "discount_code": recovery_result.get("discount_code"),
                "discount_percent": recovery_result.get("discount_details", {}).get("percent"),
                "recovery_result": recovery_result,
            }

        except Exception as e:
            session.rollback()
            return {"success": False, "error": str(e)}
        finally:
            session.close()

    # ==================== AGENTIC DASHBOARD QUERIES ====================

    def query_dashboard(self, user_query: str) -> dict:
        """
        Natural language interface for the Agentic Dashboard.
        """
        session = SyncSessionLocal()
        try:
            context_data = self._gather_dashboard_context(session)

            prompt = f"""
You are an AI assistant for an e-commerce merchant's RTO Shield Dashboard.
You have access to the following real-time data from the database:

{json.dumps(context_data, indent=2, default=str)}

The merchant asks: "{user_query}"

Provide a clear, actionable response based on the data above.
Include specific numbers, order IDs, and recommendations where relevant.
Format your response in a readable way with bullet points and sections.
If the data doesn't contain enough information to fully answer, say so honestly.

Respond in a professional but friendly tone, as if you're a smart analytics assistant.
"""

            # ✅ FIX: CrewAI LLM uses .call() not .invoke()
            # .call() takes a list of message dicts and returns a string
            response_text = self.llm.call(
                messages=[{"role": "user", "content": prompt}]
            )

            return {
                "success": True,
                "query": user_query,
                "response": response_text,
                "data_context": context_data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            return {
                "success": False,
                "query": user_query,
                "error": str(e),
                "response": f"I encountered an error processing your query: {str(e)}. Please try again.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        finally:
            session.close()

    def _gather_dashboard_context(self, session: Session) -> dict:
        """Gather comprehensive data for dashboard queries."""
        try:
            total_orders = session.query(func.count(Order.id)).scalar() or 0
            cod_orders = session.query(func.count(Order.id)).filter(
                Order.payment_method == PaymentMethod.COD
            ).scalar() or 0

            status_counts = {}
            for status in OrderStatus:
                count = session.query(func.count(Order.id)).filter(
                    Order.status == status
                ).scalar() or 0
                if count > 0:
                    status_counts[status.value] = count

            risk_counts = {}
            for level in RiskLevel:
                count = session.query(func.count(Order.id)).filter(
                    Order.risk_level == level
                ).scalar() or 0
                if count > 0:
                    risk_counts[level.value] = count

            high_risk_orders = session.query(Order).filter(
                Order.risk_level.in_([RiskLevel.HIGH, RiskLevel.CRITICAL]),
                Order.payment_method == PaymentMethod.COD,
            ).order_by(desc(Order.risk_score)).limit(10).all()

            high_risk_list = []
            for o in high_risk_orders:
                customer = session.query(Customer).filter(Customer.id == o.customer_id).first()
                high_risk_list.append({
                    "order_number": o.order_number,
                    "amount": o.total_amount,
                    "risk_score": o.risk_score,
                    "risk_level": o.risk_level.value if o.risk_level else "unknown",
                    "status": o.status.value,
                    "customer_name": customer.name if customer else "Unknown",
                    "risk_factors": o.risk_factors or [],
                    "created_at": o.created_at.isoformat() if o.created_at else None,
                })

            rto_orders = session.query(Order).filter(
                Order.status.in_([
                    OrderStatus.RTO_INITIATED,
                    OrderStatus.RTO_IN_TRANSIT,
                    OrderStatus.RTO_RECEIVED,
                    OrderStatus.RECOVERY_INITIATED,
                ])
            ).all()

            total_rto_cost = sum(o.total_rto_cost or 0 for o in rto_orders)
            total_rto_revenue_at_risk = sum(o.total_amount or 0 for o in rto_orders)

            recovery_attempted = session.query(func.count(Order.id)).filter(
                Order.recovery_attempted == True
            ).scalar() or 0
            recovery_successful = session.query(func.count(Order.id)).filter(
                Order.recovery_successful == True
            ).scalar() or 0

            recent_actions = session.query(AgentAction).order_by(
                desc(AgentAction.created_at)
            ).limit(15).all()

            actions_list = [{
                "agent": a.agent_name,
                "action": a.action_type.value,
                "order_id": str(a.order_id),
                "reasoning_preview": (a.reasoning or "")[:150],
                "success": a.success,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            } for a in recent_actions]

            pending_orders = session.query(Order).filter(
                Order.status == OrderStatus.PENDING,
                Order.payment_method == PaymentMethod.COD,
            ).count()

            flagged_orders = session.query(Order).filter(
                Order.status == OrderStatus.FLAGGED,
            ).count()

            return {
                "summary": {
                    "total_orders": total_orders,
                    "cod_orders": cod_orders,
                    "pending_assessment": pending_orders,
                    "flagged_for_review": flagged_orders,
                },
                "status_breakdown": status_counts,
                "risk_breakdown": risk_counts,
                "high_risk_orders": high_risk_list,
                "rto_impact": {
                    "total_rto_orders": len(rto_orders),
                    "total_shipping_cost_lost": round(total_rto_cost, 2),
                    "total_revenue_at_risk": round(total_rto_revenue_at_risk, 2),
                },
                "recovery_stats": {
                    "attempted": recovery_attempted,
                    "successful": recovery_successful,
                    "success_rate": f"{(recovery_successful / max(recovery_attempted, 1)) * 100:.1f}%",
                },
                "recent_agent_actions": actions_list,
            }

        except Exception as e:
            return {"error": f"Failed to gather context: {str(e)}"}

    # ==================== BATCH OPERATIONS ====================

    def assess_pending_orders(self, limit: int = 10) -> List[dict]:
        """Assess all pending COD orders in batch."""
        session = SyncSessionLocal()
        results = []
        try:
            pending = session.query(Order).filter(
                Order.status == OrderStatus.PENDING,
                Order.payment_method == PaymentMethod.COD,
                Order.risk_score == None,
            ).limit(limit).all()

            for order in pending:
                result = self.process_new_order(str(order.id))
                results.append(result)

            return results

        except Exception as e:
            return [{"success": False, "error": str(e)}]
        finally:
            session.close()

    def process_pending_rto_recoveries(self, limit: int = 5) -> List[dict]:
        """Process pending RTO orders that haven't been through recovery."""
        session = SyncSessionLocal()
        results = []
        try:
            rto_orders = session.query(Order).filter(
                Order.status.in_([OrderStatus.RTO_RECEIVED, OrderStatus.RTO_IN_TRANSIT]),
                Order.recovery_attempted == False,
            ).limit(limit).all()

            for order in rto_orders:
                result = self.process_rto_event(
                    str(order.id),
                    return_reason="Customer refused delivery"
                )
                results.append(result)

            return results

        except Exception as e:
            return [{"success": False, "error": str(e)}]
        finally:
            session.close()