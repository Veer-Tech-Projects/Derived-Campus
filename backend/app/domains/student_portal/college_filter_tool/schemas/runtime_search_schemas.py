from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ============================================================
# ENUMS
# ============================================================

class MetricType(str, Enum):
    RANK = "rank"
    PERCENTILE = "percentile"


class CollegeBand(str, Enum):
    SAFE = "SAFE"
    MODERATE = "MODERATE"
    HARD = "HARD"
    SUGGESTED = "SUGGESTED"


class SortMode(str, Enum):
    BEST_FIT = "best_fit"


class FilterControlType(str, Enum):
    NUMBER_INPUT = "NUMBER_INPUT"
    SELECT = "SELECT"
    AUTOCOMPLETE = "AUTOCOMPLETE"


class OptionSource(str, Enum):
    STATIC = "STATIC"
    SERVING_MAP = "SERVING_MAP"
    BRANCH = "BRANCH"
    LOCATION = "LOCATION"
    PATH_OPTION = "PATH_OPTION"


# ============================================================
# REQUEST DTOs
# ============================================================

class BandPageRequest(BaseModel):
    """
    Independent page cursor per band.
    This keeps the API future-safe for tabbed UIs where each band paginates independently.
    """
    safe: int = Field(default=1, ge=1)
    moderate: int = Field(default=1, ge=1)
    hard: int = Field(default=1, ge=1)
    suggested: int = Field(default=1, ge=1)


