import logging
import os
from collections import defaultdict
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models import (
    College,
    CollegeLocation,
    CollegeMedia,
    CutoffOutcome,
    ExamPathCatalog,
    ExamProgramServingMap,
    MappingStatusEnum,
    MediaStatusEnum,
    MediaTypeEnum,
    ProbabilityPolicyConfig,
    RoundProjectionStats,
    SearchBuildStatusEnum,
    SearchReadModel,
    SearchReadModelBuild,
    SeatBucketTaxonomy,
)

logger = logging.getLogger(__name__)


class SearchReadModelBuilder:
    """
    Step 6: Offline CQRS Read Model Builder.

    Guarantees:
    - build-scoped materialization with SearchReadModelBuild lineage
    - per-path live round derivation
    - exact college/program/seat-bucket row identity
    - Option A: offline current-round projection when live round is ahead of latest actual
    - Option X: new-year R1 uses latest historical same-round anchor without marking projected
    - deterministic one-hero-media-per-college
    - no ORM queries inside the row loop
    """

    def __init__(self, db: Session):
        self.db = db

    def build_for_scope(
        self,
        *,
        trigger_reason: str,
        trigger_exam_code: str | None,
        policy_id: Any | None,
        created_by: str | None,
    ) -> dict:
        build = SearchReadModelBuild(
            status=SearchBuildStatusEnum.RUNNING,
            trigger_reason=trigger_reason,
            trigger_exam_code=trigger_exam_code,
            policy_id=policy_id,
            created_by=created_by,
        )
        self.db.add(build)
        self.db.commit()
        self.db.refresh(build)

        try:
            result = self._execute_build(
                build_id=build.build_id,
                trigger_exam_code=trigger_exam_code,
                policy_id=policy_id,
            )

            build = self.db.get(SearchReadModelBuild, build.build_id)
            build.status = SearchBuildStatusEnum.COMPLETED
            build.completed_at = func.now()
            build.rows_written = result["rows_written"]
            build.source_latest_ingestion_run_id = result["source_latest_ingestion_run_id"]
            build.source_watermark_year = result["source_watermark_year"]
            build.source_watermark_round = result["source_watermark_round"]

            self.db.commit()

            return {
                "build_id": str(build.build_id),
                "rows_written": result["rows_written"],
                "status": "COMPLETED",
            }

        except Exception as exc:
            self.db.rollback()
            logger.exception("SearchReadModelBuilder FAILED")

            failed_build = self.db.get(SearchReadModelBuild, build.build_id)
            if failed_build:
                failed_build.status = SearchBuildStatusEnum.FAILED
                failed_build.completed_at = func.now()
                failed_build.error_message = str(exc)[:4000]
                self.db.commit()

            raise

    def _execute_build(
        self,
        *,
        build_id: Any,
        trigger_exam_code: str | None,
        policy_id: Any | None,
    ) -> dict:
        active_paths = (
            self.db.query(ExamPathCatalog)
            .filter(
                ExamPathCatalog.active.is_(True),
                ExamPathCatalog.resolved_exam_code.isnot(None),
            )
            .order_by(ExamPathCatalog.display_order.asc(), ExamPathCatalog.path_key.asc())
            .all()
        )

        if trigger_exam_code:
            trigger_exam_code_norm = str(trigger_exam_code).strip().upper()
            active_paths = [
                p for p in active_paths
                if (p.resolved_exam_code or "").upper() == trigger_exam_code_norm
            ]

        if not active_paths:
            return {
                "rows_written": 0,
                "source_latest_ingestion_run_id": None,
                "source_watermark_year": None,
                "source_watermark_round": None,
            }

        scoped_path_ids = [p.path_id for p in active_paths]
        scoped_exam_codes = sorted({str(p.resolved_exam_code).upper() for p in active_paths})

        (
            self.db.query(SearchReadModel)
            .filter(SearchReadModel.path_id.in_(scoped_path_ids))
            .delete(synchronize_session=False)
        )

        source_latest_ingestion_run_id, source_watermark_year, source_watermark_round = (
            self._compute_source_watermark(scoped_exam_codes)
        )

        active_policy_by_path = self._load_active_policy_by_path(scoped_path_ids)
        branch_option_by_path_program = self._load_branch_option_map(scoped_path_ids)
        taxonomy_by_bucket = self._load_taxonomy_by_bucket(scoped_exam_codes)
        location_by_college = self._load_location_by_college()
        hero_media_by_college = self._load_hero_media_by_college()
        projection_stats_by_key = self._load_projection_stats_by_path(scoped_path_ids)
        college_name_by_id = self._load_college_names()

        rows_written = 0

        for path in active_paths:
            exam_code = str(path.resolved_exam_code).upper()

            latest_year_available, latest_round_available = self._get_exam_latest_year_round(exam_code)
            if latest_year_available is None or latest_round_available is None:
                continue

            live_year, live_round_number = self._derive_live_year_round(
                latest_year_available=latest_year_available,
                latest_round_available=latest_round_available,
                expected_max_rounds=int(path.expected_max_rounds),
            )

            fact_rows = (
                self.db.query(CutoffOutcome)
                .filter(
                    CutoffOutcome.exam_code == exam_code,
                    CutoffOutcome.is_latest.is_(True),
                )
                .all()
            )
            if not fact_rows:
                continue

            grouped_rows = self._group_fact_rows(fact_rows)

            active_policy_id = policy_id or active_policy_by_path.get(path.path_id)

            for (college_id, program_code_key, seat_bucket_code), rows in grouped_rows.items():
                rows_sorted = sorted(rows, key=lambda r: (int(r.year), int(r.round_number)))

                latest_group_year = max(int(r.year) for r in rows_sorted)
                latest_group_round = max(
                    int(r.round_number)
                    for r in rows_sorted
                    if int(r.year) == latest_group_year
                )

                comparison_row, is_projected, current_round_cutoff_value = self._resolve_live_anchor(
                    rows_sorted=rows_sorted,
                    live_year=live_year,
                    live_round_number=live_round_number,
                    latest_group_year=latest_group_year,
                    latest_group_round=latest_group_round,
                    path_id=path.path_id,
                    college_id=college_id,
                    seat_bucket_code=seat_bucket_code,
                    program_code_key=program_code_key,
                    projection_stats_by_key=projection_stats_by_key,
                    metric_type=str(path.metric_type).lower(),
                )

                if comparison_row is None or current_round_cutoff_value is None:
                    continue

                stats_key = (
                    path.path_id,
                    college_id,
                    seat_bucket_code,
                    program_code_key,
                    live_round_number,
                )
                stats_row = projection_stats_by_key.get(stats_key)

                taxonomy = taxonomy_by_bucket.get(seat_bucket_code)
                location = location_by_college.get(college_id)
                hero_media = hero_media_by_college.get(college_id)

                raw_program_code = str(comparison_row.program_code) if comparison_row.program_code is not None else None
                branch_option_key = branch_option_by_path_program.get((path.path_id, program_code_key))

                college_name = college_name_by_id.get(college_id, str(comparison_row.institute_name))

                read_row = SearchReadModel(
                    build_id=build_id,
                    path_id=path.path_id,
                    path_key=path.path_key,
                    exam_code=exam_code,
                    live_round_number=live_round_number,
                    comparison_year=int(comparison_row.year),
                    comparison_round_number=int(comparison_row.round_number),
                    college_id=college_id,
                    college_name=college_name,
                    institute_code=str(comparison_row.institute_code),
                    institute_name=str(comparison_row.institute_name),
                    program_code=raw_program_code,
                    program_name=str(comparison_row.program_name) if comparison_row.program_name is not None else None,
                    branch_option_key=branch_option_key,
                    seat_bucket_code=str(comparison_row.seat_bucket_code),
                    category_name=taxonomy.category_name if taxonomy else None,
                    reservation_type=taxonomy.reservation_type if taxonomy else None,
                    location_type=taxonomy.location_type if taxonomy else None,
                    course_type=taxonomy.course_type if taxonomy else None,
                    state_code=location.state_code if location else None,
                    district=location.district if location else None,
                    pincode=location.pincode if location else None,
                    hero_storage_key=hero_media.storage_key if hero_media else None,
                    hero_public_url=self._derive_public_media_url(
                        storage_key=hero_media.storage_key if hero_media else None
                    ),
                    metric_type=str(path.metric_type).lower(),
                    opening_rank=self._to_decimal_or_none(comparison_row.opening_rank),
                    closing_rank=self._to_decimal_or_none(comparison_row.closing_rank),
                    cutoff_percentile=self._to_decimal_or_none(comparison_row.cutoff_percentile),
                    current_round_cutoff_value=current_round_cutoff_value,
                    is_projected_current_round=is_projected,
                    round_evidence_score=self._stats_or_zero(stats_row, "round_evidence_score"),
                    round_stability_score=self._stats_or_zero(stats_row, "round_stability_score"),
                    current_year_presence_score=self._stats_or_zero(stats_row, "current_year_presence_score"),
                    is_cold_start=bool(getattr(stats_row, "is_cold_start", True)) if stats_row else True,
                    source_authority=comparison_row.source_authority,
                    source_document=comparison_row.source_document,
                    valid_from=comparison_row.valid_from,
                    latest_year_available=latest_group_year,
                    latest_round_available=latest_group_round,
                    active_policy_id=active_policy_id,
                )

                self.db.add(read_row)
                rows_written += 1

        self.db.flush()

        return {
            "rows_written": rows_written,
            "source_latest_ingestion_run_id": source_latest_ingestion_run_id,
            "source_watermark_year": source_watermark_year,
            "source_watermark_round": source_watermark_round,
        }

    def _compute_source_watermark(self, exam_codes: list[str]) -> tuple[Any | None, int | None, int | None]:
        latest_year = (
            self.db.query(func.max(CutoffOutcome.year))
            .filter(CutoffOutcome.exam_code.in_(exam_codes))
            .scalar()
        )
        if latest_year is None:
            return None, None, None

        latest_year = int(latest_year)
        latest_round = (
            self.db.query(func.max(CutoffOutcome.round_number))
            .filter(
                CutoffOutcome.exam_code.in_(exam_codes),
                CutoffOutcome.year == latest_year,
            )
            .scalar()
        )
        latest_round = int(latest_round) if latest_round is not None else None

        latest_row = (
            self.db.query(CutoffOutcome.ingestion_run_id)
            .filter(
                CutoffOutcome.exam_code.in_(exam_codes),
                CutoffOutcome.year == latest_year,
                CutoffOutcome.round_number == latest_round,
            )
            .order_by(desc(CutoffOutcome.valid_from), desc(CutoffOutcome.id))
            .first()
        )

        latest_ingestion_run_id = latest_row[0] if latest_row else None
        return latest_ingestion_run_id, latest_year, latest_round

    def _get_exam_latest_year_round(self, exam_code: str) -> tuple[int | None, int | None]:
        latest_year = (
            self.db.query(func.max(CutoffOutcome.year))
            .filter(
                CutoffOutcome.exam_code == exam_code,
                CutoffOutcome.is_latest.is_(True),
            )
            .scalar()
        )
        if latest_year is None:
            return None, None

        latest_year = int(latest_year)
        latest_round = (
            self.db.query(func.max(CutoffOutcome.round_number))
            .filter(
                CutoffOutcome.exam_code == exam_code,
                CutoffOutcome.is_latest.is_(True),
                CutoffOutcome.year == latest_year,
            )
            .scalar()
        )

        return latest_year, int(latest_round) if latest_round is not None else None

    @staticmethod
    def _derive_live_year_round(
        *,
        latest_year_available: int,
        latest_round_available: int,
        expected_max_rounds: int,
    ) -> tuple[int, int]:
        if latest_round_available < expected_max_rounds:
            return latest_year_available, latest_round_available + 1
        return latest_year_available + 1, 1

    def _group_fact_rows(
        self,
        rows: list[CutoffOutcome],
    ) -> dict[tuple[Any, str, str], list[CutoffOutcome]]:
        grouped: dict[tuple[Any, str, str], list[CutoffOutcome]] = defaultdict(list)

        for row in rows:
            if not row.college_id:
                continue
            key = (
                row.college_id,
                self._normalize_program_code_key(row.program_code),
                str(row.seat_bucket_code),
            )
            grouped[key].append(row)

        return grouped

    def _resolve_live_anchor(
        self,
        *,
        rows_sorted: list[CutoffOutcome],
        live_year: int,
        live_round_number: int,
        latest_group_year: int,
        latest_group_round: int,
        path_id: Any,
        college_id: Any,
        seat_bucket_code: str,
        program_code_key: str,
        projection_stats_by_key: dict[tuple[Any, Any, str, str, int], RoundProjectionStats],
        metric_type: str,
    ) -> tuple[CutoffOutcome | None, bool, Decimal | None]:
        by_year_round = {
            (int(r.year), int(r.round_number)): r
            for r in rows_sorted
        }

        actual_live_row = by_year_round.get((live_year, live_round_number))
        if actual_live_row:
            return actual_live_row, False, self._metric_decimal(actual_live_row, metric_type)

        if live_round_number == 1:
            same_round_rows = [r for r in rows_sorted if int(r.round_number) == 1]
            if not same_round_rows:
                return None, False, None

            comparison_row = max(same_round_rows, key=lambda r: int(r.year))
            return comparison_row, False, self._metric_decimal(comparison_row, metric_type)

        latest_actual_row = max(rows_sorted, key=lambda r: (int(r.year), int(r.round_number)))

        if int(latest_actual_row.year) != live_year:
            return None, True, None

        start_round = int(latest_actual_row.round_number)
        if start_round >= live_round_number:
            return None, True, None

        current_value = self._metric_decimal(latest_actual_row, metric_type)
        if current_value is None:
            return None, True, None

        for target_round in range(start_round + 1, live_round_number + 1):
            stats_key = (
                path_id,
                college_id,
                seat_bucket_code,
                program_code_key,
                target_round,
            )
            stats_row = projection_stats_by_key.get(stats_key)
            if not stats_row or stats_row.relaxation_ratio_from_prev_round is None:
                return None, True, None

            ratio = Decimal(str(stats_row.relaxation_ratio_from_prev_round))
            current_value = current_value * ratio

        return latest_actual_row, True, current_value

    def _load_active_policy_by_path(self, path_ids: list[Any]) -> dict[Any, Any]:
        mapping: dict[Any, Any] = {}

        rows = (
            self.db.query(ProbabilityPolicyConfig)
            .filter(
                ProbabilityPolicyConfig.is_active.is_(True),
                ProbabilityPolicyConfig.path_id.in_(path_ids),
            )
            .order_by(ProbabilityPolicyConfig.path_id.asc(), ProbabilityPolicyConfig.version_no.desc())
            .all()
        )

        for row in rows:
            if row.path_id not in mapping:
                mapping[row.path_id] = row.policy_id

        global_policy = (
            self.db.query(ProbabilityPolicyConfig)
            .filter(
                ProbabilityPolicyConfig.is_active.is_(True),
                ProbabilityPolicyConfig.path_id.is_(None),
            )
            .order_by(ProbabilityPolicyConfig.version_no.desc())
            .first()
        )

        if global_policy:
            for path_id in path_ids:
                mapping.setdefault(path_id, global_policy.policy_id)

        return mapping

    def _load_branch_option_map(self, path_ids: list[Any]) -> dict[tuple[Any, str], str]:
        mapping: dict[tuple[Any, str], str] = {}

        rows = (
            self.db.query(ExamProgramServingMap)
            .filter(
                ExamProgramServingMap.path_id.in_(path_ids),
                ExamProgramServingMap.mapping_status.in_(
                    [MappingStatusEnum.APPROVED, MappingStatusEnum.AUTO_APPROVED]
                ),
            )
            .all()
        )

        for row in rows:
            key = (row.path_id, self._normalize_program_code_key(row.program_code))
            if key not in mapping:
                mapping[key] = row.branch_option_key

        return mapping

    def _load_taxonomy_by_bucket(self, exam_codes: list[str]) -> dict[str, SeatBucketTaxonomy]:
        rows = (
            self.db.query(SeatBucketTaxonomy)
            .filter(SeatBucketTaxonomy.exam_code.in_(exam_codes))
            .all()
        )
        return {str(r.seat_bucket_code): r for r in rows}

    def _load_location_by_college(self) -> dict[Any, CollegeLocation]:
        rows = self.db.query(CollegeLocation).all()
        return {row.college_id: row for row in rows}

    def _load_hero_media_by_college(self) -> dict[Any, CollegeMedia]:
        rows = (
            self.db.query(CollegeMedia)
            .filter(
                CollegeMedia.status == MediaStatusEnum.ACCEPTED,
                CollegeMedia.media_type == MediaTypeEnum.CAMPUS_HERO,
            )
            .order_by(CollegeMedia.college_id.asc(), desc(CollegeMedia.ingested_at))
            .all()
        )

        media_by_college: dict[Any, CollegeMedia] = {}
        for row in rows:
            media_by_college.setdefault(row.college_id, row)
        return media_by_college

    def _load_projection_stats_by_path(
        self,
        path_ids: list[Any],
    ) -> dict[tuple[Any, Any, str, str, int], RoundProjectionStats]:
        rows = (
            self.db.query(RoundProjectionStats)
            .filter(RoundProjectionStats.path_id.in_(path_ids))
            .all()
        )

        mapping: dict[tuple[Any, Any, str, str, int], RoundProjectionStats] = {}
        for row in rows:
            key = (
                row.path_id,
                row.college_id,
                str(row.seat_bucket_code),
                self._normalize_program_code_key(row.program_code),
                int(row.round_number),
            )
            mapping[key] = row

        return mapping

    def _load_college_names(self) -> dict[Any, str]:
        rows = self.db.query(College.college_id, College.canonical_name).all()
        return {
            row.college_id: str(row.canonical_name)
            for row in rows
            if row.college_id and row.canonical_name
        }

    @staticmethod
    def _derive_public_media_url(storage_key: str | None) -> str | None:
        """
        Derive browser-renderable media URL from canonical storage key.

        Architecture:
        - storage_key remains the SOT
        - browser receives only a delivery URL
        - frontend must never construct provider URLs itself

        Resolution order:
        1. CDN_PUBLIC_BASE (preferred browser-facing delivery base)
        2. fallback to S3_ENDPOINT_URL + bucket for local/dev
        """
        if not storage_key:
            return None

        normalized_key = str(storage_key).strip().lstrip("/")
        if not normalized_key:
            return None

        cdn_public_base = str(os.getenv("CDN_PUBLIC_BASE", "")).strip().rstrip("/")
        if cdn_public_base:
            return f"{cdn_public_base}/{normalized_key}"

        s3_endpoint_url = str(os.getenv("S3_ENDPOINT_URL", "")).strip().rstrip("/")
        s3_bucket_name = str(os.getenv("S3_BUCKET_NAME", "")).strip()

        if s3_endpoint_url and s3_bucket_name:
            return f"{s3_endpoint_url}/{s3_bucket_name}/{normalized_key}"

        return None

    @staticmethod
    def _metric_decimal(row: CutoffOutcome, metric_type: str) -> Decimal | None:
        metric = str(metric_type or "rank").lower()
        if metric == "percentile":
            return SearchReadModelBuilder._to_decimal_or_none(row.cutoff_percentile)
        return SearchReadModelBuilder._to_decimal_or_none(row.closing_rank)

    @staticmethod
    def _to_decimal_or_none(value: Any) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value))

    @staticmethod
    def _stats_or_zero(stats_row: RoundProjectionStats | None, attr_name: str) -> Decimal:
        if not stats_row:
            return Decimal("0")
        value = getattr(stats_row, attr_name, None)
        return Decimal(str(value)) if value is not None else Decimal("0")

    @staticmethod
    def _normalize_program_code_key(value: Any) -> str:
        return str(value) if value is not None else ""