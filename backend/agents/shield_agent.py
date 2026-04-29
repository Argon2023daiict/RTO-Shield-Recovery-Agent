"""
RTO Shield Agent - Pre-Dispatch Risk Assessment
Analyzes every COD order at placement to determine risk level and recommended action.
This is the first line of defense against costly RTO events.
"""

import json
from datetime import datetime, timezone
from typing import Optional

from crewai import Agent, LLM, Task  # ✅ FIX: use CrewAI's native LLM, remove LangChain

from backend.config import get_settings
from backend.agents.tools.address_validator import AddressValidatorTool
from backend.agents.tools.risk_scorer import RiskScorerTool
from backend.agents.tools.whatsapp_sender import WhatsAppSenderTool
from backend.agents.tools.razorpay_payment import RazorpayPaymentTool

settings = get_settings()


class ShieldAgent:
    """
    The Shield Agent operates in the critical window between order placement
    and dispatch. It must make fast, accurate risk assessments and take
    autonomous action to protect merchants from RTO losses.
    """

    def __init__(self):
        self.llm = self._initialize_llm()
        self.tools = [
            AddressValidatorTool(),
            RiskScorerTool(),
            WhatsAppSenderTool(),
            RazorpayPaymentTool(),
        ]
        self.agent = self._create_agent()

    def _initialize_llm(self) -> LLM:
        """Initialize the LLM based on configuration."""
        # ────────────────────────────────────────────────────────
        # CrewAI 1.x uses its own LLM class with LiteLLM format:
        #   "provider/model-name"
        # API keys are read from env vars automatically:
        #   GROQ_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY
        # Or you can pass api_key= explicitly.
        # ────────────────────────────────────────────────────────

        if settings.llm_provider == "groq" and settings.groq_api_key:
            return LLM(
                model=f"groq/{settings.llm_model}",
                api_key=settings.groq_api_key,
                temperature=0.1,
            )
        elif settings.llm_provider == "anthropic" and settings.anthropic_api_key:
            return LLM(
                model=f"anthropic/{settings.llm_model}",
                api_key=settings.anthropic_api_key,
                temperature=0.1,
                max_tokens=4096,
            )
        elif settings.openai_api_key:
            model_name = settings.llm_model if "gpt" in settings.llm_model else "gpt-4o"
            return LLM(
                model=f"openai/{model_name}",
                api_key=settings.openai_api_key,
                temperature=0.1,
                max_tokens=4096,
            )
        else:
            return LLM(
                model="openai/gpt-4o-mini",
                temperature=0.1,
                max_tokens=4096,
            )

    def _create_agent(self) -> Agent:
        """Create the CrewAI Shield Agent."""
        return Agent(
            role="RTO Shield Risk Analyst",
            goal=(
                "Analyze Cash on Delivery (COD) orders to accurately assess the risk of "
                "Return to Origin (RTO). Protect merchants from financial losses by identifying "
                "high-risk orders BEFORE they are dispatched. Take appropriate autonomous actions "
                "based on risk level: approve low-risk orders, request verification for medium-risk "
                "orders, and recommend cancellation for high-risk orders."
            ),
            backstory=(
                "You are an expert risk analyst at a leading Indian fintech company, specialized "
                "in e-commerce fraud detection and COD order analysis. You've analyzed millions "
                "of orders and understand the subtle behavioral patterns that predict RTO events. "
                "You know that in India, COD accounts for ~60% of e-commerce orders, and RTO rates "
                "can be as high as 25-40% for some merchants. Every RTO costs the merchant ₹100-300 "
                "in wasted shipping. Your job is to catch risky orders early while ensuring legitimate "
                "customers aren't inconvenienced. You think systematically: first validate the address, "
                "then assess the customer, then compute the risk score, and finally take action."
            ),
            tools=self.tools,
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
            max_iter=10,
            memory=True,
        )

    # ─── Everything below here is UNCHANGED ───────────────────

    def assess_order(self, order_data: dict) -> dict:
        """
        Main entry point: Assess a single COD order for RTO risk.

        Args:
            order_data: Dictionary containing order, customer, and address info

        Returns:
            Complete risk assessment with recommended action
        """
        task_description = self._build_assessment_task(order_data)

        task = Task(
            description=task_description,
            expected_output=(
                "A comprehensive JSON risk assessment containing:\n"
                "1. risk_score (0-100)\n"
                "2. risk_level (LOW/MEDIUM/HIGH/CRITICAL)\n"
                "3. recommended_action (APPROVE/FLAG_FOR_REVIEW/REQUEST_PREPAYMENT/RECOMMEND_CANCELLATION)\n"
                "4. action_taken (what autonomous action was executed)\n"
                "5. risk_factors (list of identified risk signals)\n"
                "6. reasoning (detailed explanation of the assessment)\n"
                "7. address_validation_result (from address validation tool)\n"
                "8. estimated_rto_probability (percentage)\n"
                "9. estimated_financial_impact (potential loss in INR if RTO occurs)\n\n"
                "IMPORTANT: You MUST use the tools in this order:\n"
                "1. First, use address_validator to validate the shipping address\n"
                "2. Then, use risk_scorer with the combined customer + address data\n"
                "3. Based on the risk level, take the appropriate action:\n"
                "   - LOW risk: Just report the approval\n"
                "   - MEDIUM risk: Use whatsapp_sender to send a verification message\n"
                "   - HIGH risk: Use razorpay_payment_link to create a partial payment link, "
                "     then use whatsapp_sender to send it\n"
                "   - CRITICAL risk: Use whatsapp_sender to send a cancellation notice\n\n"
                "Return the final result as a valid JSON object."
            ),
            agent=self.agent,
        )

        try:
            result = task.execute_sync()
            return self._parse_result(result, order_data)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "risk_score": 50,
                "risk_level": "MEDIUM",
                "recommended_action": "FLAG_FOR_REVIEW",
                "reasoning": f"Assessment failed with error: {str(e)}. Flagging for manual review.",
                "assessed_at": datetime.now(timezone.utc).isoformat(),
            }

    def _build_assessment_task(self, order_data: dict) -> str:
        """Build a detailed task description from order data."""
        customer = order_data.get("customer", {})
        address = order_data.get("address", {})
        order = order_data.get("order", {})
        items = order_data.get("items", [])

        items_desc = "\n".join([
            f"  - {item.get('name', 'Unknown')} (₹{item.get('price', 0)}) x {item.get('quantity', 1)}"
            for item in items
        ]) or "  No item details available"

        return f"""
URGENT: Assess the following COD order for RTO risk. This order has just been placed and
we need a risk assessment BEFORE dispatch.

═══════════════════════════════════════════════
ORDER DETAILS
═══════════════════════════════════════════════
Order Number: {order.get('order_number', 'N/A')}
Order Amount: ₹{order.get('total_amount', 0):.2f}
Payment Method: Cash on Delivery (COD)
Items:
{items_desc}
Order Time: {order.get('created_at', 'N/A')}
Estimated Shipping Cost: ₹{order.get('forward_shipping_cost', 80):.2f}

═══════════════════════════════════════════════
CUSTOMER PROFILE
═══════════════════════════════════════════════
Name: {customer.get('name', 'N/A')}
Phone: {customer.get('phone', 'N/A')}
Email: {customer.get('email', 'Not provided')}
Account Age: {customer.get('account_age_days', 0)} days
Verified: {'Yes' if customer.get('is_verified', False) else 'No'}
Total Past Orders: {customer.get('total_orders', 0)}
Successful Deliveries: {customer.get('successful_deliveries', 0)}
RTO Count: {customer.get('rto_count', 0)}
Failed Payment Attempts: {customer.get('failed_payment_attempts', 0)}

═══════════════════════════════════════════════
SHIPPING ADDRESS
═══════════════════════════════════════════════
Address Line 1: {address.get('address_line_1', 'N/A')}
Address Line 2: {address.get('address_line_2', '')}
City: {address.get('city', 'N/A')}
State: {address.get('state', 'N/A')}
Pincode: {address.get('pincode', 'N/A')}
Landmark: {address.get('landmark', 'None')}

═══════════════════════════════════════════════
YOUR TASK
═══════════════════════════════════════════════
1. VALIDATE the shipping address using the address_validator tool
2. COMPUTE the risk score using the risk_scorer tool (pass both customer data and address validation results)
3. TAKE ACTION based on the risk level
4. RETURN a complete JSON assessment

For the address_validator tool, pass this JSON:
{json.dumps({
    "address_line_1": address.get('address_line_1', ''),
    "address_line_2": address.get('address_line_2', ''),
    "city": address.get('city', ''),
    "state": address.get('state', ''),
    "pincode": address.get('pincode', ''),
    "landmark": address.get('landmark', ''),
})}

For the risk_scorer tool, you'll need to combine the address validation result with customer data.
Pass this JSON (fill in address_validation with the result from step 1):
{json.dumps({
    "customer": customer,
    "order": {
        "total_amount": order.get('total_amount', 0),
        "item_count": len(items),
        "category": items[0].get('category', '') if items else '',
        "order_hour": order.get('order_hour'),
        "order_day_of_week": order.get('order_day_of_week'),
    },
    "address_validation": "<<FILL_FROM_STEP_1>>",
})}

For the whatsapp_sender tool (if needed for medium/high risk):
- Phone: {customer.get('phone', '')}
- Customer name: {customer.get('name', '')}
- Order number: {order.get('order_number', '')}
- Amount: {order.get('total_amount', 0)}

For the razorpay_payment_link tool (if needed for high risk):
- Token amount for verification: ₹{min(99, order.get('total_amount', 0) * 0.1):.0f}
- Customer details as above
"""

    def _parse_result(self, result, order_data: dict) -> dict:
        """Parse the agent's output into a structured result."""
        result_str = str(result)

        try:
            import re
            json_match = re.search(r'\{[\s\S]*\}', result_str)
            if json_match:
                parsed = json.loads(json_match.group())
                parsed["success"] = True
                parsed["assessed_at"] = datetime.now(timezone.utc).isoformat()
                parsed["order_number"] = order_data.get("order", {}).get("order_number")
                return parsed
        except (json.JSONDecodeError, AttributeError):
            pass

        return {
            "success": True,
            "raw_assessment": result_str,
            "risk_score": 50,
            "risk_level": "MEDIUM",
            "recommended_action": "FLAG_FOR_REVIEW",
            "reasoning": result_str[:1000],
            "assessed_at": datetime.now(timezone.utc).isoformat(),
            "order_number": order_data.get("order", {}).get("order_number"),
            "note": "Could not parse structured JSON; raw assessment provided.",
        }