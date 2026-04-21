from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from time import perf_counter
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.student_portal.college_filter_tool.schemas.runtime_search_schemas import (
    BandCountsDTO,
    BandPaginationDTO,
    BandResultDTO,
    CollegeBand,
    CollegeCardDTO,
    CollegeFilterSearchRequest,
    CollegeFilterSearchResponse,
    ComparisonContextDTO,
    PathSummaryDTO,
    ProbabilityEvidenceDTO,
    SearchBandsDTO,
)
from app.domains.student_portal.college_filter_tool.repositories.search_repository import (
    SearchRepository,
    SearchRepositoryRow,
)
from app.domains.student_portal.college_filter_tool.services.band_classifier import (
    BandClassifier,
    BandDecision,
    SuggestedEligibility,
)
from app.domains.student_portal.college_filter_tool.services.band_pagination_service import (
    BandPaginationService,
    PaginatedBandSlice,
)
from app.domains.student_portal.college_filter_tool.services.best_fit_sort_service import (
    BestFitSortService,
    RankedCandidate,
)
from app.domains.student_portal.college_filter_tool.services.metric_comparison_service import (
    ConfidenceAnalysis,
    MarginAnalysis,
    MetricComparisonService,
    RuntimeComparisonSnapshot,
)
from app.domains.student_portal.college_filter_tool.services.path_validation_service import (
    PathValidationService,
    ResolvedPathContext,
)
from app.domains.student_portal.college_filter_tool.services.policy_resolution_service import (
    PolicyResolutionService,
)
from app.domains.student_portal.college_filter_tool.services.probability_engine import (
    ProbabilityAnalysis,
    ProbabilityEngine,
)
from app.domains.student_portal.college_filter_tool.services.search_snapshot_cache_service import (
    college_filter_search_snapshot_cache_service,
)


logger = logging.getLogger(__name__)

DECIMAL_FOUR_PLACES = Decimal("0.0001")


# ======================================================
# RUNTIME-ONLY INTERNAL SNAPSHOT DATACLASSES
# ======================================================

@dataclass(frozen=True)
class ComputedSearchSnapshotRuntime:
    fingerprint: str
    path: PathSummaryDTO
    user_score: Decimal
    safe_sorted: List[RankedCandidate]
    moderate_sorted: List[RankedCandidate]
    hard_sorted: List[RankedCandidate]
    suggested_sorted: List[RankedCandidate]
    total_matching_count: int
    generated_at: datetime
    primary_row_count: int
    suggested_row_count: int


# ======================================================
# Pydantic snapshot models for Redis-safe serialization
# ======================================================

class PathSummarySnapshotModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path_id: UUID
    path_key: str
    visible_label: str
    exam_family: str
    resolved_exam_code: Optional[str] = None
    education_type: Optional[str] = None
    selection_type: Optional[str] = None
    metric_type: str
    expected_max_rounds: int
    supports_branch: bool
    supports_course_relaxation: bool
    supports_location_filter: bool
    supports_opening_rank: bool


class SearchRepositoryRowSnapshotModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    path_id: UUID
    path_key: str
    exam_code: str

    live_round_number: int
    comparison_year: int
    comparison_round_number: int

    college_id: UUID
    college_name: str
    institute_code: str
    institute_name: str

    program_code: str
    program_name: str
    branch_option_key: Optional[str] = None

    seat_bucket_code: str
    category_name: Optional[str] = None
    reservation_type: Optional[str] = None
    location_type: Optional[str] = None
    course_type: Optional[str] = None

    state_code: Optional[str] = None
    district: Optional[str] = None
    pincode: Optional[str] = None

    hero_storage_key: Optional[str] = None
    hero_public_url: Optional[str] = None

    current_round_cutoff_value: Optional[Decimal] = None
    is_projected_current_round: bool

    opening_rank: Optional[Decimal] = None

    latest_year_available: int
    latest_round_available: int


class MarginAnalysisSnapshotModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_type: str
    user_score: Decimal
    current_round_cutoff_value: Decimal
    raw_margin: Decimal
    normalized_margin_ratio: Decimal
    absolute_gap_ratio: Decimal
    qualified_against_current_anchor: bool


class ConfidenceAnalysisSnapshotModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    round_evidence_score: Decimal
    round_stability_score: Decimal
    current_year_presence_score: Decimal
    weighted_confidence: Decimal
    is_cold_start: bool


class RuntimeComparisonSnapshotModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    margin: MarginAnalysisSnapshotModel
    confidence: ConfidenceAnalysisSnapshotModel


class ProbabilityAnalysisSnapshotModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    normalized_margin_ratio: Decimal
    weighted_confidence: Decimal
    margin_component: Decimal
    confidence_component: Decimal
    blended_signal: Decimal
    raw_probability: Decimal
    bounded_probability: Decimal
    cold_start_capped: bool


class BandDecisionSnapshotModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    band: Optional[CollegeBand] = None
    reason: str


class SuggestedEligibilitySnapshotModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eligible: bool
    adjusted_margin_ratio: Decimal
    adjusted_probability: Decimal
    reason: str


class RankedCandidateSnapshotModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    row: SearchRepositoryRowSnapshotModel
    snapshot: RuntimeComparisonSnapshotModel
    probability: ProbabilityAnalysisSnapshotModel
    band_decision: BandDecisionSnapshotModel
    suggested_eligibility: Optional[SuggestedEligibilitySnapshotModel] = None


class ComputedSearchSnapshotModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fingerprint: str
    path: PathSummarySnapshotModel
    user_score: Decimal
    safe_sorted: List[RankedCandidateSnapshotModel]
    moderate_sorted: List[RankedCandidateSnapshotModel]
    hard_sorted: List[RankedCandidateSnapshotModel]
    suggested_sorted: List[RankedCandidateSnapshotModel]
    total_matching_count: int
    generated_at: datetime
    primary_row_count: int
    suggested_row_count: int


