from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Iterable, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProbabilityPolicyConfig
from app.domains.student_portal.college_filter_tool.repositories.search_repository import (
    SearchRepositoryRow,
)


@dataclass(frozen=True)
class ResolvedProbabilityPolicy:
    policy_id: UUID
    policy_key: str
    path_id: UUID | None
    version_no: int
    is_active: bool

    weight_round_evidence: Decimal
    weight_round_stability: Decimal
    weight_current_year_presence: Decimal

    weight_margin: Decimal
    weight_confidence: Decimal

    probability_base: Decimal
    probability_multiplier: Decimal
    probability_min: Decimal
    probability_max: Decimal

    safe_min_margin: Decimal
    safe_min_confidence: Decimal

    moderate_min_margin: Decimal
    moderate_min_confidence: Decimal

    hard_min_margin: Decimal
    hard_min_confidence: Decimal

    suggested_min_margin: Decimal
    suggested_min_confidence: Decimal
    suggested_score_penalty: Decimal
    suggested_probability_penalty: Decimal

    cold_start_probability_cap: Decimal
    cold_start_safe_min_margin: Decimal
    cold_start_safe_min_confidence: Decimal

    notes: str | None


class PolicyResolutionService:
    """
    Resolves row-level active policy references into strongly typed immutable policy objects.

    Resolution order:
    1. row.active_policy_id
    2. active default policy (path_id IS NULL, is_active = true)

    No invented constants are allowed when the DB already provides policy parameters.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._default_policy_cache: ResolvedProbabilityPolicy | None = None

    async def resolve_for_row(self, row: SearchRepositoryRow) -> ResolvedProbabilityPolicy:
        if row.active_policy_id:
            policy = await self._load_active_policy_by_id(row.active_policy_id)
            if policy:
                return policy

        default_policy = await self._load_default_active_policy()
        if default_policy:
            return default_policy

        raise HTTPException(
            status_code=500,
            detail="No active probability policy could be resolved for runtime scoring.",
        )

    async def resolve_map_for_rows(
        self,
        rows: Iterable[SearchRepositoryRow],
    ) -> Dict[UUID, ResolvedProbabilityPolicy]:
        """
        Batch-friendly resolution keyed by SearchReadModel row id.
        """
        rows = list(rows)
        if not rows:
            return {}

        requested_policy_ids = {
            row.active_policy_id
            for row in rows
            if row.active_policy_id is not None
        }

        policies_by_id: Dict[UUID, ResolvedProbabilityPolicy] = {}
        if requested_policy_ids:
            stmt = (
                select(ProbabilityPolicyConfig)
                .where(
                    ProbabilityPolicyConfig.policy_id.in_(list(requested_policy_ids)),
                    ProbabilityPolicyConfig.is_active.is_(True),
                )
            )
            result = await self.db.execute(stmt)
            db_rows = result.scalars().all()
            policies_by_id = {
                policy.policy_id: self._map_policy(policy)
                for policy in db_rows
            }

        default_policy = await self._load_default_active_policy()

        resolved: Dict[UUID, ResolvedProbabilityPolicy] = {}
        for row in rows:
            if row.active_policy_id and row.active_policy_id in policies_by_id:
                resolved[row.id] = policies_by_id[row.active_policy_id]
            elif default_policy is not None:
                resolved[row.id] = default_policy
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"No active probability policy available for search row {row.id}",
                )

        return resolved

    async def _load_active_policy_by_id(
        self,
        policy_id: UUID,
    ) -> Optional[ResolvedProbabilityPolicy]:
        stmt = (
            select(ProbabilityPolicyConfig)
            .where(
                ProbabilityPolicyConfig.policy_id == policy_id,
                ProbabilityPolicyConfig.is_active.is_(True),
            )
        )
        result = await self.db.execute(stmt)
        db_row = result.scalar_one_or_none()
        return self._map_policy(db_row) if db_row else None

    async def _load_default_active_policy(self) -> Optional[ResolvedProbabilityPolicy]:
        if self._default_policy_cache is not None:
            return self._default_policy_cache

        stmt = (
            select(ProbabilityPolicyConfig)
            .where(
                ProbabilityPolicyConfig.is_active.is_(True),
                ProbabilityPolicyConfig.path_id.is_(None),
            )
            .order_by(
                ProbabilityPolicyConfig.version_no.desc(),
                ProbabilityPolicyConfig.created_at.desc(),
            )
            .limit(1)
        )

        result = await self.db.execute(stmt)
        db_row = result.scalar_one_or_none()

        if db_row is None:
            return None

        self._default_policy_cache = self._map_policy(db_row)
        return self._default_policy_cache

    @staticmethod
    def _map_policy(db_row: ProbabilityPolicyConfig) -> ResolvedProbabilityPolicy:
        return ResolvedProbabilityPolicy(
            policy_id=db_row.policy_id,
            policy_key=db_row.policy_key,
            path_id=db_row.path_id,
            version_no=int(db_row.version_no),
            is_active=bool(db_row.is_active),

            weight_round_evidence=Decimal(db_row.weight_round_evidence),
            weight_round_stability=Decimal(db_row.weight_round_stability),
            weight_current_year_presence=Decimal(db_row.weight_current_year_presence),

            weight_margin=Decimal(db_row.weight_margin),
            weight_confidence=Decimal(db_row.weight_confidence),

            probability_base=Decimal(db_row.probability_base),
            probability_multiplier=Decimal(db_row.probability_multiplier),
            probability_min=Decimal(db_row.probability_min),
            probability_max=Decimal(db_row.probability_max),

            safe_min_margin=Decimal(db_row.safe_min_margin),
            safe_min_confidence=Decimal(db_row.safe_min_confidence),

            moderate_min_margin=Decimal(db_row.moderate_min_margin),
            moderate_min_confidence=Decimal(db_row.moderate_min_confidence),

            hard_min_margin=Decimal(db_row.hard_min_margin),
            hard_min_confidence=Decimal(db_row.hard_min_confidence),

            suggested_min_margin=Decimal(db_row.suggested_min_margin),
            suggested_min_confidence=Decimal(db_row.suggested_min_confidence),
            suggested_score_penalty=Decimal(db_row.suggested_score_penalty),
            suggested_probability_penalty=Decimal(db_row.suggested_probability_penalty),

            cold_start_probability_cap=Decimal(db_row.cold_start_probability_cap),
            cold_start_safe_min_margin=Decimal(db_row.cold_start_safe_min_margin),
            cold_start_safe_min_confidence=Decimal(db_row.cold_start_safe_min_confidence),

            notes=db_row.notes,
        )