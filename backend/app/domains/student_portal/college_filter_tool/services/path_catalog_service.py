from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from sqlalchemy.orm import Session

from app.models import ExamPathCatalog
from app.domains.student_portal.college_filter_tool.schemas.runtime_search_schemas import (
    CollegeFilterPathCatalogResponse,
    MetricType,
    PathCatalogItemDTO,
)


class CollegeFilterPathCatalogService:
    """
    Produces the student-visible path catalog tree used to bootstrap the
    first college-filter selection step.

    Design rules:
    - active paths only
    - no frontend hardcoding of exams or path hierarchy
    - preserve DB-driven display ordering
    - do not infer or invent children; use parent_path_id as stored
    """

    def build_path_catalog_response(
        self,
        db: Session,
    ) -> CollegeFilterPathCatalogResponse:
        rows: List[ExamPathCatalog] = (
            db.query(ExamPathCatalog)
            .filter(ExamPathCatalog.active.is_(True))
            .order_by(
                ExamPathCatalog.display_order.asc(),
                ExamPathCatalog.visible_label.asc(),
                ExamPathCatalog.path_key.asc(),
            )
            .all()
        )

        items = [
            PathCatalogItemDTO(
                path_id=row.path_id,
                parent_path_id=row.parent_path_id,
                path_key=row.path_key,
                visible_label=row.visible_label,
                exam_family=row.exam_family,
                resolved_exam_code=row.resolved_exam_code,
                education_type=row.education_type,
                selection_type=row.selection_type,
                metric_type=MetricType(str(row.metric_type).strip().lower()),
                expected_max_rounds=int(row.expected_max_rounds),
                supports_branch=bool(row.supports_branch),
                supports_course_relaxation=bool(row.supports_course_relaxation),
                supports_location_filter=bool(row.supports_location_filter),
                supports_opening_rank=bool(row.supports_opening_rank),
                active=bool(row.active),
                display_order=int(row.display_order),
            )
            for row in rows
        ]

        return CollegeFilterPathCatalogResponse(
            items=items,
            generated_at=datetime.now(timezone.utc),
        )


college_filter_path_catalog_service = CollegeFilterPathCatalogService()