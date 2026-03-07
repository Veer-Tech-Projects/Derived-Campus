import os
import logging
import requests
from typing import List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.models import MediaTypeEnum

from .constants import DEFAULT_REQUEST_TIMEOUT_SEC, DEFAULT_RETRY_ATTEMPTS
from .search_interface import (
    ImageSearchProvider,
    ImageCandidate,
    SearchTelemetry,
    SearchResult,
    SearchProviderError,
    RateLimitExceeded,
    ProviderTimeout,
    ProviderMalformedResponse
)

logger = logging.getLogger(__name__)

class GoogleImageSearchClient(ImageSearchProvider):
    """
    Enterprise adapter for Google Image Search via Serper.dev.
    Bypasses the hostile GCP Custom Search API deprecation while maintaining 
    strict IO boundaries, JSON firewalls, and HTTP state management.
    """

    BASE_URL = "https://google.serper.dev/images"

    def __init__(self):
        # We use os.getenv as a fallback so you don't have to modify your Pydantic settings.py
        self._api_key = getattr(settings, "SERPER_API_KEY", os.getenv("SERPER_API_KEY"))
        
        # Fail-fast on boot if config is missing
        if not self._api_key:
            raise ValueError("CRITICAL: SERPER_API_KEY missing from environment variables.")
            
        # Connection Pooling (TCP Handshake Optimization)
        self.session = requests.Session()
        
        # Enforce JSON and Auth at the session level
        self.session.headers.update({
            "X-API-KEY": self._api_key,
            "Content-Type": "application/json"
        })

    @property
    def provider_name(self) -> str:
        return "SERPER_GOOGLE"

    # ============================================================
    # Public Entry Points
    # ============================================================

    def search_logo(self, canonical_name: str, city: str, max_results: int = 5) -> SearchResult:
        query = self._build_logo_query(canonical_name, city)
        return self._orchestrate_search(query, MediaTypeEnum.LOGO, max_results)

    def search_campus_hero(self, canonical_name: str, city: str, max_results: int = 5) -> SearchResult:
        query = self._build_campus_query(canonical_name, city)
        return self._orchestrate_search(query, MediaTypeEnum.CAMPUS_HERO, max_results)

    # ============================================================
    # Core Orchestration
    # ============================================================

    def _orchestrate_search(self, query: str, media_type: MediaTypeEnum, max_results: int) -> SearchResult:
        """Coordinates the exact sequence: Telemetry -> IO -> Parse -> Govern -> Cap."""
        telemetry = SearchTelemetry(raw_query=query)
        logger.info(f"[{self.provider_name}] Executing {media_type.value} search. Query: '{query}'")

        try:
            # 1. Network IO (Defensive)
            raw_json = self._execute_search(query)
            
            # 2. Schema Firewall (Parsing)
            raw_candidates = self._parse_response(raw_json)
            
            # 3. Governance Layer (State-Machine rules applied)
            approved_candidates = self.apply_governance(raw_candidates, media_type, telemetry)
            
            # 4. Defensive Double-Limiting
            final_candidates = approved_candidates[:max_results]
            
            return SearchResult(candidates=final_candidates, telemetry=telemetry)
            
        except Exception as e:
            logger.error(f"[{self.provider_name}] Search failed for '{query}': {type(e).__name__} - {str(e)}")
            raise

    # ============================================================
    # Defensive IO & Retry Layer
    # ============================================================

    @retry(
        retry=retry_if_exception_type((
            requests.exceptions.RequestException, 
            ProviderTimeout, 
            RateLimitExceeded
        )),
        wait=wait_exponential(multiplier=1.5, min=2, max=10),
        stop=stop_after_attempt(DEFAULT_RETRY_ATTEMPTS),
        reraise=True
    )
    def _execute_search(self, query: str) -> Dict[str, Any]:
        """
        Executes HTTP POST call to Serper with strict Status Matrix enforcement.
        """
        payload = {
            "q": query
        }

        try:
            response = self.session.post(
                self.BASE_URL, 
                json=payload, 
                timeout=DEFAULT_REQUEST_TIMEOUT_SEC
            )
        except requests.exceptions.Timeout as e:
            raise ProviderTimeout(f"Serper API timed out after {DEFAULT_REQUEST_TIMEOUT_SEC}s") from e
        except requests.exceptions.RequestException as e:
            raise 

        # --- THE HTTP STATUS MATRIX ---
        if response.status_code == 200:
            try:
                return response.json()
            except ValueError as e:
                raise ProviderMalformedResponse("Serper API returned malformed JSON payload") from e

        elif response.status_code in (403, 401):
            raise SearchProviderError(f"Serper API HTTP {response.status_code}: Invalid API Key or Out of Credits.")

        elif 500 <= response.status_code < 600:
            response.raise_for_status() 

        else:
            raise SearchProviderError(f"Serper API returned unexpected HTTP {response.status_code}: {response.text}")

    # ============================================================
    # JSON Schema Firewall
    # ============================================================

    def _parse_response(self, raw_json: Dict[str, Any]) -> List[ImageCandidate]:
        """
        Translates raw Serper JSON into our immutable DTOs.
        Silently drops malformed items without crashing the pipeline.
        """
        candidates: List[ImageCandidate] = []
        
        # Serper puts image results in the 'images' array
        items = raw_json.get("images")
        if not items:
            return [] 
            
        if not isinstance(items, list):
            raise ProviderMalformedResponse("'images' key in Serper payload is not a list")

        for rank, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
                
            try:
                image_url = item.get("imageUrl")
                context_url = item.get("link")
                
                # Strict structure requirement
                if not image_url or not context_url:
                    continue

                width = item.get("imageWidth")
                height = item.get("imageHeight")
                
                # Byte size is not provided by Serper, Downloader will compute it safely
                byte_size = None 

                # Safe integer casting for metadata
                width = int(width) if width else None
                height = int(height) if height else None

                source_domain = self.extract_domain(image_url)
                context_domain = self.extract_domain(context_url)

                candidates.append(ImageCandidate(
                    image_url=image_url,
                    context_url=context_url,
                    source_domain=source_domain,
                    context_domain=context_domain,
                    rank_position=rank,
                    provider_name=self.provider_name,
                    width=width,
                    height=height,
                    byte_size=byte_size
                ))

            except Exception as e:
                logger.debug(f"[{self.provider_name}] Dropped malformed item at rank {rank}: {e}")
                continue

        return candidates