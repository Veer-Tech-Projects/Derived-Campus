from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Set
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import ExamPathCatalog, ExamPathFilterSchema
from app.domains.student_portal.college_filter_tool.schemas.runtime_search_schemas import (
    CollegeFilterSearchRequest,
    MetricType,
)


@dataclass(frozen=True)
class ResolvedFilterSchema:
    filter_key: str
    filter_label: str
    control_type: str
    option_source: str
    is_required: bool
    is_visible: bool
    is_auto_fillable: bool
    sort_order: int
    depends_on_filter_key: str | None


@dataclass(frozen=True)
class ResolvedPathContext:
    path_id: UUID
    path_key: str
    visible_label: str
    exam_family: str
    resolved_exam_code: str | None
    education_type: str | None
    selection_type: str | None
    metric_type: MetricType
    expected_max_rounds: int
    supports_branch: bool
    supports_course_relaxation: bool
    supports_location_filter: bool
    supports_opening_rank: bool
    active_filters: List[ResolvedFilterSchema]
    normalized_filters: Dict[str, Any]
    user_score: Decimal


class PathValidationService:
    """
    Validates runtime request payloads strictly against path metadata.

    Enterprise contract:
    - no global hardcoding of required filters
    - no acceptance of unknown filter keys
    - metric validation is path-aware
    - dependency validation is schema-driven
    """

    @staticmethod
    def resolve_and_validate(
        db: Session,
        request: CollegeFilterSearchRequest,
    ) -> ResolvedPathContext:
        path = (
            db.query(ExamPathCatalog)
            .filter(
                ExamPathCatalog.path_id == request.path_id,
                ExamPathCatalog.active == True,  # noqa: E712
            )
            .first()
        )
        if not path:
            raise HTTPException(status_code=404, detail="Active exam path not found")

        filter_rows = (
            db.query(ExamPathFilterSchema)
            .filter(ExamPathFilterSchema.path_id == request.path_id)
            .order_by(ExamPathFilterSchema.sort_order.asc(), ExamPathFilterSchema.filter_key.asc())
            .all()
        )

        if not filter_rows:
            raise HTTPException(
                status_code=500,
                detail=f"No filter schema configured for path_id={request.path_id}",
            )

        metric_type = PathValidationService._coerce_metric_type(path.metric_type)
        normalized_filters = PathValidationService._normalize_filters(request.filters)
        allowed_keys = {row.filter_key for row in filter_rows}

        PathValidationService._reject_unknown_filters(normalized_filters, allowed_keys)
        PathValidationService._validate_required_filters(
            request,
            normalized_filters,
            filter_rows,
        )
        PathValidationService._validate_dependencies(normalized_filters, filter_rows)
        PathValidationService._validate_score(metric_type, request.score)

        active_filters = [
            ResolvedFilterSchema(
                filter_key=row.filter_key,
                filter_label=row.filter_label,
                control_type=str(row.control_type.value if hasattr(row.control_type, "value") else row.control_type),
                option_source=str(row.option_source.value if hasattr(row.option_source, "value") else row.option_source),
                is_required=bool(row.is_required),
                is_visible=bool(row.is_visible),
                is_auto_fillable=bool(row.is_auto_fillable),
                sort_order=int(row.sort_order),
                depends_on_filter_key=row.depends_on_filter_key,
            )
            for row in filter_rows
        ]

        return ResolvedPathContext(
            path_id=path.path_id,
            path_key=path.path_key,
            visible_label=path.visible_label,
            exam_family=path.exam_family,
            resolved_exam_code=path.resolved_exam_code,
            education_type=path.education_type,
            selection_type=path.selection_type,
            metric_type=metric_type,
            expected_max_rounds=path.expected_max_rounds,
            supports_branch=bool(path.supports_branch),
            supports_course_relaxation=bool(path.supports_course_relaxation),
            supports_location_filter=bool(path.supports_location_filter),
            supports_opening_rank=bool(path.supports_opening_rank),
            active_filters=active_filters,
            normalized_filters=normalized_filters,
            user_score=request.score,
        )

    @staticmethod
    def get_path_only(db: Session, path_id: UUID) -> ResolvedPathContext:
        """
        Metadata-only variant used by GET /metadata/{path_id}.
        No runtime request body required.
        """
        dummy_request = CollegeFilterSearchRequest(
            path_id=path_id,
            score=Decimal("1"),
            filters={},
        )
        path = (
            db.query(ExamPathCatalog)
            .filter(
                ExamPathCatalog.path_id == path_id,
                ExamPathCatalog.active == True,  # noqa: E712
            )
            .first()
        )
        if not path:
            raise HTTPException(status_code=404, detail="Active exam path not found")

        filter_rows = (
            db.query(ExamPathFilterSchema)
            .filter(ExamPathFilterSchema.path_id == path_id)
            .order_by(ExamPathFilterSchema.sort_order.asc(), ExamPathFilterSchema.filter_key.asc())
            .all()
        )
        if not filter_rows:
            raise HTTPException(
                status_code=500,
                detail=f"No filter schema configured for path_id={path_id}",
            )

        metric_type = PathValidationService._coerce_metric_type(path.metric_type)
        active_filters = [
            ResolvedFilterSchema(
                filter_key=row.filter_key,
                filter_label=row.filter_label,
                control_type=str(row.control_type.value if hasattr(row.control_type, "value") else row.control_type),
                option_source=str(row.option_source.value if hasattr(row.option_source, "value") else row.option_source),
                is_required=bool(row.is_required),
                is_visible=bool(row.is_visible),
                is_auto_fillable=bool(row.is_auto_fillable),
                sort_order=int(row.sort_order),
                depends_on_filter_key=row.depends_on_filter_key,
            )
            for row in filter_rows
        ]

        return ResolvedPathContext(
            path_id=path.path_id,
            path_key=path.path_key,
            visible_label=path.visible_label,
            exam_family=path.exam_family,
            resolved_exam_code=path.resolved_exam_code,
            education_type=path.education_type,
            selection_type=path.selection_type,
            metric_type=metric_type,
            expected_max_rounds=path.expected_max_rounds,
            supports_branch=bool(path.supports_branch),
            supports_course_relaxation=bool(path.supports_course_relaxation),
            supports_location_filter=bool(path.supports_location_filter),
            supports_opening_rank=bool(path.supports_opening_rank),
            active_filters=active_filters,
            normalized_filters={},
            user_score=dummy_request.score,
        )

    @staticmethod
    def _coerce_metric_type(raw_metric_type: str) -> MetricType:
        normalized = str(raw_metric_type).strip().lower()
        if normalized == MetricType.RANK.value:
            return MetricType.RANK
        if normalized == MetricType.PERCENTILE.value:
            return MetricType.PERCENTILE
        raise HTTPException(
            status_code=500,
            detail=f"Unsupported metric_type configured on path: {raw_metric_type}",
        )

    @staticmethod
    def _normalize_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {}
        for raw_key, raw_value in (filters or {}).items():
            key = str(raw_key).strip()
            if not key:
                continue

            if raw_value is None:
                continue

            if isinstance(raw_value, str):
                cleaned = raw_value.strip()
                if cleaned == "":
                    continue
                normalized[key] = cleaned
            else:
                normalized[key] = raw_value

        return normalized

    @staticmethod
    def _reject_unknown_filters(normalized_filters: Dict[str, Any], allowed_keys: Set[str]) -> None:
        unknown = sorted(set(normalized_filters.keys()) - allowed_keys)
        if unknown:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Request contains unsupported filters for the selected path",
                    "unsupported_filters": unknown,
                },
            )

    @staticmethod
    def _validate_required_filters(
        request: CollegeFilterSearchRequest,
        normalized_filters: Dict[str, Any],
        filter_rows: List[ExamPathFilterSchema],
    ) -> None:
        missing_required = []

        for row in filter_rows:
            if not bool(row.is_required):
                continue

            # score is a top-level request field, not part of request.filters
            if row.filter_key == "score":
                if request.score is None:
                    missing_required.append("score")
                continue

            if row.filter_key not in normalized_filters:
                missing_required.append(row.filter_key)

        if missing_required:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Missing required filters for selected path",
                    "missing_required_filters": missing_required,
                },
            )

    @staticmethod
    def _validate_dependencies(
        normalized_filters: Dict[str, Any],
        filter_rows: List[ExamPathFilterSchema],
    ) -> None:
        violations: List[Dict[str, str]] = []
        for row in filter_rows:
            child_key = row.filter_key
            parent_key = row.depends_on_filter_key

            if child_key in normalized_filters and parent_key and parent_key not in normalized_filters:
                violations.append(
                    {
                        "filter_key": child_key,
                        "depends_on_filter_key": parent_key,
                    }
                )

        if violations:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Dependent filters are missing their parent filter values",
                    "dependency_violations": violations,
                },
            )

    @staticmethod
    def _validate_score(metric_type: MetricType, score: Decimal) -> None:
        if score <= 0:
            raise HTTPException(status_code=400, detail="score must be greater than 0")

        if metric_type == MetricType.RANK:
            if score != score.to_integral_value():
                raise HTTPException(
                    status_code=400,
                    detail="Rank-based paths require an integer-like score",
                )

        if metric_type == MetricType.PERCENTILE:
            if score > Decimal("100"):
                raise HTTPException(
                    status_code=400,
                    detail="Percentile-based paths require score <= 100",
                )