class CollegeFilterRuntimeService:
    """
    Step 7G orchestration service.

    Responsibilities:
    - resolve path + validate request
    - run primary search
    - resolve policy per row
    - compute margin/confidence, probability, and primary band decision
    - run suggested secondary query
    - evaluate suggested eligibility
    - sort/cap/paginate all bands
    - map runtime results into the final API DTO
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = SearchRepository(db)
        self.policy_resolution_service = PolicyResolutionService(db)
        self.metric_comparison_service = MetricComparisonService()
        self.probability_engine = ProbabilityEngine()
        self.band_classifier = BandClassifier()
        self.best_fit_sort_service = BestFitSortService()
        self.band_pagination_service = BandPaginationService()

    async def search(
        self,
        *,
        request: CollegeFilterSearchRequest,
    ) -> CollegeFilterSearchResponse:
        total_started_at = perf_counter()
        cache_status = "miss"

        fingerprint = college_filter_search_snapshot_cache_service.build_fingerprint(
            path_id=str(request.path_id),
            score=request.score,
            filters=request.filters,
            sort_mode=request.sort_mode.value,
        )

        snapshot_model: ComputedSearchSnapshotModel | None = None
        cached_payload = college_filter_search_snapshot_cache_service.load_snapshot_json(
            fingerprint=fingerprint
        )

        if cached_payload:
            try:
                snapshot_model = ComputedSearchSnapshotModel.model_validate_json(
                    cached_payload
                )
                cache_status = "hit"
            except Exception:
                logger.exception(
                    "College-filter snapshot payload validation failed. Recomputing fresh. "
                    "fingerprint=%s",
                    fingerprint,
                )
                cache_status = "invalid_payload"
                snapshot_model = None

        if snapshot_model is None:
            runtime_snapshot = await self._compute_search_snapshot_runtime(
                request=request,
                fingerprint=fingerprint,
            )
            snapshot_model = self._to_snapshot_model(runtime_snapshot)

            try:
                college_filter_search_snapshot_cache_service.store_snapshot_json(
                    fingerprint=fingerprint,
                    payload_json=snapshot_model.model_dump_json(),
                )
            except Exception:
                # service already fails open; this is just an extra safety belt
                logger.exception(
                    "College-filter snapshot store raised unexpectedly for fingerprint=%s",
                    fingerprint,
                )
                cache_status = (
                    "store_failed_after_invalid_payload"
                    if cache_status == "invalid_payload"
                    else "store_failed"
                )
            else:
                if cache_status != "invalid_payload":
                    cache_status = "miss"

        pagination_started_at = perf_counter()
        response = self._build_response_from_snapshot_model(
            snapshot_model=snapshot_model,
            page_size=request.page_size,
            page_by_band=request.page_by_band,
        )
        pagination_ms = round((perf_counter() - pagination_started_at) * 1000, 2)
        total_search_ms = round((perf_counter() - total_started_at) * 1000, 2)

        logger.info(
            "College-filter search completed "
            "fingerprint=%s cache_status=%s path_id=%s path_key=%s "
            "primary_rows=%s suggested_rows=%s safe_count=%s moderate_count=%s hard_count=%s suggested_count=%s "
            "pagination_ms=%s total_search_ms=%s",
            fingerprint,
            cache_status,
            snapshot_model.path.path_id,
            snapshot_model.path.path_key,
            snapshot_model.primary_row_count,
            snapshot_model.suggested_row_count,
            len(snapshot_model.safe_sorted),
            len(snapshot_model.moderate_sorted),
            len(snapshot_model.hard_sorted),
            len(snapshot_model.suggested_sorted),
            pagination_ms,
            total_search_ms,
        )

        return response

    # ======================================================
    # SNAPSHOT COMPUTATION
    # ======================================================

    async def _compute_search_snapshot_runtime(
        self,
        *,
        request: CollegeFilterSearchRequest,
        fingerprint: str,
    ) -> ComputedSearchSnapshotRuntime:
        validation_started_at = perf_counter()
        path_context = await PathValidationService.resolve_and_validate(
            db=self.db,
            request=request,
        )
        path_validation_ms = round((perf_counter() - validation_started_at) * 1000, 2)

        primary_query_started_at = perf_counter()
        primary_result = await self.repository.search_primary(
            path_context=path_context,
        )
        primary_query_ms = round((perf_counter() - primary_query_started_at) * 1000, 2)

        primary_scoring_started_at = perf_counter()
        primary_ranked_candidates = await self._score_primary_rows(
            path_context=path_context,
            rows=primary_result.rows,
        )
        primary_scoring_ms = round((perf_counter() - primary_scoring_started_at) * 1000, 2)

        primary_identity_set = {
            (
                candidate.row.college_id,
                candidate.row.program_code,
                candidate.row.seat_bucket_code,
            )
            for candidate in primary_ranked_candidates
        }

        suggested_query_started_at = perf_counter()
        suggested_result = await self.repository.search_suggested_candidates(
            path_context=path_context,
            exclude_identities=primary_identity_set,
        )
        suggested_query_ms = round((perf_counter() - suggested_query_started_at) * 1000, 2)

        suggested_scoring_started_at = perf_counter()
        suggested_ranked_candidates = await self._score_suggested_rows(
            path_context=path_context,
            rows=suggested_result.rows,
        )
        suggested_scoring_ms = round((perf_counter() - suggested_scoring_started_at) * 1000, 2)

        sorting_started_at = perf_counter()
        safe_sorted = self.best_fit_sort_service.sort_primary_band(
            candidates=primary_ranked_candidates,
            band=CollegeBand.SAFE,
        )
        moderate_sorted = self.best_fit_sort_service.sort_primary_band(
            candidates=primary_ranked_candidates,
            band=CollegeBand.MODERATE,
        )
        hard_sorted = self.best_fit_sort_service.sort_primary_band(
            candidates=primary_ranked_candidates,
            band=CollegeBand.HARD,
        )
        suggested_sorted = self.best_fit_sort_service.sort_suggested(
            candidates=suggested_ranked_candidates,
        )
        sorting_ms = round((perf_counter() - sorting_started_at) * 1000, 2)

        total_matching_count = (
            len(safe_sorted)
            + len(moderate_sorted)
            + len(hard_sorted)
        )

        snapshot = ComputedSearchSnapshotRuntime(
            fingerprint=fingerprint,
            path=self._build_path_summary(path_context),
            user_score=request.score.quantize(DECIMAL_FOUR_PLACES, rounding=ROUND_HALF_UP),
            safe_sorted=safe_sorted,
            moderate_sorted=moderate_sorted,
            hard_sorted=hard_sorted,
            suggested_sorted=suggested_sorted,
            total_matching_count=total_matching_count,
            generated_at=datetime.now(timezone.utc),
            primary_row_count=len(primary_result.rows),
            suggested_row_count=len(suggested_result.rows),
        )

        logger.info(
            "College-filter runtime snapshot computed "
            "fingerprint=%s path_id=%s path_key=%s "
            "path_validation_ms=%s primary_query_ms=%s primary_scoring_ms=%s "
            "suggested_query_ms=%s suggested_scoring_ms=%s sorting_ms=%s "
            "primary_rows=%s suggested_rows=%s safe_count=%s moderate_count=%s hard_count=%s suggested_count=%s",
            fingerprint,
            snapshot.path.path_id,
            snapshot.path.path_key,
            path_validation_ms,
            primary_query_ms,
            primary_scoring_ms,
            suggested_query_ms,
            suggested_scoring_ms,
            sorting_ms,
            snapshot.primary_row_count,
            snapshot.suggested_row_count,
            len(snapshot.safe_sorted),
            len(snapshot.moderate_sorted),
            len(snapshot.hard_sorted),
            len(snapshot.suggested_sorted),
        )

        return snapshot

    # ======================================================
    # PRIMARY / SUGGESTED SCORING
    # ======================================================

    async def _score_primary_rows(
        self,
        *,
        path_context: ResolvedPathContext,
        rows: List[SearchRepositoryRow],
    ) -> List[RankedCandidate]:
        if not rows:
            return []

        policies_by_row_id = await self.policy_resolution_service.resolve_map_for_rows(rows)

        ranked_candidates: List[RankedCandidate] = []
        for row in rows:
            policy = policies_by_row_id[row.id]
            snapshot = self.metric_comparison_service.analyze_row(
                row=row,
                user_score=path_context.user_score,
                metric_type=path_context.metric_type,
                policy=policy,
            )
            probability = self.probability_engine.compute_probability(
                snapshot=snapshot,
                policy=policy,
            )
            band_decision = self.band_classifier.classify_primary_band(
                snapshot=snapshot,
                probability=probability,
                policy=policy,
            )

            ranked_candidates.append(
                RankedCandidate(
                    row=row,
                    snapshot=snapshot,
                    probability=probability,
                    band_decision=band_decision,
                    suggested_eligibility=None,
                )
            )

        return ranked_candidates

    async def _score_suggested_rows(
        self,
        *,
        path_context: ResolvedPathContext,
        rows: List[SearchRepositoryRow],
    ) -> List[RankedCandidate]:
        if not rows:
            return []

        policies_by_row_id = await self.policy_resolution_service.resolve_map_for_rows(rows)

        ranked_candidates: List[RankedCandidate] = []
        for row in rows:
            policy = policies_by_row_id[row.id]
            snapshot = self.metric_comparison_service.analyze_row(
                row=row,
                user_score=path_context.user_score,
                metric_type=path_context.metric_type,
                policy=policy,
            )
            probability = self.probability_engine.compute_probability(
                snapshot=snapshot,
                policy=policy,
            )
            band_decision = self.band_classifier.classify_primary_band(
                snapshot=snapshot,
                probability=probability,
                policy=policy,
            )
            suggested_eligibility = self.band_classifier.evaluate_suggested_eligibility(
                snapshot=snapshot,
                probability=probability,
                policy=policy,
            )

            ranked_candidates.append(
                RankedCandidate(
                    row=row,
                    snapshot=snapshot,
                    probability=probability,
                    band_decision=band_decision,
                    suggested_eligibility=suggested_eligibility,
                )
            )

        return ranked_candidates

    # ======================================================
    # SNAPSHOT MODEL BRIDGE
    # ======================================================

    def _to_snapshot_model(
        self,
        runtime_snapshot: ComputedSearchSnapshotRuntime,
    ) -> ComputedSearchSnapshotModel:
        return ComputedSearchSnapshotModel(
            fingerprint=runtime_snapshot.fingerprint,
            path=PathSummarySnapshotModel(
                path_id=runtime_snapshot.path.path_id,
                path_key=runtime_snapshot.path.path_key,
                visible_label=runtime_snapshot.path.visible_label,
                exam_family=runtime_snapshot.path.exam_family,
                resolved_exam_code=runtime_snapshot.path.resolved_exam_code,
                education_type=runtime_snapshot.path.education_type,
                selection_type=runtime_snapshot.path.selection_type,
                metric_type=runtime_snapshot.path.metric_type.value,
                expected_max_rounds=runtime_snapshot.path.expected_max_rounds,
                supports_branch=runtime_snapshot.path.supports_branch,
                supports_course_relaxation=runtime_snapshot.path.supports_course_relaxation,
                supports_location_filter=runtime_snapshot.path.supports_location_filter,
                supports_opening_rank=runtime_snapshot.path.supports_opening_rank,
            ),
            user_score=runtime_snapshot.user_score,
            safe_sorted=[self._to_snapshot_candidate_model(candidate) for candidate in runtime_snapshot.safe_sorted],
            moderate_sorted=[self._to_snapshot_candidate_model(candidate) for candidate in runtime_snapshot.moderate_sorted],
            hard_sorted=[self._to_snapshot_candidate_model(candidate) for candidate in runtime_snapshot.hard_sorted],
            suggested_sorted=[self._to_snapshot_candidate_model(candidate) for candidate in runtime_snapshot.suggested_sorted],
            total_matching_count=runtime_snapshot.total_matching_count,
            generated_at=runtime_snapshot.generated_at,
            primary_row_count=runtime_snapshot.primary_row_count,
            suggested_row_count=runtime_snapshot.suggested_row_count,
        )

    def _to_snapshot_candidate_model(
        self,
        candidate: RankedCandidate,
    ) -> RankedCandidateSnapshotModel:
        row = candidate.row
        snapshot = candidate.snapshot
        probability = candidate.probability

        suggested_eligibility_model = None
        if candidate.suggested_eligibility is not None:
            suggested_eligibility_model = SuggestedEligibilitySnapshotModel(
                eligible=bool(candidate.suggested_eligibility.eligible),
                adjusted_margin_ratio=Decimal(candidate.suggested_eligibility.adjusted_margin_ratio),
                adjusted_probability=Decimal(candidate.suggested_eligibility.adjusted_probability),
                reason=candidate.suggested_eligibility.reason,
            )

        return RankedCandidateSnapshotModel(
            row=SearchRepositoryRowSnapshotModel(
                id=row.id,
                path_id=row.path_id,
                path_key=row.path_key,
                exam_code=row.exam_code,
                live_round_number=row.live_round_number,
                comparison_year=row.comparison_year,
                comparison_round_number=row.comparison_round_number,
                college_id=row.college_id,
                college_name=row.college_name,
                institute_code=row.institute_code,
                institute_name=row.institute_name,
                program_code=row.program_code,
                program_name=row.program_name,
                branch_option_key=row.branch_option_key,
                seat_bucket_code=row.seat_bucket_code,
                category_name=row.category_name,
                reservation_type=row.reservation_type,
                location_type=row.location_type,
                course_type=row.course_type,
                state_code=row.state_code,
                district=row.district,
                pincode=row.pincode,
                hero_storage_key=row.hero_storage_key,
                hero_public_url=row.hero_public_url,
                current_round_cutoff_value=row.current_round_cutoff_value,
                is_projected_current_round=bool(row.is_projected_current_round),
                opening_rank=row.opening_rank,
                latest_year_available=row.latest_year_available,
                latest_round_available=row.latest_round_available,
            ),
            snapshot=RuntimeComparisonSnapshotModel(
                margin=MarginAnalysisSnapshotModel(
                    metric_type=snapshot.margin.metric_type.value,
                    user_score=Decimal(snapshot.margin.user_score),
                    current_round_cutoff_value=Decimal(snapshot.margin.current_round_cutoff_value),
                    raw_margin=Decimal(snapshot.margin.raw_margin),
                    normalized_margin_ratio=Decimal(snapshot.margin.normalized_margin_ratio),
                    absolute_gap_ratio=Decimal(snapshot.margin.absolute_gap_ratio),
                    qualified_against_current_anchor=bool(
                        snapshot.margin.qualified_against_current_anchor
                    ),
                ),
                confidence=ConfidenceAnalysisSnapshotModel(
                    round_evidence_score=Decimal(snapshot.confidence.round_evidence_score),
                    round_stability_score=Decimal(snapshot.confidence.round_stability_score),
                    current_year_presence_score=Decimal(snapshot.confidence.current_year_presence_score),
                    weighted_confidence=Decimal(snapshot.confidence.weighted_confidence),
                    is_cold_start=bool(snapshot.confidence.is_cold_start),
                ),
            ),
            probability=ProbabilityAnalysisSnapshotModel(
                normalized_margin_ratio=Decimal(probability.normalized_margin_ratio),
                weighted_confidence=Decimal(probability.weighted_confidence),
                margin_component=Decimal(probability.margin_component),
                confidence_component=Decimal(probability.confidence_component),
                blended_signal=Decimal(probability.blended_signal),
                raw_probability=Decimal(probability.raw_probability),
                bounded_probability=Decimal(probability.bounded_probability),
                cold_start_capped=bool(probability.cold_start_capped),
            ),
            band_decision=BandDecisionSnapshotModel(
                band=candidate.band_decision.band,
                reason=candidate.band_decision.reason,
            ),
            suggested_eligibility=suggested_eligibility_model,
        )

    # ======================================================
    # RESPONSE MATERIALIZATION FROM SNAPSHOT MODEL
    # ======================================================

    def _build_response_from_snapshot_model(
        self,
        *,
        snapshot_model: ComputedSearchSnapshotModel,
        page_size: int,
        page_by_band,
    ) -> CollegeFilterSearchResponse:
        paginated = self.band_pagination_service.paginate_all_bands(
            safe_candidates=snapshot_model.safe_sorted,
            moderate_candidates=snapshot_model.moderate_sorted,
            hard_candidates=snapshot_model.hard_sorted,
            suggested_candidates=snapshot_model.suggested_sorted,
            page_request=page_by_band,
            page_size=page_size,
        )

        band_counts = BandCountsDTO(
            safe=len(snapshot_model.safe_sorted),
            moderate=len(snapshot_model.moderate_sorted),
            hard=len(snapshot_model.hard_sorted),
            suggested=paginated[CollegeBand.SUGGESTED].capped_total_available,
        )

        return CollegeFilterSearchResponse(
            path=PathSummaryDTO(
                path_id=snapshot_model.path.path_id,
                path_key=snapshot_model.path.path_key,
                visible_label=snapshot_model.path.visible_label,
                exam_family=snapshot_model.path.exam_family,
                resolved_exam_code=snapshot_model.path.resolved_exam_code,
                education_type=snapshot_model.path.education_type,
                selection_type=snapshot_model.path.selection_type,
                metric_type=snapshot_model.path.metric_type,
                expected_max_rounds=snapshot_model.path.expected_max_rounds,
                supports_branch=snapshot_model.path.supports_branch,
                supports_course_relaxation=snapshot_model.path.supports_course_relaxation,
                supports_location_filter=snapshot_model.path.supports_location_filter,
                supports_opening_rank=snapshot_model.path.supports_opening_rank,
            ),
            user_score=Decimal(snapshot_model.user_score).quantize(
                DECIMAL_FOUR_PLACES,
                rounding=ROUND_HALF_UP,
            ),
            total_matching_count=snapshot_model.total_matching_count,
            band_counts=band_counts,
            bands=SearchBandsDTO(
                safe=self._map_snapshot_paginated_band_slice(
                    band=CollegeBand.SAFE,
                    paginated_slice=paginated[CollegeBand.SAFE],
                ),
                moderate=self._map_snapshot_paginated_band_slice(
                    band=CollegeBand.MODERATE,
                    paginated_slice=paginated[CollegeBand.MODERATE],
                ),
                hard=self._map_snapshot_paginated_band_slice(
                    band=CollegeBand.HARD,
                    paginated_slice=paginated[CollegeBand.HARD],
                ),
                suggested=self._map_snapshot_paginated_band_slice(
                    band=CollegeBand.SUGGESTED,
                    paginated_slice=paginated[CollegeBand.SUGGESTED],
                ),
            ),
            generated_at=snapshot_model.generated_at,
        )

    # ======================================================
    # DTO MAPPING
    # ======================================================

    def _build_path_summary(
        self,
        path_context: ResolvedPathContext,
    ) -> PathSummaryDTO:
        return PathSummaryDTO(
            path_id=path_context.path_id,
            path_key=path_context.path_key,
            visible_label=path_context.visible_label,
            exam_family=path_context.exam_family,
            resolved_exam_code=path_context.resolved_exam_code,
            education_type=path_context.education_type,
            selection_type=path_context.selection_type,
            metric_type=path_context.metric_type,
            expected_max_rounds=path_context.expected_max_rounds,
            supports_branch=path_context.supports_branch,
            supports_course_relaxation=path_context.supports_course_relaxation,
            supports_location_filter=path_context.supports_location_filter,
            supports_opening_rank=path_context.supports_opening_rank,
        )

    def _map_snapshot_paginated_band_slice(
        self,
        *,
        band: CollegeBand,
        paginated_slice: PaginatedBandSlice,
    ) -> BandResultDTO:
        return BandResultDTO(
            band=band,
            items=[
                self._map_snapshot_candidate_to_card(
                    band=band,
                    candidate=candidate,
                )
                for candidate in paginated_slice.items
            ],
            pagination=BandPaginationDTO(
                page=paginated_slice.page,
                page_size=paginated_slice.page_size,
                total_matching_count=paginated_slice.all_matching_count,
                capped_total_available=paginated_slice.capped_total_available,
                has_next_page=paginated_slice.has_next_page,
                cap_reached=paginated_slice.cap_reached,
            ),
        )

    def _map_snapshot_candidate_to_card(
        self,
        *,
        band: CollegeBand,
        candidate: RankedCandidateSnapshotModel,
    ) -> CollegeCardDTO:
        row = candidate.row
        snapshot = candidate.snapshot
        probability = candidate.probability

        return CollegeCardDTO(
            college_id=row.college_id,
            college_name=row.college_name,
            institute_code=row.institute_code,
            exam_code=row.exam_code,
            path_id=row.path_id,
            path_key=row.path_key,
            program_code=row.program_code,
            program_name=row.program_name,
            branch_option_key=row.branch_option_key,
            branch_display_name=row.program_name,
            seat_bucket_code=row.seat_bucket_code,
            category_name=row.category_name,
            course_type=row.course_type,
            location_type=row.location_type,
            reservation_type=row.reservation_type,
            gender=None,
            city=None,
            district=row.district,
            state_code=row.state_code,
            pincode=row.pincode,
            logo_url=None,
            hero_storage_key=row.hero_storage_key,
            hero_media_url=row.hero_public_url,
            current_round_cutoff_value=Decimal(row.current_round_cutoff_value).quantize(
                DECIMAL_FOUR_PLACES,
                rounding=ROUND_HALF_UP,
            ),
            opening_rank=int(row.opening_rank) if row.opening_rank is not None else None,
            probability_percent=Decimal(probability.bounded_probability).quantize(
                DECIMAL_FOUR_PLACES,
                rounding=ROUND_HALF_UP,
            ),
            band=band,
            evidence=ProbabilityEvidenceDTO(
                round_evidence_score=Decimal(snapshot.confidence.round_evidence_score).quantize(
                    DECIMAL_FOUR_PLACES,
                    rounding=ROUND_HALF_UP,
                ),
                round_stability_score=Decimal(snapshot.confidence.round_stability_score).quantize(
                    DECIMAL_FOUR_PLACES,
                    rounding=ROUND_HALF_UP,
                ),
                current_year_presence_score=Decimal(snapshot.confidence.current_year_presence_score).quantize(
                    DECIMAL_FOUR_PLACES,
                    rounding=ROUND_HALF_UP,
                ),
                is_cold_start=bool(snapshot.confidence.is_cold_start),
                is_projected_current_round=bool(row.is_projected_current_round),
            ),
            comparison=ComparisonContextDTO(
                metric_type=snapshot.margin.metric_type,
                user_score=Decimal(snapshot.margin.user_score).quantize(
                    DECIMAL_FOUR_PLACES,
                    rounding=ROUND_HALF_UP,
                ),
                current_round_cutoff_value=Decimal(snapshot.margin.current_round_cutoff_value).quantize(
                    DECIMAL_FOUR_PLACES,
                    rounding=ROUND_HALF_UP,
                ),
                margin_value=Decimal(snapshot.margin.raw_margin).quantize(
                    DECIMAL_FOUR_PLACES,
                    rounding=ROUND_HALF_UP,
                ),
                qualified_against_current_anchor=bool(
                    snapshot.margin.qualified_against_current_anchor
                ),
            ),
            latest_year_available=row.latest_year_available,
            latest_round_available=row.latest_round_available,
            comparison_year=row.comparison_year,
            comparison_round_number=row.comparison_round_number,
            live_round_number=row.live_round_number,
        )