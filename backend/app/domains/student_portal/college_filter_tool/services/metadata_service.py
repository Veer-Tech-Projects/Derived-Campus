from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import (
    ExamPathOptionMap,
    ExamProgramServingMap,
    ExamSeatFilterServingMap,
    SearchReadModel,
)
from app.domains.student_portal.college_filter_tool.schemas.runtime_search_schemas import (
    CollegeFilterMetadataResponse,
    FilterDependencyDTO,
    FilterOptionDTO,
    FilterSchemaDTO,
    PathSummaryDTO,
)
from app.domains.student_portal.college_filter_tool.services.path_validation_service import (
    PathValidationService,
    ResolvedPathContext,
    ResolvedFilterSchema,
)


class CollegeFilterMetadataService:
    """
    Produces path-aware metadata for dynamic student UI rendering.

    Data source precedence:
    - PATH_OPTION  -> exam_path_option_map
    - SERVING_MAP  -> exam_seat_filter_serving_map
    - BRANCH       -> exam_program_serving_map (graceful empty fallback)
    - LOCATION     -> search metadata placeholder for now (no separate table yet in Step 7B)
    - STATIC       -> no dynamic options emitted here
    """

    def build_metadata_response(
        self,
        db: Session,
        path_id: UUID,
    ) -> CollegeFilterMetadataResponse:
        ctx = PathValidationService.get_path_only(db=db, path_id=path_id)

        filters = []
        for filter_schema in ctx.active_filters:
            options = self._resolve_options_for_filter(
                db=db,
                path_context=ctx,
                filter_schema=filter_schema,
            )

            filters.append(
                FilterSchemaDTO(
                    filter_key=filter_schema.filter_key,
                    filter_label=filter_schema.filter_label,
                    control_type=filter_schema.control_type,
                    option_source=filter_schema.option_source,
                    is_required=filter_schema.is_required,
                    is_visible=filter_schema.is_visible,
                    is_auto_fillable=filter_schema.is_auto_fillable,
                    sort_order=filter_schema.sort_order,
                    dependency=FilterDependencyDTO(
                        depends_on_filter_key=filter_schema.depends_on_filter_key
                    ),
                    options=options,
                )
            )

        return CollegeFilterMetadataResponse(
            path=PathSummaryDTO(
                path_id=ctx.path_id,
                path_key=ctx.path_key,
                visible_label=ctx.visible_label,
                exam_family=ctx.exam_family,
                resolved_exam_code=ctx.resolved_exam_code,
                education_type=ctx.education_type,
                selection_type=ctx.selection_type,
                metric_type=ctx.metric_type,
                expected_max_rounds=ctx.expected_max_rounds,
                supports_branch=ctx.supports_branch,
                supports_course_relaxation=ctx.supports_course_relaxation,
                supports_location_filter=ctx.supports_location_filter,
                supports_opening_rank=ctx.supports_opening_rank,
            ),
            filters=filters,
            generated_at=datetime.now(timezone.utc),
        )

    def _resolve_options_for_filter(
        self,
        db: Session,
        path_context: ResolvedPathContext,
        filter_schema: ResolvedFilterSchema,
    ) -> List[FilterOptionDTO]:
        option_source = filter_schema.option_source
        filter_key = filter_schema.filter_key

        if option_source == "PATH_OPTION":
            return self._load_path_option_values(db=db, path_id=path_context.path_id)

        if option_source == "SERVING_MAP":
            return self._load_serving_map_values(
                db=db,
                path_id=path_context.path_id,
                filter_key=filter_key,
            )

        if option_source == "BRANCH":
            if filter_key == "branch":
                return self._load_branch_discipline_values(
                    db=db,
                    path_id=path_context.path_id,
                )

            if filter_key == "variant":
                return self._load_branch_specialization_values(
                    db=db,
                    path_id=path_context.path_id,
                )

            return self._load_branch_values_legacy(
                db=db,
                path_id=path_context.path_id,
            )

        if option_source == "LOCATION":
            return self._load_location_placeholder_values(
                db=db,
                path_id=path_context.path_id,
                filter_key=filter_key,
            )

        if option_source == "STATIC":
            return []

        return []

    def _load_path_option_values(
        self,
        db: Session,
        path_id: UUID,
    ) -> List[FilterOptionDTO]:
        rows = (
            db.query(ExamPathOptionMap)
            .filter(
                ExamPathOptionMap.path_id == path_id,
                ExamPathOptionMap.active == True,  # noqa: E712
            )
            .order_by(
                ExamPathOptionMap.option_label.asc(),
                ExamPathOptionMap.course_type_value.asc(),
                ExamPathOptionMap.exam_code.asc(),
            )
            .all()
        )

        seen = set()
        options: List[FilterOptionDTO] = []

        for row in rows:
            value = (row.course_type_value or row.exam_code or "").strip()
            label = (row.option_label or row.course_type_value or row.exam_code or "").strip()
            if not value or not label:
                continue

            key = (value.lower(), label.lower())
            if key in seen:
                continue
            seen.add(key)

            options.append(
                FilterOptionDTO(
                    value=value,
                    label=label,
                    metadata={
                        "exam_code": row.exam_code,
                        "course_type_value": row.course_type_value,
                    },
                )
            )

        return options

    def _load_serving_map_values(
        self,
        db: Session,
        path_id: UUID,
        filter_key: str,
    ) -> List[FilterOptionDTO]:
        rows = (
            db.query(ExamSeatFilterServingMap)
            .filter(
                ExamSeatFilterServingMap.path_id == path_id,
                ExamSeatFilterServingMap.filter_key == filter_key,
                ExamSeatFilterServingMap.active == True,  # noqa: E712
            )
            .order_by(
                ExamSeatFilterServingMap.option_label.asc(),
                ExamSeatFilterServingMap.option_key.asc(),
            )
            .all()
        )

        seen = set()
        options: List[FilterOptionDTO] = []

        for row in rows:
            value = (row.option_key or "").strip()
            label = (row.option_label or "").strip()
            if not value or not label:
                continue

            dedup_key = value.lower()
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            options.append(
                FilterOptionDTO(
                    value=value,
                    label=label,
                    metadata={
                        "category_name": row.category_name,
                        "is_reserved": row.is_reserved,
                        "course_type": row.course_type,
                        "location_type": row.location_type,
                        "reservation_type": row.reservation_type,
                        "seat_bucket_code": row.seat_bucket_code,
                        "display_meta": row.display_meta or {},
                    },
                )
            )

        return options

    def _load_branch_discipline_values(
        self,
        db: Session,
        path_id: UUID,
    ) -> List[FilterOptionDTO]:
        rows = (
            db.query(ExamProgramServingMap)
            .filter(ExamProgramServingMap.path_id == path_id)
            .order_by(
                ExamProgramServingMap.branch_discipline_label.asc(),
                ExamProgramServingMap.branch_discipline_key.asc(),
                ExamProgramServingMap.program_code.asc(),
            )
            .all()
        )

        if not rows:
            return []

        seen = set()
        options: List[FilterOptionDTO] = []

        for row in rows:
            value = (row.branch_discipline_key or "").strip()
            label = (
                row.branch_discipline_label
                or row.branch_label
                or row.program_name
                or value
            )
            label = label.strip() if label else ""

            if not value or not label:
                continue

            dedup_key = value.lower()
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            options.append(
                FilterOptionDTO(
                    value=value,
                    label=label,
                    metadata={
                        "has_specialization_dimension": bool(
                            row.has_specialization_dimension
                        ),
                    },
                )
            )

        return options

    def _load_branch_specialization_values(
        self,
        db: Session,
        path_id: UUID,
    ) -> List[FilterOptionDTO]:
        rows = (
            db.query(ExamProgramServingMap)
            .filter(
                ExamProgramServingMap.path_id == path_id,
                ExamProgramServingMap.specialization_key.isnot(None),
                ExamProgramServingMap.specialization_label.isnot(None),
            )
            .order_by(
                ExamProgramServingMap.specialization_label.asc(),
                ExamProgramServingMap.specialization_key.asc(),
                ExamProgramServingMap.program_code.asc(),
            )
            .all()
        )

        if not rows:
            return []

        seen = set()
        options: List[FilterOptionDTO] = []

        for row in rows:
            value = (row.specialization_key or "").strip()
            label = (row.specialization_label or "").strip()

            if not value or not label:
                continue

            dedup_key = value.lower()
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            options.append(
                FilterOptionDTO(
                    value=value,
                    label=label,
                    metadata={
                        "branch_discipline_key": row.branch_discipline_key,
                        "branch_discipline_label": row.branch_discipline_label,
                    },
                )
            )

        return options

    def _load_branch_values_legacy(
        self,
        db: Session,
        path_id: UUID,
    ) -> List[FilterOptionDTO]:
        rows = (
            db.query(ExamProgramServingMap)
            .filter(ExamProgramServingMap.path_id == path_id)
            .order_by(
                ExamProgramServingMap.branch_label.asc(),
                ExamProgramServingMap.branch_option_key.asc(),
                ExamProgramServingMap.program_code.asc(),
            )
            .all()
        )

        if not rows:
            return []

        seen = set()
        options: List[FilterOptionDTO] = []

        for row in rows:
            value = (row.branch_option_key or "").strip()
            label = (row.branch_label or row.program_name or value).strip()
            if not value or not label:
                continue

            dedup_key = value.lower()
            if dedup_key in seen:
                continue
            seen.add(dedup_key)

            options.append(
                FilterOptionDTO(
                    value=value,
                    label=label,
                    metadata={
                        "program_code": row.program_code,
                        "program_name": row.program_name,
                        "mapping_confidence": str(row.mapping_confidence) if row.mapping_confidence is not None else None,
                        "mapping_status": (
                            row.mapping_status.value
                            if hasattr(row.mapping_status, "value")
                            else str(row.mapping_status)
                        ),
                    },
                )
            )

        return options

    def _load_location_placeholder_values(
        self,
        db: Session,
        path_id: UUID,
        filter_key: str,
    ) -> List[FilterOptionDTO]:
        """
        LOCATION options are sourced dynamically from search_read_model using the
        resolved final path's exam_code.

        Rules:
        - state_code: distinct non-null state codes
        - district: distinct non-null district values, carrying state_code and pincode metadata
        - pincode: no preloaded dropdown options; frontend uses typed input and reverse autofill
        from district metadata or direct pincode entry
        """
        ctx = PathValidationService.get_path_only(db=db, path_id=path_id)
        exam_code = (ctx.resolved_exam_code or "").strip()

        if not exam_code:
            return []

        if filter_key == "state_code":
            rows = (
                db.query(SearchReadModel.state_code)
                .filter(
                    SearchReadModel.exam_code == exam_code,
                    SearchReadModel.state_code.isnot(None),
                )
                .distinct()
                .order_by(SearchReadModel.state_code.asc())
                .all()
            )

            options: List[FilterOptionDTO] = []
            for (state_code,) in rows:
                value = (state_code or "").strip()
                if not value:
                    continue

                options.append(
                    FilterOptionDTO(
                        value=value,
                        label=value,
                        metadata={
                            "state_code": value,
                        },
                    )
                )

            return options

        if filter_key == "district":
            rows = (
                db.query(
                    SearchReadModel.district,
                    SearchReadModel.state_code,
                    SearchReadModel.pincode,
                )
                .filter(
                    SearchReadModel.exam_code == exam_code,
                    SearchReadModel.district.isnot(None),
                    SearchReadModel.state_code.isnot(None),
                )
                .distinct()
                .order_by(
                    SearchReadModel.state_code.asc(),
                    SearchReadModel.district.asc(),
                    SearchReadModel.pincode.asc(),
                )
                .all()
            )

            seen = set()
            options: List[FilterOptionDTO] = []

            for district, state_code, pincode in rows:
                district_value = (district or "").strip()
                state_value = (state_code or "").strip()
                pincode_value = (pincode or "").strip()

                if not district_value or not state_value:
                    continue

                dedup_key = (district_value.lower(), state_value.lower(), pincode_value)
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)

                options.append(
                    FilterOptionDTO(
                        value=district_value,
                        label=district_value,
                        metadata={
                            "state_code": state_value,
                            "pincode": pincode_value,
                        },
                    )
                )

            return options

        if filter_key == "pincode":
            return []

        return []


college_filter_metadata_service = CollegeFilterMetadataService()