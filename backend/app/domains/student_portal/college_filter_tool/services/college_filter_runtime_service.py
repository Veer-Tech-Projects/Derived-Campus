from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import List

from sqlalchemy.orm import Session

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
    MetricComparisonService,
)
from app.domains.student_portal.college_filter_tool.services.path_validation_service import (
    PathValidationService,
    ResolvedPathContext,
)
from app.domains.student_portal.college_filter_tool.services.policy_resolution_service import (
    PolicyResolutionService,
)
from app.domains.student_portal.college_filter_tool.services.probability_engine import (
    ProbabilityEngine,
)


DECIMAL_FOUR_PLACES = Decimal("0.0001")


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

    def __init__(self, db: Session):
        self.db = db
        self.repository = SearchRepository(db)
        self.policy_resolution_service = PolicyResolutionService(db)
        self.metric_comparison_service = MetricComparisonService()
        self.probability_engine = ProbabilityEngine()
        self.band_classifier = BandClassifier()
        self.best_fit_sort_service = BestFitSortService()
        self.band_pagination_service = BandPaginationService()

    def search(
        self,
        *,
        request: CollegeFilterSearchRequest,
    ) -> CollegeFilterSearchResponse:
        path_context = PathValidationService.resolve_and_validate(
            db=self.db,
            request=request,
        )

        # --------------------------------------------------
        # 1. Primary candidate set
        # --------------------------------------------------
        primary_result = self.repository.search_primary(
            path_context=path_context,
        )

        primary_ranked_candidates = self._score_primary_rows(
            path_context=path_context,
            rows=primary_result.rows,
        )

        # --------------------------------------------------
        # 2. Suggested candidate set
        # --------------------------------------------------
        primary_identity_set = {
            (candidate.row.college_id, candidate.row.program_code, candidate.row.seat_bucket_code)
            for candidate in primary_ranked_candidates
        }

        suggested_result = self.repository.search_suggested_candidates(
            path_context=path_context,
            exclude_identities=primary_identity_set,
        )

        suggested_ranked_candidates = self._score_suggested_rows(
            path_context=path_context,
            rows=suggested_result.rows,
        )

        # --------------------------------------------------
        # 3. Sort by band / suggestion logic
        # --------------------------------------------------
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

        # --------------------------------------------------
        # 4. Apply cap + page slicing
        # --------------------------------------------------
        paginated = self.band_pagination_service.paginate_all_bands(
            safe_candidates=safe_sorted,
            moderate_candidates=moderate_sorted,
            hard_candidates=hard_sorted,
            suggested_candidates=suggested_sorted,
            page_request=request.page_by_band,
            page_size=request.page_size,
        )

        # --------------------------------------------------
        # 5. Aggregate counts
        # --------------------------------------------------
        band_counts = BandCountsDTO(
            safe=len(safe_sorted),
            moderate=len(moderate_sorted),
            hard=len(hard_sorted),
            suggested=paginated[CollegeBand.SUGGESTED].capped_total_available,
        )

        total_matching_count = (
            band_counts.safe
            + band_counts.moderate
            + band_counts.hard
        )

        # --------------------------------------------------
        # 6. DTO mapping
        # --------------------------------------------------
        return CollegeFilterSearchResponse(
            path=self._build_path_summary(path_context),
            user_score=request.score.quantize(DECIMAL_FOUR_PLACES, rounding=ROUND_HALF_UP),
            total_matching_count=total_matching_count,
            band_counts=band_counts,
            bands=SearchBandsDTO(
                safe=self._map_paginated_band_slice(
                    band=CollegeBand.SAFE,
                    paginated_slice=paginated[CollegeBand.SAFE],
                ),
                moderate=self._map_paginated_band_slice(
                    band=CollegeBand.MODERATE,
                    paginated_slice=paginated[CollegeBand.MODERATE],
                ),
                hard=self._map_paginated_band_slice(
                    band=CollegeBand.HARD,
                    paginated_slice=paginated[CollegeBand.HARD],
                ),
                suggested=self._map_paginated_band_slice(
                    band=CollegeBand.SUGGESTED,
                    paginated_slice=paginated[CollegeBand.SUGGESTED],
                ),
            ),
            generated_at=datetime.now(timezone.utc),
        )

    # ======================================================
    # PRIMARY / SUGGESTED SCORING
    # ======================================================

    def _score_primary_rows(
        self,
        *,
        path_context: ResolvedPathContext,
        rows: List[SearchRepositoryRow],
    ) -> List[RankedCandidate]:
        if not rows:
            return []

        policies_by_row_id = self.policy_resolution_service.resolve_map_for_rows(rows)

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

    def _score_suggested_rows(
        self,
        *,
        path_context: ResolvedPathContext,
        rows: List[SearchRepositoryRow],
    ) -> List[RankedCandidate]:
        if not rows:
            return []

        policies_by_row_id = self.policy_resolution_service.resolve_map_for_rows(rows)

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

    def _map_paginated_band_slice(
        self,
        *,
        band: CollegeBand,
        paginated_slice: PaginatedBandSlice,
    ) -> BandResultDTO:
        return BandResultDTO(
            band=band,
            items=[
                self._map_ranked_candidate_to_card(
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

    def _map_ranked_candidate_to_card(
        self,
        *,
        band: CollegeBand,
        candidate: RankedCandidate,
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