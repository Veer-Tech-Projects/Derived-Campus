from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import Boolean, Select, and_, cast, false, func, or_, select
from sqlalchemy.orm import Session

from app.models import (
    ExamProgramServingMap,
    JosaaCollegeMetadata,
    SearchReadModel,
    SeatBucketTaxonomy,
)
from app.domains.student_portal.college_filter_tool.services.path_validation_service import (
    ResolvedPathContext,
)


# ============================================================
# REPOSITORY DTOs
# ============================================================

@dataclass(frozen=True)
class SearchRepositoryRow:
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
    branch_option_key: Optional[str]

    seat_bucket_code: str
    category_name: Optional[str]
    reservation_type: Optional[str]
    location_type: Optional[str]
    course_type: Optional[str]

    state_code: Optional[str]
    district: Optional[str]
    pincode: Optional[str]

    hero_storage_key: Optional[str]
    hero_public_url: Optional[str]

    metric_type: str

    opening_rank: Optional[Decimal]
    closing_rank: Optional[Decimal]
    cutoff_percentile: Optional[Decimal]

    current_round_cutoff_value: Optional[Decimal]
    is_projected_current_round: bool

    round_evidence_score: Decimal
    round_stability_score: Decimal
    current_year_presence_score: Decimal
    is_cold_start: bool

    source_authority: Optional[str]
    source_document: Optional[str]
    valid_from: Any

    latest_year_available: int
    latest_round_available: int

    active_policy_id: Optional[UUID]


@dataclass(frozen=True)
class SearchRepositoryResult:
    rows: List[SearchRepositoryRow]
    total_matching_count: int


@dataclass(frozen=True)
class SuggestedRepositoryResult:
    rows: List[SearchRepositoryRow]


# ============================================================
# REPOSITORY
# ============================================================