class CollegeFilterSearchRequest(BaseModel):
    """
    Runtime search request for the student-facing college filter engine.

    Notes:
    - `score` is intentionally not metric-validated here because the path metadata
      defines whether it should behave as Rank or Percentile.
    - `filters` stays dynamic because required/visible controls are path-governed
      from exam_path_filter_schema.
    """
    path_id: UUID
    score: Decimal = Field(..., description="Student input score; interpreted by path metric_type.")
    filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Dynamic path-aware filter payload keyed by governed filter_key."
    )
    page_size: int = Field(default=10, ge=1)
    page_by_band: BandPageRequest = Field(default_factory=BandPageRequest)
    sort_mode: SortMode = Field(default=SortMode.BEST_FIT)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("score")
    @classmethod
    def validate_score(cls, value: Decimal) -> Decimal:
        if value is None:
            raise ValueError("score is required")
        if value <= 0:
            raise ValueError("score must be greater than 0")
        return value

    @field_validator("filters")
    @classmethod
    def validate_filters(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError("filters must be an object/dictionary")
        return value


# ============================================================
# METADATA DTOs
# ============================================================

class FilterOptionDTO(BaseModel):
    """
    One selectable option for metadata-driven controls.
    """
    value: str
    label: str
    sort_order: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class FilterDependencyDTO(BaseModel):
    """
    Encodes parent-child dependency rules for dynamic UI rendering.
    """
    depends_on_filter_key: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class FilterSchemaDTO(BaseModel):
    """
    API-safe projection of exam_path_filter_schema plus resolved runtime options.
    """
    filter_key: str
    filter_label: str
    control_type: FilterControlType
    option_source: OptionSource
    is_required: bool
    is_visible: bool
    is_auto_fillable: bool
    sort_order: int
    dependency: FilterDependencyDTO = Field(default_factory=FilterDependencyDTO)
    options: List[FilterOptionDTO] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class PathSummaryDTO(BaseModel):
    path_id: UUID
    path_key: str
    visible_label: str
    exam_family: str
    resolved_exam_code: Optional[str] = None
    education_type: Optional[str] = None
    selection_type: Optional[str] = None
    metric_type: MetricType
    expected_max_rounds: int
    supports_branch: bool
    supports_course_relaxation: bool
    supports_location_filter: bool
    supports_opening_rank: bool

    model_config = ConfigDict(extra="forbid")


class PathCatalogItemDTO(BaseModel):
    """
    Student-visible path catalog item used to bootstrap the initial exam/path selector.

    This is intentionally a thin projection of exam_path_catalog so the frontend
    can render the path tree dynamically without hardcoding.
    """
    path_id: UUID
    parent_path_id: Optional[UUID] = None

    path_key: str
    visible_label: str
    exam_family: str

    resolved_exam_code: Optional[str] = None
    education_type: Optional[str] = None
    selection_type: Optional[str] = None

    metric_type: MetricType
    expected_max_rounds: int

    supports_branch: bool
    supports_course_relaxation: bool
    supports_location_filter: bool
    supports_opening_rank: bool

    active: bool
    display_order: int

    model_config = ConfigDict(extra="forbid")


class CollegeFilterPathCatalogResponse(BaseModel):
    """
    Bootstrap response for the first student-facing college-filter selection step.

    Returns the active path catalog tree in display order so the frontend can:
    - render root exam/path choices dynamically
    - reveal child paths where applicable
    - avoid hardcoding exam families or path keys
    """
    items: List[PathCatalogItemDTO] = Field(default_factory=list)
    generated_at: datetime

    model_config = ConfigDict(extra="forbid")


class CollegeFilterMetadataResponse(BaseModel):
    """
    Metadata contract for building the student UI dynamically.

    This endpoint should tell the frontend:
    - which dropdowns to show
    - which are required
    - which depend on another filter
    - what options are currently available
    """
    path: PathSummaryDTO
    filters: List[FilterSchemaDTO] = Field(default_factory=list)
    generated_at: datetime

    model_config = ConfigDict(extra="forbid")


# ============================================================
# RESPONSE DTOs — SEARCH
# ============================================================

class ProbabilityEvidenceDTO(BaseModel):
    """
    Minimal explanation payload for display/debugging.
    """
    round_evidence_score: Optional[Decimal] = None
    round_stability_score: Optional[Decimal] = None
    current_year_presence_score: Optional[Decimal] = None
    is_cold_start: bool = False
    is_projected_current_round: bool = False

    model_config = ConfigDict(extra="forbid")


class ComparisonContextDTO(BaseModel):
    """
    Runtime comparison context for one card.
    """
    metric_type: MetricType
    user_score: Decimal
    current_round_cutoff_value: Decimal
    margin_value: Decimal
    qualified_against_current_anchor: bool

    model_config = ConfigDict(extra="forbid")


class CollegeCardDTO(BaseModel):
    """
    One student-facing college/program/seat card.

    Notes:
    - opening_rank is optional and display-only.
    - institute_code is intentionally included per approved business rule.
    - probability_percent is per-card, runtime-computed.
    """
    college_id: UUID
    college_name: str
    institute_code: Optional[str] = None

    exam_code: str
    path_id: UUID
    path_key: str

    program_code: str
    program_name: str
    branch_option_key: Optional[str] = None
    branch_display_name: Optional[str] = None

    seat_bucket_code: str
    category_name: Optional[str] = None
    course_type: Optional[str] = None
    location_type: Optional[str] = None
    reservation_type: Optional[str] = None
    gender: Optional[str] = None

    city: Optional[str] = None
    district: Optional[str] = None
    state_code: Optional[str] = None
    pincode: Optional[str] = None

    logo_url: Optional[str] = None
    hero_storage_key: Optional[str] = None
    hero_media_url: Optional[str] = None

    current_round_cutoff_value: Decimal
    opening_rank: Optional[int] = None

    probability_percent: Decimal = Field(..., ge=Decimal("0"), le=Decimal("100"))
    band: CollegeBand

    evidence: ProbabilityEvidenceDTO
    comparison: ComparisonContextDTO

    latest_year_available: Optional[int] = None
    latest_round_available: Optional[int] = None
    comparison_year: Optional[int] = None
    comparison_round_number: Optional[int] = None
    live_round_number: Optional[int] = None

    model_config = ConfigDict(extra="forbid")

    @field_validator("college_name", "program_name", "program_code", "seat_bucket_code", "exam_code", "path_key")
    @classmethod
    def validate_non_empty_strings(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("string fields must not be empty")
        return value.strip()


class BandPaginationDTO(BaseModel):
    """
    Pagination metadata for one band bucket.

    Important:
    - total_matching_count = real uncapped count before the 200-row band cap
    - capped_total_available = min(total_matching_count, cap)
    - has_next_page must become false once capped depth is exhausted
    """
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1)

    total_matching_count: int = Field(..., ge=0)
    capped_total_available: int = Field(..., ge=0)

    has_next_page: bool
    cap_reached: bool

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_count_relationships(self) -> "BandPaginationDTO":
        if self.capped_total_available > self.total_matching_count:
            raise ValueError("capped_total_available cannot exceed total_matching_count")
        return self


class BandResultDTO(BaseModel):
    band: CollegeBand
    items: List[CollegeCardDTO] = Field(default_factory=list)
    pagination: BandPaginationDTO

    model_config = ConfigDict(extra="forbid")


class BandCountsDTO(BaseModel):
    """
    Aggregate counts across all buckets.

    For SAFE / MODERATE / HARD:
    - counts represent real uncapped matches above threshold before 200-row truncation

    For SUGGESTED:
    - count represents the alternative-path suggestion result size actually emitted
      by the secondary relaxed query
    """
    safe: int = Field(default=0, ge=0)
    moderate: int = Field(default=0, ge=0)
    hard: int = Field(default=0, ge=0)
    suggested: int = Field(default=0, ge=0)

    model_config = ConfigDict(extra="forbid")


class SearchBandsDTO(BaseModel):
    safe: BandResultDTO
    moderate: BandResultDTO
    hard: BandResultDTO
    suggested: BandResultDTO

    model_config = ConfigDict(extra="forbid")


class CollegeFilterSearchResponse(BaseModel):
    """
    Final student-facing response for runtime search.

    Binding business rules reflected here:
    - per-card probability %
    - grouped safety bands
    - counts for band summary chips
    - suggested alternatives as a separate bucket
    - capped pagination metadata per band
    """
    path: PathSummaryDTO
    user_score: Decimal
    total_matching_count: int = Field(..., ge=0)
    band_counts: BandCountsDTO
    bands: SearchBandsDTO
    generated_at: datetime

    model_config = ConfigDict(extra="forbid")