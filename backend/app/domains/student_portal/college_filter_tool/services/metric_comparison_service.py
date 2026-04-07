from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from fastapi import HTTPException

from app.domains.student_portal.college_filter_tool.schemas.runtime_search_schemas import (
    MetricType,
)
from app.domains.student_portal.college_filter_tool.repositories.search_repository import (
    SearchRepositoryRow,
)
from app.domains.student_portal.college_filter_tool.services.policy_resolution_service import (
    ResolvedProbabilityPolicy,
)


DECIMAL_FOUR_PLACES = Decimal("0.0001")
DECIMAL_SIX_PLACES = Decimal("0.000001")
EPSILON = Decimal("0.000001")


@dataclass(frozen=True)
class ConfidenceAnalysis:
    """
    Pure confidence composite from Step 5/6 evidence inputs.
    Range is clamped to [0, 1].
    """
    round_evidence_score: Decimal
    round_stability_score: Decimal
    current_year_presence_score: Decimal
    weighted_confidence: Decimal
    is_cold_start: bool


@dataclass(frozen=True)
class MarginAnalysis:
    """
    Metric-normalized comparison result.

    Core invariant:
    positive margin always means the student cleared the cutoff.
    """
    metric_type: MetricType
    user_score: Decimal
    current_round_cutoff_value: Decimal

    raw_margin: Decimal
    normalized_margin_ratio: Decimal
    absolute_gap_ratio: Decimal

    qualified_against_current_anchor: bool


@dataclass(frozen=True)
class RuntimeComparisonSnapshot:
    """
    Consolidated Step 7D comparison primitive.
    This becomes the direct input to Step 7E probability and band logic.
    """
    margin: MarginAnalysis
    confidence: ConfidenceAnalysis


class MetricComparisonService:
    """
    Computes deterministic runtime comparison primitives for one candidate row.

    Step 7D scope:
    - compute metric-aware positive-margin semantics
    - compute normalized margin ratio for rank/percentile exams
    - compute confidence composite from Step 5/6 evidence signals
    - do NOT compute final probability or band classification here
    """

    def analyze_row(
        self,
        *,
        row: SearchRepositoryRow,
        user_score: Decimal,
        metric_type: MetricType,
        policy: ResolvedProbabilityPolicy,
    ) -> RuntimeComparisonSnapshot:
        if row.current_round_cutoff_value is None:
            raise HTTPException(
                status_code=500,
                detail=f"Search row {row.id} is missing current_round_cutoff_value",
            )

        margin = self._compute_margin_analysis(
            metric_type=metric_type,
            user_score=user_score,
            current_round_cutoff_value=Decimal(row.current_round_cutoff_value),
        )
        confidence = self._compute_confidence_analysis(
            row=row,
            policy=policy,
        )

        return RuntimeComparisonSnapshot(
            margin=margin,
            confidence=confidence,
        )

    def _compute_margin_analysis(
        self,
        *,
        metric_type: MetricType,
        user_score: Decimal,
        current_round_cutoff_value: Decimal,
    ) -> MarginAnalysis:
        if current_round_cutoff_value <= 0:
            raise HTTPException(
                status_code=500,
                detail="current_round_cutoff_value must be > 0 for runtime comparison",
            )

        if user_score <= 0:
            raise HTTPException(
                status_code=400,
                detail="user score must be > 0",
            )

        if metric_type == MetricType.RANK:
            raw_margin = current_round_cutoff_value - user_score
            denominator = current_round_cutoff_value

        elif metric_type == MetricType.PERCENTILE:
            raw_margin = user_score - current_round_cutoff_value
            denominator = Decimal("100")

        else:
            raise HTTPException(
                status_code=500,
                detail=f"Unsupported metric type for comparison: {metric_type}",
            )

        normalized_margin_ratio = (
            raw_margin / denominator
        ).quantize(DECIMAL_SIX_PLACES, rounding=ROUND_HALF_UP)

        absolute_gap_ratio = (
            abs(raw_margin) / denominator
        ).quantize(DECIMAL_SIX_PLACES, rounding=ROUND_HALF_UP)

        return MarginAnalysis(
            metric_type=metric_type,
            user_score=user_score,
            current_round_cutoff_value=current_round_cutoff_value,
            raw_margin=raw_margin.quantize(DECIMAL_FOUR_PLACES, rounding=ROUND_HALF_UP),
            normalized_margin_ratio=normalized_margin_ratio,
            absolute_gap_ratio=absolute_gap_ratio,
            qualified_against_current_anchor=raw_margin >= 0,
        )

    def _compute_confidence_analysis(
        self,
        *,
        row: SearchRepositoryRow,
        policy: ResolvedProbabilityPolicy,
    ) -> ConfidenceAnalysis:
        evidence = self._clamp_unit_decimal(Decimal(row.round_evidence_score))
        stability = self._clamp_unit_decimal(Decimal(row.round_stability_score))
        current_year = self._clamp_unit_decimal(Decimal(row.current_year_presence_score))

        weight_sum = (
            policy.weight_round_evidence
            + policy.weight_round_stability
            + policy.weight_current_year_presence
        )

        if weight_sum <= 0:
            raise HTTPException(
                status_code=500,
                detail=f"Policy {policy.policy_key} has non-positive confidence weight sum",
            )

        weighted_confidence = (
            (
                evidence * policy.weight_round_evidence
                + stability * policy.weight_round_stability
                + current_year * policy.weight_current_year_presence
            ) / weight_sum
        ).quantize(DECIMAL_SIX_PLACES, rounding=ROUND_HALF_UP)

        weighted_confidence = self._clamp_unit_decimal(weighted_confidence)

        return ConfidenceAnalysis(
            round_evidence_score=evidence,
            round_stability_score=stability,
            current_year_presence_score=current_year,
            weighted_confidence=weighted_confidence,
            is_cold_start=bool(row.is_cold_start),
        )

    @staticmethod
    def _clamp_unit_decimal(value: Decimal) -> Decimal:
        if value < Decimal("0"):
            return Decimal("0")
        if value > Decimal("1"):
            return Decimal("1")
        return value.quantize(DECIMAL_SIX_PLACES, rounding=ROUND_HALF_UP)