class SearchRepository:
    """
    Final Step 7C runtime repository.

    Design contract:
    - search_read_model is the primary runtime candidate source
    - runtime does not redo Step 4 normalization policy
    - metadata/options come from exam_seat_filter_serving_map
    - row membership comes from:
        * search_read_model flattened columns where available
        * SeatBucketTaxonomy only for approved non-flattened seat filters
        * JosaaCollegeMetadata only for JEE institute_type
    - primary query returns ALL filtered rows
    - no SQL pagination here; banding/cap/pagination happen later
    """

    SUGGESTED_CANDIDATE_LIMIT = 500

    def __init__(self, db: Session):
        self.db = db

    # --------------------------------------------------------
    # PRIMARY QUERY
    # --------------------------------------------------------

    def search_primary(
        self,
        *,
        path_context: ResolvedPathContext,
    ) -> SearchRepositoryResult:
        """
        Return the full exact-path candidate set after hard filters.

        Important:
        - no OFFSET/LIMIT here
        - Step 7D/7E/7F will handle probability, bands, sorting, 200-row caps, and pagination
        """
        base_query = self._build_primary_base_query(path_context=path_context)

        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_matching_count = int(self.db.execute(count_stmt).scalar() or 0)

        rows_stmt = base_query.order_by(
            SearchReadModel.comparison_year.desc(),
            SearchReadModel.comparison_round_number.desc(),
            SearchReadModel.college_name.asc(),
            SearchReadModel.college_id.asc(),
            SearchReadModel.program_code.asc(),
            SearchReadModel.seat_bucket_code.asc(),
        )

        rows = self.db.execute(rows_stmt).scalars().all()

        return SearchRepositoryResult(
            rows=[self._map_row(row) for row in rows],
            total_matching_count=total_matching_count,
        )

    # --------------------------------------------------------
    # SUGGESTED CANDIDATE QUERY
    # --------------------------------------------------------

    def search_suggested_candidates(
        self,
        *,
        path_context: ResolvedPathContext,
        exclude_identities: Iterable[Tuple[UUID, str, str]],
    ) -> SuggestedRepositoryResult:
        """
        Secondary relaxed candidate pool for SUGGESTED.

        Rules:
        - keep demographic/location/institute filters
        - relax branch filter
        - relax course filter only if path supports course relaxation
        - final probability >= 45 and top-10 trimming happen later
        """
        base_query = self._build_suggested_base_query(path_context=path_context)

        rows_stmt = (
            base_query
            .order_by(
                SearchReadModel.comparison_year.desc(),
                SearchReadModel.comparison_round_number.desc(),
                SearchReadModel.college_name.asc(),
                SearchReadModel.college_id.asc(),
                SearchReadModel.program_code.asc(),
                SearchReadModel.seat_bucket_code.asc(),
            )
            .limit(self.SUGGESTED_CANDIDATE_LIMIT)
        )

        rows = self.db.execute(rows_stmt).scalars().all()
        mapped_rows = [self._map_row(row) for row in rows]

        exclude_set = set(exclude_identities)
        filtered_rows = [
            row
            for row in mapped_rows
            if (row.college_id, row.program_code, row.seat_bucket_code) not in exclude_set
        ]

        return SuggestedRepositoryResult(rows=filtered_rows)

    # --------------------------------------------------------
    # INTERNAL QUERY BUILDERS
    # --------------------------------------------------------

    def _build_primary_base_query(
        self,
        *,
        path_context: ResolvedPathContext,
    ) -> Select:
        stmt = select(SearchReadModel).where(
            SearchReadModel.path_id == path_context.path_id,
            SearchReadModel.current_round_cutoff_value.is_not(None),
        )

        stmt = self._apply_common_filters(
            stmt=stmt,
            path_context=path_context,
            filters=path_context.normalized_filters,
            relax_course_filter=False,
            relax_branch_filter=False,
        )

        return stmt

    def _build_suggested_base_query(
        self,
        *,
        path_context: ResolvedPathContext,
    ) -> Select:
        stmt = select(SearchReadModel).where(
            SearchReadModel.path_id == path_context.path_id,
            SearchReadModel.current_round_cutoff_value.is_not(None),
        )

        stmt = self._apply_common_filters(
            stmt=stmt,
            path_context=path_context,
            filters=path_context.normalized_filters,
            relax_course_filter=bool(path_context.supports_course_relaxation),
            relax_branch_filter=True,
        )

        return stmt

    # --------------------------------------------------------
    # FILTER APPLICATION
    # --------------------------------------------------------

    def _apply_common_filters(
        self,
        *,
        stmt: Select,
        path_context: ResolvedPathContext,
        filters: Dict[str, Any],
        relax_course_filter: bool,
        relax_branch_filter: bool,
    ) -> Select:
        """
        Filter source strategy:

        1) Primary flattened filters from search_read_model
        2) Conditional row-level joins only for approved non-flattened filters:
           - gender / is_pwd      -> SeatBucketTaxonomy
           - institute_type (JEE) -> latest JosaaCollegeMetadata row
        """

        # ---------- Flattened runtime filters on SearchReadModel ----------
        category = self._string_filter(filters, "category")
        if category:
            stmt = stmt.where(
                self._normalized_sql_key(SearchReadModel.category_name)
                == self._normalize_option_key(category)
            )

        reservation_type = self._string_filter(filters, "reservation_type")
        if reservation_type:
            stmt = stmt.where(
                self._normalized_sql_key(SearchReadModel.reservation_type)
                == self._normalize_option_key(reservation_type)
            )

        location_type = self._string_filter(filters, "location_type")
        if location_type:
            stmt = stmt.where(
                self._normalized_sql_key(SearchReadModel.location_type)
                == self._normalize_option_key(location_type)
            )

        course_type = self._string_filter(filters, "course_type")
        if course_type and not relax_course_filter:
            stmt = stmt.where(
                self._normalized_sql_key(SearchReadModel.course_type)
                == self._normalize_option_key(course_type)
            )

        state_code = self._string_filter(filters, "state_code")
        if state_code:
            stmt = stmt.where(SearchReadModel.state_code == state_code)

        district = self._string_filter(filters, "district")
        if district:
            stmt = stmt.where(func.lower(SearchReadModel.district) == district.lower())

        pincode = self._string_filter(filters, "pincode")
        if pincode:
            stmt = stmt.where(SearchReadModel.pincode == pincode)

        branch_value = self._string_filter(filters, "branch")
        variant_value = self._string_filter(filters, "variant")

        if branch_value and not relax_branch_filter:
            matched_program_codes = self._resolve_program_codes_for_branch_selection(
                path_id=path_context.path_id,
                branch_value=branch_value,
                variant_value=variant_value,
            )

            if not matched_program_codes:
                stmt = stmt.where(false())
            else:
                stmt = stmt.where(SearchReadModel.program_code.in_(matched_program_codes))

        # ---------- Conditional row-level join for gender / is_pwd ----------
        gender = self._string_filter(filters, "gender")
        is_pwd = self._normalize_bool_like(filters.get("is_pwd"))

        if gender is not None or is_pwd is not None:
            stmt = stmt.join(
                SeatBucketTaxonomy,
                SearchReadModel.seat_bucket_code == SeatBucketTaxonomy.seat_bucket_code,
            )

            if path_context.resolved_exam_code:
                stmt = stmt.where(SeatBucketTaxonomy.exam_code == path_context.resolved_exam_code)

            if gender is not None:
                stmt = stmt.where(self._build_gender_predicate(gender))

            if is_pwd is not None:
                stmt = stmt.where(self._build_is_pwd_predicate(is_pwd))

        # ---------- Conditional row-level join for JEE institute_type ----------
        institute_type = self._string_filter(filters, "institute_type")
        if institute_type is not None:
            if path_context.resolved_exam_code not in {"JEE_MAIN", "JEE_ADV"}:
                raise ValueError("institute_type filter is only supported for JEE paths")

            stmt = self._join_latest_josaa_metadata(stmt=stmt)

            canonical_institute_type = self._normalize_option_key(institute_type)
            josaa_institute_type_key = self._normalized_sql_key(JosaaCollegeMetadata.institute_type)

            stmt = stmt.where(
                josaa_institute_type_key == canonical_institute_type,
                JosaaCollegeMetadata.exam_code == path_context.resolved_exam_code,
            )

        return stmt

    # --------------------------------------------------------
    # SPECIAL JOINS / PREDICATES
    # --------------------------------------------------------

    def _join_latest_josaa_metadata(self, *, stmt: Select) -> Select:
        """
        Join the latest josaa_college_metadata row per (college_id, exam_code).

        This avoids duplicate expansion across metadata years.
        """
        latest_year_subquery = (
            select(
                JosaaCollegeMetadata.college_id.label("college_id"),
                JosaaCollegeMetadata.exam_code.label("exam_code"),
                func.max(JosaaCollegeMetadata.year).label("latest_year"),
            )
            .group_by(
                JosaaCollegeMetadata.college_id,
                JosaaCollegeMetadata.exam_code,
            )
            .subquery("josaa_latest_year")
        )

        return (
            stmt.join(
                latest_year_subquery,
                and_(
                    SearchReadModel.college_id == latest_year_subquery.c.college_id,
                    SearchReadModel.exam_code == latest_year_subquery.c.exam_code,
                ),
            )
            .join(
                JosaaCollegeMetadata,
                and_(
                    JosaaCollegeMetadata.college_id == latest_year_subquery.c.college_id,
                    JosaaCollegeMetadata.exam_code == latest_year_subquery.c.exam_code,
                    JosaaCollegeMetadata.year == latest_year_subquery.c.latest_year,
                ),
            )
        )

    def _build_branch_predicate(self, branch_value: str):
        """
        Transitional-safe branch predicate.

        UI may label this as "Academic Program" for JEE, but row identity still comes
        from program/branch fields in the serving model.

        Preferred:
        - exact match on branch_option_key

        Transitional fallback:
        - when branch_option_key is NULL, fall back to program_name search
        """
        normalized = branch_value.strip()
        like_value = f"%{normalized}%"

        return or_(
            SearchReadModel.branch_option_key == normalized,
            and_(
                SearchReadModel.branch_option_key.is_(None),
                SearchReadModel.program_name.ilike(like_value),
            ),
        )

    def _build_gender_predicate(self, gender_option_key: str):
        """
        Canonical option-key comparison only.

        Step 4 already owns normalization policy for filter options.
        Runtime therefore compares canonical-to-canonical instead of re-expanding
        hardcoded synonym sets.
        """
        canonical_key = self._normalize_option_key(gender_option_key)

        jsonb_gender_key = self._normalized_sql_key(
            SeatBucketTaxonomy.attributes["gender"].astext
        )
        reservation_gender_key = self._normalized_sql_key(
            SeatBucketTaxonomy.reservation_type
        )

        return or_(
            jsonb_gender_key == canonical_key,
            reservation_gender_key == canonical_key,
        )

    def _build_is_pwd_predicate(self, is_pwd: bool):
        """
        PwD uses canonical runtime boolean semantics:
        - Step 4 options expose yes/no
        - request is normalized to bool
        - row-level source comes from taxonomy JSONB
        """
        jsonb_is_pwd_expr = cast(
            SeatBucketTaxonomy.attributes["is_pwd"].astext,
            Boolean,
        )
        return jsonb_is_pwd_expr.is_(is_pwd)

    # --------------------------------------------------------
    # HELPERS
    # --------------------------------------------------------

    @staticmethod
    def _string_filter(filters: Dict[str, Any], key: str) -> Optional[str]:
        value = filters.get(key)
        if value is None:
            return None
        if not isinstance(value, str):
            value = str(value)
        value = value.strip()
        return value or None

    @staticmethod
    def _normalize_bool_like(value: Any) -> Optional[bool]:
        if value is None:
            return None
        if isinstance(value, bool):
            return value

        normalized = str(value).strip().lower()
        if normalized in {"yes", "true", "1"}:
            return True
        if normalized in {"no", "false", "0"}:
            return False
        return None

    @staticmethod
    def _normalize_option_key(value: str) -> str:
        """
        Canonical option-key normalization aligned to Step 4 semantics:
        lowercase + underscores for spaces.
        """
        return str(value).strip().lower().replace(" ", "_")

    @staticmethod
    def _normalized_sql_key(sql_expr):
        """
        SQL-side canonicalization aligned with Step 4 option_key policy:
        lowercase + replace spaces with underscores.
        """
        return func.replace(func.lower(func.coalesce(sql_expr, "")), " ", "_")

    def _resolve_program_codes_for_branch_selection(
        self,
        *,
        path_id: UUID,
        branch_value: str,
        variant_value: Optional[str],
    ) -> List[str]:
        """
        Resolve governed branch selection to concrete program codes using
        exam_program_serving_map.

        Runtime semantics:
        - branch only      -> all program codes under that discipline
        - branch + variant -> only program codes under that specialization
        """
        normalized_branch = self._normalize_branch_key(branch_value)

        query = (
            self.db.query(ExamProgramServingMap.program_code)
            .filter(
                ExamProgramServingMap.path_id == path_id,
                func.lower(ExamProgramServingMap.branch_discipline_key) == normalized_branch,
            )
            .distinct()
        )

        if variant_value is not None:
            normalized_variant = self._normalize_branch_key(variant_value)
            query = query.filter(
                func.lower(ExamProgramServingMap.specialization_key) == normalized_variant
            )

        rows = query.all()
        return [str(program_code) for (program_code,) in rows if program_code]

    @staticmethod
    def _normalize_branch_key(value: str) -> str:
        """
        Branch/variant keys come from exam_program_serving_map branch_discipline_key
        and specialization_key, which are lowercase text keys (not underscore-normalized
        option keys like seat filters).
        """
        return " ".join(str(value).strip().lower().split())

    @staticmethod
    def _map_row(row: SearchReadModel) -> SearchRepositoryRow:
        return SearchRepositoryRow(
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
            metric_type=row.metric_type,
            opening_rank=row.opening_rank,
            closing_rank=row.closing_rank,
            cutoff_percentile=row.cutoff_percentile,
            current_round_cutoff_value=row.current_round_cutoff_value,
            is_projected_current_round=bool(row.is_projected_current_round),
            round_evidence_score=row.round_evidence_score,
            round_stability_score=row.round_stability_score,
            current_year_presence_score=row.current_year_presence_score,
            is_cold_start=bool(row.is_cold_start),
            source_authority=row.source_authority,
            source_document=row.source_document,
            valid_from=row.valid_from,
            latest_year_available=row.latest_year_available,
            latest_round_available=row.latest_round_available,
            active_policy_id=row.active_policy_id,
        )