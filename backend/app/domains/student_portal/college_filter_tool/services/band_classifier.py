from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from app.domains.student_portal.college_filter_tool.schemas.runtime_search_schemas import (
    CollegeBand,
)
from app.domains.student_portal.college_filter_tool.services.metric_comparison_service import (
    RuntimeComparisonSnapshot,
)
from app.domains.student_portal.college_filter_tool.services.policy_resolution_service import (
    ResolvedProbabilityPolicy,
)
from app.domains.student_portal.college_filter_tool.services.probability_engine import (
    ProbabilityAnalysis,
)


DECIMAL_FOUR_PLACES = Decimal("0.0001")
PRIMARY_SAFE_MIN_PROBABILITY = Decimal("75.0000")
PRIMARY_MODERATE_MIN_PROBABILITY = Decimal("45.0000")
PRIMARY_HARD_MIN_PROBABILITY = Decimal("20.0000")


@dataclass(frozen=True)
class BandDecision:
    """
    Primary band result.

    band=None means exclude from primary safety-band response.
    """
    band: Optional[CollegeBand]
    reason: str


@dataclass(frozen=True)
class SuggestedEligibility:
    """
    Separate helper for the alternative-branch/course SUGGESTED engine.
    """
    eligible: bool
    adjusted_margin_ratio: Decimal
    adjusted_probability: Decimal
    reason: str


class BandClassifier:
    """
    Step 7E band classifier.

    Business rules:
    - primary bands are decided primarily by final probability percent
    - SAFE / MODERATE / HARD thresholds are probability-led
    - rows with probability < 20 are excluded
    - SUGGESTED is NOT a primary band spill bucket; it is a separate eligibility helper
    """

    def classify_primary_band(
        self,
        *,
        snapshot: RuntimeComparisonSnapshot,
        probability: ProbabilityAnalysis,
        policy: ResolvedProbabilityPolicy,
    ) -> BandDecision:
        margin = Decimal(snapshot.margin.normalized_margin_ratio)
        confidence = Decimal(snapshot.confidence.weighted_confidence)
        final_probability = Decimal(probability.bounded_probability)

        # < 20 is explicitly excluded by approved business rule.
        if final_probability < PRIMARY_HARD_MIN_PROBABILITY:
            return BandDecision(
                band=None,
                reason="probability_below_primary_floor",
            )

        # SAFE remains probability-led, but still obeys policy minimums.
        if final_probability >= PRIMARY_SAFE_MIN_PROBABILITY:
            if snapshot.confidence.is_cold_start:
                if (
                    margin >= policy.cold_start_safe_min_margin
                    and confidence >= policy.cold_start_safe_min_confidence
                ):
                    return BandDecision(
                        band=CollegeBand.SAFE,
                        reason="safe_probability_and_cold_start_thresholds_met",
                    )
            else:
                if (
                    margin >= policy.safe_min_margin
                    and confidence >= policy.safe_min_confidence
                ):
                    return BandDecision(
                        band=CollegeBand.SAFE,
                        reason="safe_probability_and_thresholds_met",
                    )

        if final_probability >= PRIMARY_MODERATE_MIN_PROBABILITY:
            if (
                margin >= policy.moderate_min_margin
                and confidence >= policy.moderate_min_confidence
            ):
                return BandDecision(
                    band=CollegeBand.MODERATE,
                    reason="moderate_probability_and_thresholds_met",
                )

        if final_probability >= PRIMARY_HARD_MIN_PROBABILITY:
            if (
                margin >= policy.hard_min_margin
                and confidence >= policy.hard_min_confidence
            ):
                return BandDecision(
                    band=CollegeBand.HARD,
                    reason="hard_probability_and_thresholds_met",
                )

        return BandDecision(
            band=None,
            reason="primary_thresholds_not_met_after_policy_gates",
        )

    def evaluate_suggested_eligibility(
        self,
        *,
        snapshot: RuntimeComparisonSnapshot,
        probability: ProbabilityAnalysis,
        policy: ResolvedProbabilityPolicy,
    ) -> SuggestedEligibility:
        """
        SUGGESTED is a separate alternative-path helper.

        Eligibility rule implemented from your approved design:
        - alternative branch/course engine only
        - must still be reasonably viable
        - use policy penalties for suggested scoring
        - final adjusted probability must still be >= 45
        """
        adjusted_margin_ratio = (
            Decimal(snapshot.margin.normalized_margin_ratio)
            - policy.suggested_score_penalty
        ).quantize(DECIMAL_FOUR_PLACES, rounding=ROUND_HALF_UP)

        adjusted_probability = (
            Decimal(probability.bounded_probability)
            - policy.suggested_probability_penalty
        ).quantize(DECIMAL_FOUR_PLACES, rounding=ROUND_HALF_UP)

        confidence = Decimal(snapshot.confidence.weighted_confidence)

        if adjusted_probability < PRIMARY_MODERATE_MIN_PROBABILITY:
            return SuggestedEligibility(
                eligible=False,
                adjusted_margin_ratio=adjusted_margin_ratio,
                adjusted_probability=adjusted_probability,
                reason="suggested_probability_below_45",
            )

        if adjusted_margin_ratio < policy.suggested_min_margin:
            return SuggestedEligibility(
                eligible=False,
                adjusted_margin_ratio=adjusted_margin_ratio,
                adjusted_probability=adjusted_probability,
                reason="suggested_margin_below_policy_minimum",
            )

        if confidence < policy.suggested_min_confidence:
            return SuggestedEligibility(
                eligible=False,
                adjusted_margin_ratio=adjusted_margin_ratio,
                adjusted_probability=adjusted_probability,
                reason="suggested_confidence_below_policy_minimum",
            )

        return SuggestedEligibility(
            eligible=True,
            adjusted_margin_ratio=adjusted_margin_ratio,
            adjusted_probability=adjusted_probability,
            reason="suggested_thresholds_met",
        )