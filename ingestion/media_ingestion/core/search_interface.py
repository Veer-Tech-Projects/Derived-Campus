from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse
import logging

from app.models import MediaTypeEnum

from .constants import (
    NOISE_DOMAINS, AUTHORITY_TLDS, 
    LOGO_QUERY_TEMPLATE, CAMPUS_HERO_QUERY_TEMPLATE,
    LOGO_MIN_WIDTH, LOGO_MIN_HEIGHT, LOGO_MAX_ASPECT_RATIO, LOGO_MAX_BYTES,
    CAMPUS_MIN_WIDTH, CAMPUS_MIN_HEIGHT, CAMPUS_MAX_BYTES
)

logger = logging.getLogger(__name__)

# ============================================================
# Failure Taxonomy
# ============================================================
class SearchProviderError(Exception): pass
class RateLimitExceeded(SearchProviderError): pass
class ProviderTimeout(SearchProviderError): pass
class ProviderMalformedResponse(SearchProviderError): pass


# ============================================================
# Data Transfer Objects
# ============================================================
@dataclass(frozen=True)
class ImageCandidate:
    image_url: str
    context_url: str  
    source_domain: str
    context_domain: str
    rank_position: int
    provider_name: str
    
    width: Optional[int] = None
    height: Optional[int] = None
    byte_size: Optional[int] = None

    def is_noise(self) -> bool:
        """Defense in Depth: Fails closed on malformed domains, checks both URLs against noise."""
        if self.source_domain == "malformed_domain" or self.context_domain == "malformed_domain":
            return True
            
        return any(
            noise in self.source_domain or noise in self.context_domain 
            for noise in NOISE_DOMAINS
        )

    def is_authoritative(self) -> bool:
        """Checks if the context page belongs to a verified educational TLD."""
        return self.context_domain.endswith(AUTHORITY_TLDS)


@dataclass
class SearchTelemetry:
    """Granular Observability hook for the Admin Dashboard."""
    raw_query: str
    total_results_returned: int = 0
    dropped_by_noise_filter: int = 0
    dropped_by_missing_metadata: int = 0  # NEW: Tracks API anomalies
    dropped_by_dimension_filter: int = 0
    valid_candidates: int = 0


@dataclass
class SearchResult:
    candidates: List[ImageCandidate]
    telemetry: SearchTelemetry


# ============================================================
# Abstract Interface
# ============================================================
class ImageSearchProvider(ABC):
    """
    CONTRACT: All concrete providers MUST support '-site:' exclusion 
    syntax in their base query resolution.
    """
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Forces concrete classes to declare their identity."""
        pass

    @abstractmethod
    def search_logo(self, canonical_name: str, city: str, max_results: int = 5) -> SearchResult:
        pass

    @abstractmethod
    def search_campus_hero(self, canonical_name: str, city: str, max_results: int = 5) -> SearchResult:
        pass

    # ---------------------------
    # Deterministic Query Builder
    # ---------------------------
    def _build_logo_query(self, canonical_name: str, city: str) -> str:
        base = LOGO_QUERY_TEMPLATE.format(canonical_name=canonical_name, city=city or "")
        return self._inject_governance(base)

    def _build_campus_query(self, canonical_name: str, city: str) -> str:
        base = CAMPUS_HERO_QUERY_TEMPLATE.format(canonical_name=canonical_name, city=city or "")
        return self._inject_governance(base)

    def _inject_governance(self, base_query: str) -> str:
        """Injects syntax-level blacklist exclusions (-site:domain.com)."""
        exclusions = " ".join(f"-site:{domain}" for domain in NOISE_DOMAINS)
        return f"{base_query} {exclusions}".strip()

    # ---------------------------
    # Governance Validation
    # ---------------------------
    @staticmethod
    def extract_domain(url: str) -> str:
        """Strict domain extraction. Returns 'malformed_domain' on failure."""
        try:
            domain = urlparse(url).netloc.lower()
            return domain if domain else "malformed_domain"
        except Exception:
            return "malformed_domain"

    def apply_governance(
        self, 
        raw_candidates: List[ImageCandidate], 
        media_type: MediaTypeEnum,
        telemetry: SearchTelemetry
    ) -> List[ImageCandidate]:
        """
        Executes strict noise and dimensional filtering. 
        Updates telemetry dynamically.
        """
        telemetry.total_results_returned = len(raw_candidates)
        approved = []

        for candidate in raw_candidates:
            # 1. Noise Filter (Masked CDNs & Malformed Domains)
            if candidate.is_noise():
                telemetry.dropped_by_noise_filter += 1
                continue

            # 2. Metadata Presence Gate (Google must provide dimensions)
            if not candidate.width or not candidate.height:
                telemetry.dropped_by_missing_metadata += 1
                continue

            # 3. Mathematical Dimensional Guardrails
            if not self._passes_dimensions(candidate, media_type):
                telemetry.dropped_by_dimension_filter += 1
                continue

            approved.append(candidate)

        # 4. Mathematical Compound Sort: Authoritative first, preserve original search engine rank
        approved.sort(key=lambda c: (not c.is_authoritative(), c.rank_position))
        
        telemetry.valid_candidates = len(approved)
        return approved

    def _passes_dimensions(self, candidate: ImageCandidate, media_type: MediaTypeEnum) -> bool:
        """
        Mathematical verification of image viability before IO.
        Note: Metadata existence is verified prior to calling this method.
        """
        if media_type == MediaTypeEnum.LOGO:
            if candidate.byte_size and candidate.byte_size > LOGO_MAX_BYTES:
                return False
            if candidate.width < LOGO_MIN_WIDTH or candidate.height < LOGO_MIN_HEIGHT:
                return False
            # Prevent ultra-wide banners masquerading as logos
            aspect_ratio = max(candidate.width, candidate.height) / min(candidate.width, candidate.height)
            if aspect_ratio > LOGO_MAX_ASPECT_RATIO:
                return False

        elif media_type == MediaTypeEnum.CAMPUS_HERO:
            if candidate.byte_size and candidate.byte_size > CAMPUS_MAX_BYTES:
                return False
            if candidate.width < CAMPUS_MIN_WIDTH or candidate.height < CAMPUS_MIN_HEIGHT:
                return False

        return True