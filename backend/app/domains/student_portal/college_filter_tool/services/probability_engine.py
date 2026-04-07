from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.domains.student_portal.college_filter_tool.services.metric_comparison_service import (
    RuntimeComparisonSnapshot,
)
from app.domains.student_portal.college_filter_tool.services.policy_resolution_service import (
    ResolvedProbabilityPolicy,
)


DECIMAL_FOUR_PLACES = Decimal("0.0001")
DECIMAL_SIX_PLACES = Decimal("0.000001")
DECIMAL_PERCENT = Decimal("0.01")
UNIT_ZERO = Decimal("0")
UNIT_ONE = Decimal("1")
PROBABILITY_FLOOR_PRIMARY = Decimal("20.0000")
PROBABILITY_MODERATE_MIN = Decimal("45.0000")
PROBABILITY_SAFE_MIN = Decimal("75.0000")


@dataclass(frozen=True)
class ProbabilityAnalysis:
    """
    Final bounded current-round probability result for one row.

    This is the primary numerical driver for Step 7 banding.
    """
    normalized_margin_ratio: Decimal
    weighted_confidence: Decimal

    margin_component: Decimal
    confidence_component: Decimal
    blended_signal: Decimal

    raw_probability: Decimal
    bounded_probability: Decimal
    cold_start_capped: bool


class ProbabilityEngine:
    """
    Step 7E probability engine.

    Formula contract:
    - base all policy tuning on ProbabilityPolicyConfig
    - use Step 7D normalized margin and confidence primitives
    - keep final probability strictly bounded
    - strongly cap cold-start rows using policy
    """

    def compute_probability(
        self,
        *,
        snapshot: RuntimeComparisonSnapshot,
        policy: ResolvedProbabilityPolicy,
    ) -> ProbabilityAnalysis:
        margin_ratio = Decimal(snapshot.margin.normalized_margin_ratio)
        confidence = Decimal(snapshot.confidence.weighted_confidence)

        margin_component = (
            margin_ratio * policy.weight_margin
        ).quantize(DECIMAL_SIX_PLACES, rounding=ROUND_HALF_UP)

        confidence_component = (
            confidence * policy.weight_confidence
        ).quantize(DECIMAL_SIX_PLACES, rounding=ROUND_HALF_UP)

        blended_signal = (
            margin_component + confidence_component
        ).quantize(DECIMAL_SIX_PLACES, rounding=ROUND_HALF_UP)

        raw_probability = (
            policy.probability_base
            + (policy.probability_multiplier * blended_signal)
        ).quantize(DECIMAL_FOUR_PLACES, rounding=ROUND_HALF_UP)

        bounded_probability = self._clamp_probability(
            raw_probability=raw_probability,
            probability_min=policy.probability_min,
            probability_max=policy.probability_max,
        )

        cold_start_capped = False
        if snapshot.confidence.is_cold_start:
            bounded_probability = min(
                bounded_probability,
                policy.cold_start_probability_cap,
            ).quantize(DECIMAL_FOUR_PLACES, rounding=ROUND_HALF_UP)
            cold_start_capped = True

        return ProbabilityAnalysis(
            normalized_margin_ratio=margin_ratio.quantize(DECIMAL_SIX_PLACES, rounding=ROUND_HALF_UP),
            weighted_confidence=confidence.quantize(DECIMAL_SIX_PLACES, rounding=ROUND_HALF_UP),
            margin_component=margin_component,
            confidence_component=confidence_component,
            blended_signal=blended_signal,
            raw_probability=raw_probability,
            bounded_probability=bounded_probability,
            cold_start_capped=cold_start_capped,
        )

    @staticmethod
    def _clamp_probability(
        *,
        raw_probability: Decimal,
        probability_min: Decimal,
        probability_max: Decimal,
    ) -> Decimal:
        bounded = max(probability_min, min(raw_probability, probability_max))
        return bounded.quantize(DECIMAL_FOUR_PLACES, rounding=ROUND_HALF_UP)