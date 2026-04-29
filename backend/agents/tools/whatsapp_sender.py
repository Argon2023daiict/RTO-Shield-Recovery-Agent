"""
WhatsApp Communication Tool
Sends templated and dynamic messages to customers via Twilio WhatsApp API.
Used by both Shield Agent (partial payment requests) and Recovery Agent (re-engagement).
"""

import json
import uuid
from typing import ClassVar, Optional, Type
from datetime import datetime, timezone
from crewai.tools import BaseTool

from backend.config import get_settings

settings = get_settings()


class WhatsAppSenderTool(BaseTool):
    name: str = "whatsapp_sender"
    description: str = (
        "Sends WhatsApp messages to customers for order verification, partial payment requests, "
        "or post-RTO recovery outreach. Input should be a JSON string with fields: "
        "phone_number, message_type (verification|partial_payment|recovery|custom), "
        "and context data like customer_name, order_number, amount, discount_code, etc."
    )

    # ✅ ClassVar tells Pydantic: "this is a class constant, NOT a model field"
    TEMPLATES: ClassVar[dict] = {
        "verification": (
            "🛒 *Order Confirmation Required*\n\n"
            "Hi {customer_name}! 👋\n\n"
            "We received your COD order *{order_number}* for ₹{amount}.\n\n"
            "To confirm your order and ensure smooth delivery, please reply with *CONFIRM* "
            "within the next 2 hours.\n\n"
            "If you didn't place this order, reply *CANCEL*.\n\n"
            "Thank you! 🙏\n"
            "— {merchant_name}"
        ),
        "partial_payment": (
            "💳 *Quick Verification for Your Order*\n\n"
            "Hi {customer_name}! 👋\n\n"
            "Your COD order *{order_number}* (₹{amount}) is almost ready to ship! 🚀\n\n"
            "To fast-track your delivery, we'd like to verify your order with a small "
            "token payment of *₹{token_amount}*. This amount will be deducted from your "
            "total COD amount at delivery.\n\n"
            "👉 Pay here: {payment_link}\n\n"
            "This helps us prioritize your order and ensure faster delivery! ⚡\n\n"
            "— {merchant_name}"
        ),
        "recovery": (
            "👋 *We'd Love to Make It Right!*\n\n"
            "Hi {customer_name},\n\n"
            "We noticed your recent order *{order_number}* for *{product_name}* "
            "couldn't be delivered. We're sorry about that! 😔\n\n"
            "Was there an issue? We'd love to help:\n"
            "• Wrong address? We'll update it! 📍\n"
            "• Changed your mind? No worries at all! \n"
            "• Want to try again? Here's a special offer just for you! 🎁\n\n"
            "Use code *{discount_code}* to get *{discount_percent}% OFF* + "
            "*FREE shipping* on your next order!\n\n"
            "👉 Reorder here: {payment_link}\n\n"
            "This offer expires in 48 hours. ⏰\n\n"
            "— {merchant_name}"
        ),
        "recovery_simple": (
            "Hi {customer_name}! 👋\n\n"
            "We noticed you returned *{product_name}* from order *{order_number}*.\n\n"
            "Was there an issue? We'd love to offer you *free shipping* on your next order "
            "to make it right! 🎁\n\n"
            "Use code *{discount_code}* for *{discount_percent}% OFF*.\n\n"
            "— {merchant_name}"
        ),
        "order_cancelled": (
            "ℹ️ *Order Update*\n\n"
            "Hi {customer_name},\n\n"
            "We regret to inform you that your order *{order_number}* has been cancelled "
            "due to verification issues.\n\n"
            "If you'd like to place a new order, we recommend using prepaid payment "
            "for faster processing! 💳\n\n"
            "Need help? Reply to this message.\n\n"
            "— {merchant_name}"
        ),
    }

    def _run(self, message_json: str) -> str:
        """Send a WhatsApp message to the customer."""
        try:
            data = json.loads(message_json) if isinstance(message_json, str) else message_json

            phone_number = data.get("phone_number", "")
            message_type = data.get("message_type", "custom")
            context = data.get("context", {})

            # Validate phone number
            if not phone_number or len(phone_number) < 10:
                return json.dumps({
                    "success": False,
                    "error": "Invalid phone number",
                    "message_id": None,
                })

            # Build message from template or use custom
            if message_type == "custom":
                message_body = data.get("custom_message", "")
            elif message_type in self.TEMPLATES:
                template = self.TEMPLATES[message_type]
                # Fill in template with defaults for missing fields
                context.setdefault("merchant_name", "ShopEasy")
                context.setdefault("customer_name", "Customer")
                context.setdefault("order_number", "N/A")
                context.setdefault("amount", "0")
                context.setdefault("product_name", "your item")
                context.setdefault("token_amount", "49")
                context.setdefault("payment_link", "#")
                context.setdefault("discount_code", "WELCOME10")
                context.setdefault("discount_percent", "10")

                try:
                    message_body = template.format(**context)
                except KeyError as e:
                    return json.dumps({
                        "success": False,
                        "error": f"Missing template variable: {e}",
                        "message_id": None,
                    })
            else:
                return json.dumps({
                    "success": False,
                    "error": f"Unknown message type: {message_type}",
                    "available_types": list(self.TEMPLATES.keys()) + ["custom"],
                    "message_id": None,
                })

            # Send via Twilio or simulate
            result = self._send_message(phone_number, message_body)

            return json.dumps({
                "success": result["success"],
                "message_id": result.get("message_id"),
                "phone_number": phone_number,
                "message_type": message_type,
                "message_preview": message_body[:200] + "..." if len(message_body) > 200 else message_body,
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "delivery_status": result.get("status", "unknown"),
                "error": result.get("error"),
            })

        except json.JSONDecodeError:
            return json.dumps({
                "success": False,
                "error": "Invalid JSON input",
                "message_id": None,
            })
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "message_id": None,
            })

    def _send_message(self, phone_number: str, message_body: str) -> dict:
        """
        Send message via Twilio WhatsApp API.
        Falls back to simulation mode if Twilio is not configured.
        """
        if settings.twilio_account_sid and settings.twilio_auth_token:
            try:
                from twilio.rest import Client

                client = Client(settings.twilio_account_sid, settings.twilio_auth_token)

                # Ensure WhatsApp format
                to_number = phone_number if phone_number.startswith("whatsapp:") else f"whatsapp:{phone_number}"

                message = client.messages.create(
                    body=message_body,
                    from_=settings.twilio_whatsapp_from,
                    to=to_number,
                )

                return {
                    "success": True,
                    "message_id": message.sid,
                    "status": message.status,
                }

            except Exception as e:
                return {
                    "success": False,
                    "error": f"Twilio error: {str(e)}",
                    "message_id": None,
                    "status": "failed",
                }
        else:
            # Simulation mode
            simulated_id = f"SIM_{uuid.uuid4().hex[:12].upper()}"
            print(f"\n{'='*60}")
            print(f"📱 SIMULATED WhatsApp Message")
            print(f"   To: {phone_number}")
            print(f"   ID: {simulated_id}")
            print(f"{'='*60}")
            print(message_body)
            print(f"{'='*60}\n")

            return {
                "success": True,
                "message_id": simulated_id,
                "status": "simulated",
            }