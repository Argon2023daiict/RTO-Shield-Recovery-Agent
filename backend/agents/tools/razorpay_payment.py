"""
Razorpay Payment Link Tool
Creates payment links for partial prepayment verification and recovery re-orders.
Integrates with Razorpay's Payment Links API to close the loop.
"""

import json
import uuid
import time
from typing import Optional
from crewai.tools import BaseTool

from backend.config import get_settings

settings = get_settings()


class RazorpayPaymentTool(BaseTool):
    name: str = "razorpay_payment_link"
    description: str = (
        "Creates a Razorpay payment link for collecting partial prepayment (order verification) "
        "or recovery payment (re-ordering after RTO). Input should be a JSON string with: "
        "amount (in INR), purpose (verification|recovery), customer_name, customer_phone, "
        "customer_email (optional), order_number, description."
    )

    def _run(self, payment_json: str) -> str:
        """Create a Razorpay payment link."""
        try:
            data = json.loads(payment_json) if isinstance(payment_json, str) else payment_json

            amount_inr = data.get("amount", 0)
            purpose = data.get("purpose", "verification")
            customer_name = data.get("customer_name", "Customer")
            customer_phone = data.get("customer_phone", "")
            customer_email = data.get("customer_email", "")
            order_number = data.get("order_number", "")
            description = data.get("description", "")
            discount_code = data.get("discount_code")

            if amount_inr <= 0:
                return json.dumps({
                    "success": False,
                    "error": "Amount must be greater than 0",
                    "payment_link": None,
                })

            # Build description
            if purpose == "verification":
                if not description:
                    description = (
                        f"Token payment of ₹{amount_inr} for COD order {order_number}. "
                        f"This amount will be adjusted in your final COD payment."
                    )
                expire_minutes = 120  # 2 hours for verification
            elif purpose == "recovery":
                if not description:
                    discount_msg = f" (Discount: {discount_code})" if discount_code else ""
                    description = (
                        f"Re-order payment for {order_number}{discount_msg}. "
                        f"Free shipping included!"
                    )
                expire_minutes = 2880  # 48 hours for recovery
            else:
                if not description:
                    description = f"Payment for order {order_number}"
                expire_minutes = 1440  # 24 hours default

            # Attempt real Razorpay API call
            result = self._create_payment_link(
                amount_paise=int(amount_inr * 100),  # Razorpay uses paise
                description=description,
                customer_name=customer_name,
                customer_phone=customer_phone,
                customer_email=customer_email,
                order_number=order_number,
                expire_minutes=expire_minutes,
                purpose=purpose,
            )

            return json.dumps(result, indent=2)

        except json.JSONDecodeError:
            return json.dumps({
                "success": False,
                "error": "Invalid JSON input",
                "payment_link": None,
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "payment_link": None,
            })

    def _create_payment_link(
        self,
        amount_paise: int,
        description: str,
        customer_name: str,
        customer_phone: str,
        customer_email: str,
        order_number: str,
        expire_minutes: int,
        purpose: str,
    ) -> dict:
        """Create payment link via Razorpay API or simulate."""

        if settings.razorpay_key_id and settings.razorpay_key_secret and \
           not settings.razorpay_key_id.startswith("rzp_test_xxx"):
            try:
                import razorpay

                client = razorpay.Client(
                    auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
                )

                # Build payment link payload
                payload = {
                    "amount": amount_paise,
                    "currency": "INR",
                    "accept_partial": False,
                    "description": description,
                    "customer": {
                        "name": customer_name,
                        "contact": customer_phone,
                    },
                    "notify": {
                        "sms": True,
                        "email": bool(customer_email),
                    },
                    "reminder_enable": True,
                    "notes": {
                        "order_number": order_number,
                        "purpose": purpose,
                        "source": "rto_shield_agent",
                    },
                    "callback_url": f"{settings.backend_url}/api/webhooks/razorpay/payment",
                    "callback_method": "get",
                    "expire_by": int(time.time()) + (expire_minutes * 60),
                }

                if customer_email:
                    payload["customer"]["email"] = customer_email

                link = client.payment_link.create(payload)

                return {
                    "success": True,
                    "payment_link_id": link["id"],
                    "payment_link": link["short_url"],
                    "amount_inr": amount_paise / 100,
                    "currency": "INR",
                    "status": link["status"],
                    "expire_by": link.get("expire_by"),
                    "purpose": purpose,
                    "order_number": order_number,
                    "mode": "live",
                }

            except Exception as e:
                return {
                    "success": False,
                    "error": f"Razorpay API error: {str(e)}",
                    "payment_link": None,
                    "mode": "live_failed",
                }
        else:
            # Simulation mode
            simulated_id = f"plink_sim_{uuid.uuid4().hex[:16]}"
            simulated_url = f"https://rzp.io/i/{simulated_id[:10]}"

            print(f"\n{'='*60}")
            print(f"💳 SIMULATED Razorpay Payment Link")
            print(f"   ID: {simulated_id}")
            print(f"   URL: {simulated_url}")
            print(f"   Amount: ₹{amount_paise / 100:.2f}")
            print(f"   Purpose: {purpose}")
            print(f"   For: {customer_name} ({customer_phone})")
            print(f"   Order: {order_number}")
            print(f"{'='*60}\n")

            return {
                "success": True,
                "payment_link_id": simulated_id,
                "payment_link": simulated_url,
                "amount_inr": amount_paise / 100,
                "currency": "INR",
                "status": "created",
                "expire_by": int(time.time()) + (expire_minutes * 60),
                "purpose": purpose,
                "order_number": order_number,
                "mode": "simulated",
            }