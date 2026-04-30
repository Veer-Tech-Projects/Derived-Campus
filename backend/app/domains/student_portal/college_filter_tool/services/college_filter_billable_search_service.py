from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StudentUser
from app.domains.student_portal.college_filter_tool.schemas.runtime_search_schemas import (
    CollegeFilterSearchRequest,
    CollegeFilterSearchResponse,
)
from app.domains.student_portal.college_filter_tool.services.college_filter_runtime_service import (
    CollegeFilterRuntimeService,
)
from app.domains.student_portal.college_filter_tool.services.college_filter_search_entitlement_service import (
    college_filter_search_entitlement_service,
)
from app.domains.student_portal.college_filter_tool.services.college_filter_search_fingerprint_service import (
    college_filter_search_fingerprint_service,
)
from app.domains.student_portal.student_billing.constants import (
    BILLING_CREATED_BY_COLLEGE_FILTER_SEARCH,
    COLLEGE_FILTER_SEARCH_CREDIT_COST,
)
from app.domains.student_portal.student_billing.exceptions import (
    InsufficientCreditsError,
)
from app.domains.student_portal.student_billing.services.credit_ledger_service import (
    credit_ledger_service,
)


class CollegeFilterBillableSearchService:
    """
    Authenticated, entitlement-aware outer orchestration for College Filter search.

    Design rules:
    - runtime search math stays delegated to the pure runtime service
    - active entitlement bypasses balance gate and debit
    - if no entitlement exists, wallet sufficiency is checked before search executes
    - zero-result searches remain free
    - successful billable searches consume exactly one credit
    """

    async def execute_billable_search(
        self,
        *,
        db: AsyncSession,
        student: StudentUser,
        request: CollegeFilterSearchRequest,
    ) -> CollegeFilterSearchResponse:
        score_decimal = Decimal(str(request.score).strip())

        fingerprint = college_filter_search_fingerprint_service.build_fingerprint(
            path_id=str(request.path_id),
            score=score_decimal,
            filters=request.filters,
            sort_mode=request.sort_mode,
        )
        request_snapshot = (
            college_filter_search_fingerprint_service.build_request_snapshot(
                path_id=str(request.path_id),
                score=score_decimal,
                filters=request.filters,
                sort_mode=request.sort_mode,
            )
        )

        active_entitlement = (
            await college_filter_search_entitlement_service.get_active_entitlement(
                db=db,
                student_user_id=student.id,
                fingerprint=fingerprint,
            )
        )

        if active_entitlement is None:
            await self._assert_wallet_can_cover_new_search(
                db=db,
                student_user_id=student.id,
            )
        else:
            await college_filter_search_entitlement_service.mark_entitlement_accessed(
                db=db,
                entitlement_id=active_entitlement.id,
            )

        runtime_service = CollegeFilterRuntimeService(db)
        response = await runtime_service.search(
            request=request,
        )

        if not self._has_any_results(response):
            return response

        if active_entitlement is not None:
            return response

        entitlement = await college_filter_search_entitlement_service.create_or_replace_entitlement(
            db=db,
            student_user_id=student.id,
            path_id=request.path_id,
            fingerprint=fingerprint,
            request_snapshot_json=request_snapshot,
            consumption_ledger_id=None,
        )

        _, ledger_entry = await credit_ledger_service.consume_search_credit(
            db=db,
            student_user_id=student.id,
            entitlement_id=entitlement.id,
            credit_cost=COLLEGE_FILTER_SEARCH_CREDIT_COST,
            idempotency_key=self._build_search_debit_idempotency_key(
                student_user_id=student.id,
                fingerprint=fingerprint,
            ),
            metadata_json={
                "path_id": str(request.path_id),
                "search_fingerprint": fingerprint,
                "score": request_snapshot["score"],
                "filters": request_snapshot["filters"],
                "sort_mode": request_snapshot["sort_mode"],
                "total_matching_count": response.total_matching_count,
                "band_counts": {
                    "safe": response.band_counts.safe,
                    "moderate": response.band_counts.moderate,
                    "hard": response.band_counts.hard,
                    "suggested": response.band_counts.suggested,
                },
            },
            created_by=BILLING_CREATED_BY_COLLEGE_FILTER_SEARCH,
        )

        await college_filter_search_entitlement_service.create_or_replace_entitlement(
            db=db,
            student_user_id=student.id,
            path_id=request.path_id,
            fingerprint=fingerprint,
            request_snapshot_json=request_snapshot,
            consumption_ledger_id=ledger_entry.id,
        )

        await db.commit()
        return response

    async def _assert_wallet_can_cover_new_search(
        self,
        *,
        db: AsyncSession,
        student_user_id: UUID,
    ) -> None:
        wallet = await credit_ledger_service.get_wallet_snapshot(
            db=db,
            student_user_id=student_user_id,
        )

        available_credits = wallet.available_credits if wallet is not None else 0

        if available_credits < COLLEGE_FILTER_SEARCH_CREDIT_COST:
            raise InsufficientCreditsError(
                "Insufficient credits for College Filter search.",
                available_credits=available_credits,
                required_credits=COLLEGE_FILTER_SEARCH_CREDIT_COST,
            )

    @staticmethod
    def _has_any_results(response: CollegeFilterSearchResponse) -> bool:
        return any(
            [
                response.band_counts.safe > 0,
                response.band_counts.moderate > 0,
                response.band_counts.hard > 0,
                response.band_counts.suggested > 0,
            ]
        )

    @staticmethod
    def _build_search_debit_idempotency_key(
        *,
        student_user_id: UUID,
        fingerprint: str,
    ) -> str:
        return f"SEARCH_CONSUME:{student_user_id}:{fingerprint}"


college_filter_billable_search_service = CollegeFilterBillableSearchService()