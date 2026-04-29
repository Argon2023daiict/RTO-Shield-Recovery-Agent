"""
RTO Recovery Agent - Post-Return Revenue Salvage
Activates after an order is returned, attempting to re-engage the customer,
generate dynamic incentives, and recover lost revenue.
"""

import json
import uuid
import random
import string
from datetime import datetime, timezone, timedelta
from typing import Optional

from crewai import Agent, LLM, Task  # ✅ FIX: CrewAI native LLM, no LangChain

from backend.config import get_settings
from backend.agents.tools.whatsapp_sender import WhatsAppSenderTool
from backend.agents.tools.razorpay_payment import RazorpayPaymentTool
from backend.agents.tools.inventory_manager import InventoryManagerTool

settings = get_settings()


class RecoveryAgent:
    """
    The Recovery Agent operates after RTO has occurred. Its goal is to
    minimize financial loss by:
    1. Re-engaging the customer with empathetic, personalized outreach
    2. Generating dynamic discount codes to incentivize re-orders
    3. Creating payment links for easy re-purchasing
    4. Updating inventory status for returned items
    """

    def __init__(self):
        self.llm = self._initialize_llm()
        self.tools = [
            WhatsAppSenderTool(),
            RazorpayPaymentTool(),
            InventoryManagerTool(),
        ]
        self.agent = self._create_agent()

    def _initialize_llm(self) -> LLM:
        """Initialize the LLM based on configuration."""
        # ────────────────────────────────────────────────────────
        # CrewAI 1.x uses its own LLM class with LiteLLM format:
        #   "provider/model-name"
        # API keys can be passed explicitly or read from env vars.
        # ────────────────────────────────────────────────────────

        if settings.llm_provider == "groq" and settings.groq_api_key:
            return LLM(
                model=f"groq/{settings.llm_model}",
                api_key=settings.groq_api_key,
                temperature=0.4,
            )
        elif settings.llm_provider == "anthropic" and settings.anthropic_api_key:
            return LLM(
                model=f"anthropic/{settings.llm_model}",
                api_key=settings.anthropic_api_key,
                temperature=0.4,
                max_tokens=4096,
            )
        elif settings.openai_api_key:
            model_name = settings.llm_model if "gpt" in settings.llm_model else "gpt-4o"
            return LLM(
                model=f"openai/{model_name}",
                api_key=settings.openai_api_key,
                temperature=0.4,
                max_tokens=4096,
            )
        else:
            return LLM(
                model="openai/gpt-4o-mini",
                temperature=0.4,
                max_tokens=4096,
            )

    def _create_agent(self) -> Agent:
        """Create the CrewAI Recovery Agent."""
        return Agent(
            role="RTO Recovery Specialist & Customer Re-engagement Expert",
            goal=(
                "Recover revenue from RTO (Return to Origin) orders by re-engaging customers "
                "with empathetic, personalized outreach. Generate dynamic discount codes and "
                "create easy re-order payment links. Update inventory status for returned items. "
                "The goal is NOT to blame the customer, but to understand their situation and "
                "provide a compelling reason to complete the purchase."
            ),
            backstory=(
                "You are a customer success expert at a leading Indian e-commerce company. "
                "You understand that RTOs happen for many reasons: wrong address, customer not "
                "home, changed their mind, or found it cheaper elsewhere. Your approach is always "
                "empathetic and solution-oriented. You know that a well-timed, personalized message "
                "with the right incentive can recover 15-25% of RTO orders. You craft messages that "
                "feel personal, not automated. You consider the order value, customer history, and "
                "product type when deciding the discount percentage. High-value items get smaller "
                "percentage discounts; low-value items get larger ones. You always update inventory "
                "status to maintain operational clarity. You are data-driven: you track every "
                "recovery attempt and its outcome."
            ),
            tools=self.tools,
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
            max_iter=10,
            memory=True,
        )

    # ─── Everything below here is UNCHANGED ───────────────────

    def recover_order(self, rto_data: dict) -> dict:
        """
        Main entry point: Initiate recovery process for an RTO order.

        Args:
            rto_data: Dictionary with order, customer, and return details

        Returns:
            Recovery action results
        """
        # Generate discount code
        discount = self._calculate_discount(rto_data)
        discount_code = self._generate_discount_code()

        # Build recovery task
        task_description = self._build_recovery_task(rto_data, discount_code, discount)

        task = Task(
            description=task_description,
            expected_output=(
                "A comprehensive JSON recovery report containing:\n"
                "1. recovery_actions_taken: list of all actions performed\n"
                "2. discount_code: the generated discount code\n"
                "3. discount_percent: the discount percentage offered\n"
                "4. payment_link: the re-order payment link (if created)\n"
                "5. whatsapp_message_sent: boolean + message_id\n"
                "6. inventory_updated: boolean + new status\n"
                "7. estimated_recovery_probability: percentage\n"
                "8. recovery_strategy: explanation of the chosen approach\n"
                "9. follow_up_plan: next steps if customer doesn't respond\n\n"
                "IMPORTANT: Execute these steps in order:\n"
                "1. Use inventory_manager to mark items as 'mark_pending_inspection'\n"
                "2. Use razorpay_payment_link to create a discounted re-order payment link\n"
                "3. Use whatsapp_sender to send the recovery message with the discount and link\n\n"
                "Return the final result as a valid JSON object."
            ),
            agent=self.agent,
        )

        try:
            result = task.execute_sync()
            parsed = self._parse_result(result, rto_data, discount_code, discount)
            return parsed
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "discount_code": discount_code,
                "discount_percent": discount["percent"],
                "recovery_status": "FAILED",
                "reasoning": f"Recovery process failed: {str(e)}",
                "attempted_at": datetime.now(timezone.utc).isoformat(),
            }

    def _calculate_discount(self, rto_data: dict) -> dict:
        """
        Dynamically calculate the discount based on order value,
        customer history, and product category.
        """
        order = rto_data.get("order", {})
        customer = rto_data.get("customer", {})
        amount = order.get("total_amount", 0)
        rto_count = customer.get("rto_count", 0)
        total_orders = customer.get("total_orders", 0)

        # Base discount logic
        if amount > 5000:
            base_percent = 5
        elif amount > 2000:
            base_percent = 10
        elif amount > 500:
            base_percent = 15
        else:
            base_percent = 20

        # Customer loyalty bonus
        if total_orders > 20 and rto_count <= 2:
            base_percent += 5
        elif rto_count > 3:
            base_percent = max(5, base_percent - 5)

        # Cap the discount
        base_percent = min(30, max(5, base_percent))

        discounted_amount = amount * (1 - base_percent / 100)
        max_discount = amount * 0.3

        return {
            "percent": base_percent,
            "original_amount": amount,
            "discounted_amount": round(discounted_amount, 2),
            "savings": round(amount - discounted_amount, 2),
            "max_discount": round(max_discount, 2),
            "free_shipping": True,
        }

    def _generate_discount_code(self) -> str:
        """Generate a unique, human-readable discount code."""
        prefix = "RTO"
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"{prefix}-{random_part}"

    def _build_recovery_task(self, rto_data: dict, discount_code: str, discount: dict) -> str:
        """Build the recovery task description."""
        customer = rto_data.get("customer", {})
        order = rto_data.get("order", {})
        items = rto_data.get("items", [])
        return_reason = rto_data.get("return_reason", "Unknown")

        items_desc = "\n".join([
            f"  - {item.get('name', 'Unknown')} (₹{item.get('price', 0)})"
            for item in items
        ]) or "  No item details"

        product_name = items[0].get("name", "your item") if items else "your item"

        return f"""
RECOVERY MISSION: An order has been returned (RTO). Your job is to recover this sale
through empathetic customer outreach and smart incentives.

═══════════════════════════════════════════════
RETURNED ORDER DETAILS
═══════════════════════════════════════════════
Order Number: {order.get('order_number', 'N/A')}
Original Amount: ₹{order.get('total_amount', 0):.2f}
Return Reason: {return_reason}
RTO Date: {order.get('rto_initiated_at', 'Recent')}
Items Returned:
{items_desc}

Financial Impact:
  Forward Shipping Cost: ₹{order.get('forward_shipping_cost', 80):.2f}
  Reverse Shipping Cost: ₹{order.get('reverse_shipping_cost', 80):.2f}
  Total RTO Loss: ₹{order.get('total_rto_cost', 160):.2f}

═══════════════════════════════════════════════
CUSTOMER PROFILE
═══════════════════════════════════════════════
Name: {customer.get('name', 'Customer')}
Phone: {customer.get('phone', 'N/A')}
Email: {customer.get('email', 'Not provided')}
Total Orders: {customer.get('total_orders', 0)}
Successful Deliveries: {customer.get('successful_deliveries', 0)}
RTO Count: {customer.get('rto_count', 0)}
Account Age: {customer.get('account_age_days', 0)} days

═══════════════════════════════════════════════
RECOVERY INCENTIVE (Pre-calculated)
═══════════════════════════════════════════════
Discount Code: {discount_code}
Discount: {discount['percent']}% OFF
Original Price: ₹{discount['original_amount']:.2f}
Discounted Price: ₹{discount['discounted_amount']:.2f}
Customer Saves: ₹{discount['savings']:.2f}
Free Shipping: YES ✓

═══════════════════════════════════════════════
YOUR RECOVERY PLAN
═══════════════════════════════════════════════

Step 1: UPDATE INVENTORY
Use the inventory_manager tool to mark items as pending inspection:
{json.dumps({
    "order_id": str(order.get('id', '')),
    "action": "mark_pending_inspection",
    "notes": f"RTO received. Recovery process initiated. Discount code: {discount_code}",
})}

Step 2: CREATE PAYMENT LINK
Use the razorpay_payment_link tool to create a discounted re-order link:
{json.dumps({
    "amount": discount['discounted_amount'],
    "purpose": "recovery",
    "customer_name": customer.get('name', 'Customer'),
    "customer_phone": customer.get('phone', ''),
    "customer_email": customer.get('email', ''),
    "order_number": order.get('order_number', ''),
    "description": f"Re-order with {discount['percent']}% discount + free shipping! Use code {discount_code}",
    "discount_code": discount_code,
})}

Step 3: SEND WHATSAPP MESSAGE
Use the whatsapp_sender tool to send the recovery message:
{json.dumps({
    "phone_number": customer.get('phone', ''),
    "message_type": "recovery",
    "context": {
        "customer_name": customer.get('name', 'there'),
        "order_number": order.get('order_number', ''),
        "product_name": product_name,
        "discount_code": discount_code,
        "discount_percent": str(discount['percent']),
        "payment_link": "<<USE_LINK_FROM_STEP_2>>",
        "merchant_name": "ShopEasy",
    },
})}

Execute all three steps and report the results.
"""

    def _parse_result(self, result, rto_data: dict, discount_code: str, discount: dict) -> dict:
        """Parse recovery agent output into structured result."""
        result_str = str(result)

        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', result_str)
            if json_match:
                parsed = json.loads(json_match.group())
                parsed["success"] = True
                parsed["discount_code"] = discount_code
                parsed["discount_details"] = discount
                parsed["attempted_at"] = datetime.now(timezone.utc).isoformat()
                parsed["order_number"] = rto_data.get("order", {}).get("order_number")
                return parsed
        except (json.JSONDecodeError, AttributeError):
            pass

        return {
            "success": True,
            "raw_result": result_str[:2000],
            "discount_code": discount_code,
            "discount_details": discount,
            "recovery_status": "ATTEMPTED",
            "attempted_at": datetime.now(timezone.utc).isoformat(),
            "order_number": rto_data.get("order", {}).get("order_number"),
            "note": "Recovery actions executed. See raw_result for details.",
        }