"""
Address Intelligence Tool
Validates shipping addresses using geocoding and heuristic analysis.
Detects vague addresses, pincode-city mismatches, and other red flags.
"""

import re
import json
from typing import Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from backend.config import get_settings

settings = get_settings()

# Known Indian pincode-city mappings (subset for demo; in production, use India Post API)
PINCODE_CITY_DB = {
    "400001": "Mumbai", "400050": "Mumbai", "400070": "Mumbai", "400093": "Mumbai",
    "110001": "Delhi", "110016": "Delhi", "110085": "Delhi", "110092": "Delhi",
    "560001": "Bangalore", "560034": "Bangalore", "560068": "Bangalore", "560100": "Bangalore",
    "600001": "Chennai", "600017": "Chennai", "600042": "Chennai", "600096": "Chennai",
    "500001": "Hyderabad", "500034": "Hyderabad", "500072": "Hyderabad", "500081": "Hyderabad",
    "411001": "Pune", "411014": "Pune", "411038": "Pune", "411057": "Pune",
    "700001": "Kolkata", "700019": "Kolkata", "700054": "Kolkata", "700091": "Kolkata",
    "302001": "Jaipur", "302015": "Jaipur", "302020": "Jaipur", "302033": "Jaipur",
}

# Vague address indicators
VAGUE_PATTERNS = [
    r"near\s+(the\s+)?(big|old|small)\s+\w+",
    r"behind\s+(the\s+)?\w+",
    r"opposite\s+(the\s+)?\w+",
    r"ask\s+(anyone|somebody|people)",
    r"(near|beside|next\s+to)\s+(temple|mosque|church|school|hospital|tree|shop|paan)",
    r"\d+(st|nd|rd|th)\s+house\s+from",
    r"village\s+road",
    r"(yellow|red|blue|green|white)\s+(gate|building|house)",
    r"(neem|banyan|peepal|mango)\s+tree",
]

# Valid address patterns (structured)
STRUCTURED_PATTERNS = [
    r"(flat|apt|apartment|house)\s*(no\.?)?\s*\d+",
    r"(plot|sector|block|phase)\s*[\-\s]?\d+",
    r"\d+[\/\-]\w+",  # Like 12/A or 15-B
    r"(floor|storey)\s*\d+",
    r"(tower|wing|building)\s*[\-\s]?\w+",
]


class AddressValidationInput(BaseModel):
    address_line_1: str = Field(description="Primary address line")
    address_line_2: Optional[str] = Field(None, description="Secondary address line")
    city: str = Field(description="City name")
    state: str = Field(description="State name")
    pincode: str = Field(description="6-digit pincode")
    landmark: Optional[str] = Field(None, description="Landmark near the address")


