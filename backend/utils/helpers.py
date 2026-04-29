"""
Utility helper functions used across the application.
"""

import re
import uuid
import random
import string
from datetime import datetime, timezone
from typing import Optional


def generate_order_number(prefix: str = "ORD") -> str:
    """Generate a unique, human-readable order number."""
    return f"{prefix}-{random.randint(100000, 999999)}"


def generate_discount_code(prefix: str = "RTO") -> str:
    """Generate a unique discount code."""
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}-{random_part}"


def sanitize_phone(phone: str) -> str:
    """Normalize Indian phone numbers to +91XXXXXXXXXX format."""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)

    # Handle various formats
    if len(digits) == 10:
        return f"+91{digits}"
    elif len(digits) == 11 and digits.startswith("0"):
        return f"+91{digits[1:]}"
    elif len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    elif len(digits) == 13 and digits.startswith("091"):
        return f"+91{digits[3:]}"
    else:
        return phone  # Return as-is if can't normalize


def mask_phone(phone: str) -> str:
    """Mask phone number for display: +91XXXX543210 → +91XXXX****10"""
    if len(phone) >= 10:
        return phone[:-6] + "****" + phone[-2:]
    return phone


def mask_email(email: str) -> Optional[str]:
    """Mask email for display: user@domain.com → u***@domain.com"""
    if not email or "@" not in email:
        return email
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}@{domain}"


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def format_inr(amount: float) -> str:
    """Format amount in Indian Rupee notation."""
    if amount >= 10000000:  # 1 Crore
        return f"₹{amount / 10000000:.2f} Cr"
    elif amount >= 100000:  # 1 Lakh
        return f"₹{amount / 100000:.2f} L"
    elif amount >= 1000:
        return f"₹{amount:,.2f}"
    else:
        return f"₹{amount:.2f}"