from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, List, Optional
from uuid import UUID

from app.domains.student_portal.college_filter_tool.schemas.runtime_search_schemas import (
    CollegeBand,
)
from app.domains.student_portal.college_filter_tool.repositories.search_repository import (
    SearchRepositoryRow,
)
from app.domains.student_portal.college_filter_tool.services.band_classifier import (
    BandDecision,
    SuggestedEligibility,
)
from app.domains.student_portal.college_filter_tool.services.metric_comparison_service import (
    RuntimeComparisonSnapshot,
)
from app.domains.student_portal.college_filter_tool.services.probability_engine import (
    ProbabilityAnalysis,
)


@dataclass(frozen=True)
class RankedCandidate:
    """
    Fully scored runtime row ready for sorting/capping/pagination.
    """
    row: SearchRepositoryRow
    snapshot: RuntimeComparisonSnapshot
    probability: ProbabilityAnalysis
    band_decision: BandDecision
    suggested_eligibility: SuggestedEligibility | None = None


class BestFitSortService:
    """
    Best-fit ordering service.

    Locked business contract:
    1. smaller positive margin first
    2. then probability descending
    3. then college name ascending
    4. then stable unique tie-breakers
    """

    def sort_primary_band(
        self,
        *,
        candidates: Iterable[RankedCandidate],
        band: CollegeBand,
    ) -> List[RankedCandidate]:
        filtered = [
            candidate
            for candidate in candidates
            if candidate.band_decision.band == band
        ]
        return sorted(filtered, key=self._primary_best_fit_key)

    def sort_suggested(
        self,
        *,
        candidates: Iterable[RankedCandidate],
    ) -> List[RankedCandidate]:
        filtered = [
            candidate
            for candidate in candidates
            if candidate.suggested_eligibility is not None
            and candidate.suggested_eligibility.eligible
        ]
        return sorted(filtered, key=self._suggested_best_fit_key)

    @staticmethod
    def _primary_best_fit_key(candidate: RankedCandidate):
        """
        Best-fit ordering:
        - primary objective: closest viable fit
        - secondary: higher probability
        - tertiary: stable alphabetical ordering
        - final: stable identity ordering
        """
        margin_ratio = Decimal(candidate.snapshot.margin.normalized_margin_ratio)
        probability = Decimal(candidate.probability.bounded_probability)

        # positive-or-zero first, negatives after
        qualification_bucket = 0 if margin_ratio >= 0 else 1

        # smaller positive margin first; for negative margins, closest miss first
        fit_distance = abs(margin_ratio)

        return (
            qualification_bucket,
            fit_distance,
            -probability,
            candidate.row.college_name.lower(),
            candidate.row.college_id,
            candidate.row.program_code or "",
            candidate.row.seat_bucket_code,
        )

    @staticmethod
    def _suggested_best_fit_key(candidate: RankedCandidate):
        """
        Suggested ordering:
        - smaller adjusted positive margin first
        - then adjusted probability descending
        - then stable college ordering
        """
        adjusted_margin = Decimal(candidate.suggested_eligibility.adjusted_margin_ratio)
        adjusted_probability = Decimal(candidate.suggested_eligibility.adjusted_probability)

        qualification_bucket = 0 if adjusted_margin >= 0 else 1
        fit_distance = abs(adjusted_margin)

        return (
            qualification_bucket,
            fit_distance,
            -adjusted_probability,
            candidate.row.college_name.lower(),
            candidate.row.college_id,
            candidate.row.program_code or "",
            candidate.row.seat_bucket_code,
        )