class AddressValidatorTool(BaseTool):
    name: str = "address_validator"
    description: str = (
        "Validates a shipping address for completeness, accuracy, and risk signals. "
        "Checks pincode-city match, detects vague/incomplete addresses, and provides "
        "a validation score from 0 (invalid) to 100 (fully verified). "
        "Input should be a JSON string with fields: address_line_1, city, state, pincode."
    )

    def _run(self, address_json: str) -> str:
        """Validate the address and return a detailed risk analysis."""
        try:
            # Parse input
            if isinstance(address_json, str):
                addr_data = json.loads(address_json)
            else:
                addr_data = address_json

            address_line = addr_data.get("address_line_1", "")
            city = addr_data.get("city", "")
            state = addr_data.get("state", "")
            pincode = addr_data.get("pincode", "")
            landmark = addr_data.get("landmark", "")

            full_address = f"{address_line} {addr_data.get('address_line_2', '')} {landmark}".strip()

            validation_result = {
                "is_valid": True,
                "score": 100.0,
                "flags": [],
                "details": {},
            }

            # 1. Pincode format validation
            if not re.match(r"^\d{6}$", pincode):
                validation_result["flags"].append("INVALID_PINCODE_FORMAT")
                validation_result["score"] -= 30
                validation_result["details"]["pincode_format"] = "Invalid - not 6 digits"
            else:
                validation_result["details"]["pincode_format"] = "Valid"

            # 2. Pincode-City match check
            expected_city = PINCODE_CITY_DB.get(pincode)
            if expected_city:
                if expected_city.lower() != city.lower():
                    validation_result["flags"].append("PINCODE_CITY_MISMATCH")
                    validation_result["score"] -= 35
                    validation_result["details"]["pincode_city_match"] = (
                        f"MISMATCH: Pincode {pincode} maps to {expected_city}, "
                        f"but city is listed as {city}"
                    )
                else:
                    validation_result["details"]["pincode_city_match"] = "Match confirmed"
            else:
                validation_result["details"]["pincode_city_match"] = (
                    f"Pincode {pincode} not in local DB - requires external verification"
                )
                validation_result["score"] -= 5

            # 3. Vague address detection
            vague_indicators = []
            full_address_lower = full_address.lower()
            for pattern in VAGUE_PATTERNS:
                match = re.search(pattern, full_address_lower)
                if match:
                    vague_indicators.append(match.group())

            if vague_indicators:
                penalty = min(len(vague_indicators) * 12, 40)
                validation_result["flags"].append("VAGUE_ADDRESS")
                validation_result["score"] -= penalty
                validation_result["details"]["vague_indicators"] = vague_indicators
                validation_result["details"]["vague_severity"] = (
                    "HIGH" if len(vague_indicators) >= 2 else "MEDIUM"
                )

            # 4. Structured address check
            has_structure = False
            for pattern in STRUCTURED_PATTERNS:
                if re.search(pattern, full_address_lower):
                    has_structure = True
                    break

            if not has_structure:
                validation_result["flags"].append("NO_STRUCTURED_ADDRESS")
                validation_result["score"] -= 15
                validation_result["details"]["structured_address"] = "No flat/house/plot number detected"
            else:
                validation_result["details"]["structured_address"] = "Structured address found"

            # 5. Address completeness check
            if len(address_line.strip()) < 10:
                validation_result["flags"].append("ADDRESS_TOO_SHORT")
                validation_result["score"] -= 20
                validation_result["details"]["completeness"] = "Address is too short to be reliable"
            elif len(address_line.strip()) < 20:
                validation_result["score"] -= 5
                validation_result["details"]["completeness"] = "Address is somewhat brief"
            else:
                validation_result["details"]["completeness"] = "Adequate length"

            # 6. Missing fields check
            missing = []
            if not city.strip():
                missing.append("city")
            if not state.strip():
                missing.append("state")
            if not pincode.strip():
                missing.append("pincode")
            if missing:
                validation_result["flags"].append("MISSING_FIELDS")
                validation_result["score"] -= len(missing) * 15
                validation_result["details"]["missing_fields"] = missing

            # Clamp score
            validation_result["score"] = max(0, min(100, validation_result["score"]))
            validation_result["is_valid"] = validation_result["score"] >= 40

            # Geocoding attempt (if Google Maps API is configured)
            geocode_result = self._try_geocode(full_address, city, state, pincode)
            if geocode_result:
                validation_result["details"]["geocoding"] = geocode_result
                if not geocode_result.get("success", False):
                    validation_result["flags"].append("GEOCODING_FAILED")
                    validation_result["score"] = max(0, validation_result["score"] - 10)

            # Risk classification
            score = validation_result["score"]
            if score >= 80:
                validation_result["risk_classification"] = "LOW"
            elif score >= 50:
                validation_result["risk_classification"] = "MEDIUM"
            else:
                validation_result["risk_classification"] = "HIGH"

            return json.dumps(validation_result, indent=2)

        except json.JSONDecodeError:
            return json.dumps({
                "error": "Invalid JSON input",
                "is_valid": False,
                "score": 0,
                "flags": ["INVALID_INPUT"],
            })
        except Exception as e:
            return json.dumps({
                "error": str(e),
                "is_valid": False,
                "score": 0,
                "flags": ["VALIDATION_ERROR"],
            })

    def _try_geocode(self, address: str, city: str, state: str, pincode: str) -> Optional[dict]:
        """Attempt geocoding via Google Maps API if available."""
        if not settings.google_maps_api_key:
            return {"success": False, "reason": "Google Maps API key not configured"}

        try:
            import googlemaps
            gmaps = googlemaps.Client(key=settings.google_maps_api_key)
            full_query = f"{address}, {city}, {state}, {pincode}, India"
            geocode_result = gmaps.geocode(full_query)

            if geocode_result:
                location = geocode_result[0]["geometry"]["location"]
                formatted = geocode_result[0].get("formatted_address", "")
                return {
                    "success": True,
                    "lat": location["lat"],
                    "lng": location["lng"],
                    "formatted_address": formatted,
                    "confidence": geocode_result[0]["geometry"].get("location_type", "APPROXIMATE"),
                }
            else:
                return {"success": False, "reason": "No geocoding results found"}
        except Exception as e:
            return {"success": False, "reason": f"Geocoding error: {str(e)}"}