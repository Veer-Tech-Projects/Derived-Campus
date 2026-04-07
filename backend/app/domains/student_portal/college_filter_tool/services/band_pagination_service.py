from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from typing import Dict, Iterable, List

from app.domains.student_portal.college_filter_tool.schemas.runtime_search_schemas import (
    BandPageRequest,
    CollegeBand,
)
from app.domains.student_portal.college_filter_tool.services.best_fit_sort_service import (
    RankedCandidate,
)


PRIMARY_BAND_CAP = 200
SUGGESTED_BAND_CAP = 10


@dataclass(frozen=True)
class PaginatedBandSlice:
    band: CollegeBand
    all_matching_count: int
    capped_total_available: int
    cap_reached: bool
    page: int
    page_size: int
    has_next_page: bool
    items: List[RankedCandidate]


class BandPaginationService:
    """
    Applies the Step 7F hard-cap and per-band page slicing rules.

    Primary bands:
    - SAFE / MODERATE / HARD: cap at 200 rows after best-fit sorting

    Suggested:
    - cap at 10 rows total
    """

    def paginate_primary_band(
        self,
        *,
        band: CollegeBand,
        sorted_candidates: Iterable[RankedCandidate],
        page: int,
        page_size: int,
    ) -> PaginatedBandSlice:
        candidates = list(sorted_candidates)
        all_matching_count = len(candidates)

        capped_candidates = candidates[:PRIMARY_BAND_CAP]
        capped_total_available = len(capped_candidates)
        cap_reached = all_matching_count > PRIMARY_BAND_CAP

        page_items, has_next_page = self._slice_page(
            items=capped_candidates,
            page=page,
            page_size=page_size,
        )

        return PaginatedBandSlice(
            band=band,
            all_matching_count=all_matching_count,
            capped_total_available=capped_total_available,
            cap_reached=cap_reached,
            page=page,
            page_size=page_size,
            has_next_page=has_next_page,
            items=page_items,
        )

    def paginate_suggested_band(
        self,
        *,
        sorted_candidates: Iterable[RankedCandidate],
        page: int,
        page_size: int,
    ) -> PaginatedBandSlice:
        candidates = list(sorted_candidates)
        all_matching_count = len(candidates)

        capped_candidates = candidates[:SUGGESTED_BAND_CAP]
        capped_total_available = len(capped_candidates)
        cap_reached = all_matching_count > SUGGESTED_BAND_CAP

        page_items, has_next_page = self._slice_page(
            items=capped_candidates,
            page=page,
            page_size=page_size,
        )

        return PaginatedBandSlice(
            band=CollegeBand.SUGGESTED,
            all_matching_count=all_matching_count,
            capped_total_available=capped_total_available,
            cap_reached=cap_reached,
            page=page,
            page_size=page_size,
            has_next_page=has_next_page,
            items=page_items,
        )

    def paginate_all_bands(
        self,
        *,
        safe_candidates: Iterable[RankedCandidate],
        moderate_candidates: Iterable[RankedCandidate],
        hard_candidates: Iterable[RankedCandidate],
        suggested_candidates: Iterable[RankedCandidate],
        page_request: BandPageRequest,
        page_size: int,
    ) -> Dict[CollegeBand, PaginatedBandSlice]:
        return {
            CollegeBand.SAFE: self.paginate_primary_band(
                band=CollegeBand.SAFE,
                sorted_candidates=safe_candidates,
                page=page_request.safe,
                page_size=page_size,
            ),
            CollegeBand.MODERATE: self.paginate_primary_band(
                band=CollegeBand.MODERATE,
                sorted_candidates=moderate_candidates,
                page=page_request.moderate,
                page_size=page_size,
            ),
            CollegeBand.HARD: self.paginate_primary_band(
                band=CollegeBand.HARD,
                sorted_candidates=hard_candidates,
                page=page_request.hard,
                page_size=page_size,
            ),
            CollegeBand.SUGGESTED: self.paginate_suggested_band(
                sorted_candidates=suggested_candidates,
                page=page_request.suggested,
                page_size=page_size,
            ),
        }

    @staticmethod
    def _slice_page(
        *,
        items: List[RankedCandidate],
        page: int,
        page_size: int,
    ) -> tuple[List[RankedCandidate], bool]:
        if page < 1:
            raise ValueError("page must be >= 1")
        if page_size < 1:
            raise ValueError("page_size must be >= 1")

        start = (page - 1) * page_size
        end = start + page_size
        page_items = items[start:end]
        has_next_page = end < len(items)

        return page_items, has_next_page