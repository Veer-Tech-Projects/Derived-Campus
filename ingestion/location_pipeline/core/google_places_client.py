import os
import re
import logging
import requests
from requests.adapters import HTTPAdapter
from typing import Dict, Any, Optional
from dataclasses import dataclass
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from .pincode_resolver import pincode_resolver

logger = logging.getLogger(__name__)

class ProviderTimeout(Exception): pass
class ProviderMalformedResponse(Exception): pass
class RateLimitExceeded(Exception): pass
class LocationSearchError(Exception): pass

@dataclass
class LocationCandidateDTO:
    raw_address: str
    latitude: float
    longitude: float
    pincode: Optional[str]
    parsed_district: Optional[str]
    parsed_state_code: Optional[str]
    parsed_city: Optional[str]
    is_state_mismatch: bool
    raw_payload: Dict[str, Any]

class GooglePlacesClient:
    """
    Enterprise adapter for Google Places Search via Serper.dev.
    """
    BASE_URL = "https://google.serper.dev/places"
    TIMEOUT_SEC = 10
    PINCODE_REGEX = re.compile(r'\b[1-9][0-9]{5}\b')

    def __init__(self):
        self._api_key = getattr(settings, "SERPER_API_KEY", os.getenv("SERPER_API_KEY"))
        if not self._api_key:
            raise ValueError("CRITICAL: SERPER_API_KEY missing from environment variables.")

        self.session = requests.Session()
        
        adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20)
        self.session.mount("https://", adapter)

        self.session.headers.update({
            "X-API-KEY": self._api_key,
            "Content-Type": "application/json",
            "User-Agent": "Derived-Campus-Location-Pipeline/1.0" # [AUDIT FIX] WAF Protection
        })

    def _build_query(self, canonical_name: str, state_code: str) -> str:
        name_lower = canonical_name.lower()
        if not any(word in name_lower for word in ["college", "institute", "university", "school", "academy"]):
            return f"{canonical_name} college {state_code} India"
        return f"{canonical_name} {state_code} India"

    @retry(
        retry=retry_if_exception_type((requests.exceptions.RequestException, ProviderTimeout, RateLimitExceeded)),
        wait=wait_exponential(multiplier=1.5, min=2, max=10),
        stop=stop_after_attempt(3),
        reraise=True
    )
    def _execute_search(self, query: str) -> Dict[str, Any]:
        payload = {"q": query}
        try:
            response = self.session.post(self.BASE_URL, json=payload, timeout=self.TIMEOUT_SEC)
        except requests.exceptions.Timeout as e:
            raise ProviderTimeout("Serper Places API timed out.") from e

        if response.status_code == 200:
            try:
                return response.json()
            except ValueError as e:
                raise ProviderMalformedResponse("Invalid JSON from Serper") from e
        elif response.status_code == 429:
            # [AUDIT FIX] Explicit Rate Limit routing to trigger Tenacity backoff
            raise RateLimitExceeded("Serper API Rate Limit Exceeded (429).")
        elif response.status_code in (401, 403):
            raise LocationSearchError(f"API Auth/Quota Error: {response.status_code}")
        else:
            response.raise_for_status()

    def search_college_location(self, canonical_name: str, expected_state_code: str) -> Optional[LocationCandidateDTO]:
        query = self._build_query(canonical_name, expected_state_code)
        logger.info(f"[GooglePlaces] Searching location for: '{query}'")

        try:
            raw_json = self._execute_search(query)
        except Exception as e:
            logger.error(f"[GooglePlaces] Search failed for {canonical_name}: {str(e)}")
            return None

        if "places" not in raw_json:
            logger.warning(f"[GooglePlaces] 'places' key missing in response for {canonical_name}")
            return None

        places = raw_json.get("places", [])
        if not places or not isinstance(places, list):
            logger.warning(f"[GooglePlaces] No places found for {canonical_name}")
            return None

        top_result = places[0]
        raw_address = top_result.get("address", "")
        if not raw_address:
            return None

        lat = top_result.get("latitude")
        lng = top_result.get("longitude")
        if lat is None or lng is None:
            geometry = top_result.get("geometry", {}).get("location", {})
            lat = geometry.get("lat")
            lng = geometry.get("lng")

        if lat is None or lng is None:
            logger.warning(f"[GooglePlaces] Coordinates missing for {canonical_name}. Rejecting candidate.")
            return None

        # [AUDIT FIX] Strict Type Casting & Error Handling
        try:
            lat = float(lat)
            lng = float(lng)
        except (ValueError, TypeError):
            logger.warning(f"[GooglePlaces] Malformed coordinate data types for {canonical_name}. Rejecting candidate.")
            return None

        pincode_match = self.PINCODE_REGEX.search(raw_address)
        extracted_pin = pincode_match.group() if pincode_match else None

        parsed_district = None
        parsed_state_code = None
        is_mismatch = False

        if extracted_pin:
            resolved_data = pincode_resolver.resolve(extracted_pin)
            if resolved_data:
                parsed_district = resolved_data.get("district")
                parsed_state_code = resolved_data.get("state_code")
                
                if parsed_state_code and expected_state_code and parsed_state_code.upper() != expected_state_code.upper():
                    is_mismatch = True
                    logger.warning(f"[GooglePlaces] PIN Mismatch! Expected {expected_state_code}, got {parsed_state_code}")

        parsed_city = None
        if not parsed_district:
            parts = [p.strip() for p in raw_address.split(",")]
            if len(parts) >= 2:
                raw_city = parts[-2].replace(extracted_pin, "").strip() if extracted_pin else parts[-2]
                parsed_city = re.sub(r'[^a-zA-Z\s]', '', raw_city).strip()

        return LocationCandidateDTO(
            raw_address=raw_address,
            latitude=lat,
            longitude=lng,
            pincode=extracted_pin,
            parsed_district=parsed_district,
            parsed_state_code=parsed_state_code,
            parsed_city=parsed_city,
            is_state_mismatch=is_mismatch,
            raw_payload=top_result
        )