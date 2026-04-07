export type UUID = string;

export type MetricType = "rank" | "percentile";
export type CollegeBand = "SAFE" | "MODERATE" | "HARD" | "SUGGESTED";
export type SortMode = "best_fit";

export type FilterControlType = "NUMBER_INPUT" | "SELECT" | "AUTOCOMPLETE";
export type OptionSource =
  | "STATIC"
  | "SERVING_MAP"
  | "BRANCH"
  | "LOCATION"
  | "PATH_OPTION";

export interface PathCatalogItemDTO {
  path_id: UUID;
  parent_path_id: UUID | null;

  path_key: string;
  visible_label: string;
  exam_family: string;

  resolved_exam_code: string | null;
  education_type: string | null;
  selection_type: string | null;

  metric_type: MetricType;
  expected_max_rounds: number;

  supports_branch: boolean;
  supports_course_relaxation: boolean;
  supports_location_filter: boolean;
  supports_opening_rank: boolean;

  active: boolean;
  display_order: number;
}

export interface CollegeFilterPathCatalogResponse {
  items: PathCatalogItemDTO[];
  generated_at: string;
}

export interface FilterOptionDTO {
  value: string;
  label: string;
  sort_order?: number | null;
  metadata: Record<string, unknown>;
}

export interface FilterDependencyDTO {
  depends_on_filter_key?: string | null;
}

export interface FilterSchemaDTO {
  filter_key: string;
  filter_label: string;
  control_type: FilterControlType;
  option_source: OptionSource;
  is_required: boolean;
  is_visible: boolean;
  is_auto_fillable: boolean;
  sort_order: number;
  dependency: FilterDependencyDTO;
  options: FilterOptionDTO[];
}

export interface PathSummaryDTO {
  path_id: UUID;
  path_key: string;
  visible_label: string;
  exam_family: string;
  resolved_exam_code: string | null;
  education_type: string | null;
  selection_type: string | null;
  metric_type: MetricType;
  expected_max_rounds: number;
  supports_branch: boolean;
  supports_course_relaxation: boolean;
  supports_location_filter: boolean;
  supports_opening_rank: boolean;
}

export interface CollegeFilterMetadataResponse {
  path: PathSummaryDTO;
  filters: FilterSchemaDTO[];
  generated_at: string;
}

export interface BandPageRequest {
  safe: number;
  moderate: number;
  hard: number;
  suggested: number;
}

export interface ProbabilityEvidenceDTO {
  round_evidence_score: string;
  round_stability_score: string;
  current_year_presence_score: string;
  is_cold_start: boolean;
  is_projected_current_round: boolean;
}

export interface ComparisonContextDTO {
  metric_type: MetricType;
  user_score: string;
  current_round_cutoff_value: string;
  margin_value: string;
  qualified_against_current_anchor: boolean;
}

export interface CollegeCardDTO {
  college_id: UUID;
  college_name: string;
  institute_code: string;
  exam_code: string;

  path_id: UUID;
  path_key: string;

  program_code: string;
  program_name: string;

  branch_option_key: string | null;
  branch_display_name: string | null;

  seat_bucket_code: string;

  category_name: string | null;
  course_type: string | null;
  location_type: string | null;
  reservation_type: string | null;
  gender: string | null;

  city: string | null;
  district: string | null;
  state_code: string | null;
  pincode: string | null;

  logo_url: string | null;
  hero_storage_key: string | null;
  hero_media_url?: string | null;
  
  current_round_cutoff_value: string;
  opening_rank: number | null;

  probability_percent: string;
  band: CollegeBand;

  evidence: ProbabilityEvidenceDTO;
  comparison: ComparisonContextDTO;

  latest_year_available: number;
  latest_round_available: number;
  comparison_year: number;
  comparison_round_number: number;
  live_round_number: number;
}

export interface BandPaginationDTO {
  page: number;
  page_size: number;
  total_matching_count: number;
  capped_total_available: number;
  has_next_page: boolean;
  cap_reached: boolean;
}

export interface BandResultDTO {
  band: CollegeBand;
  items: CollegeCardDTO[];
  pagination: BandPaginationDTO;
}

export interface SearchBandsDTO {
  safe: BandResultDTO;
  moderate: BandResultDTO;
  hard: BandResultDTO;
  suggested: BandResultDTO;
}

export interface BandCountsDTO {
  safe: number;
  moderate: number;
  hard: number;
  suggested: number;
}

export interface CollegeFilterSearchResponse {
  path: PathSummaryDTO;
  user_score: string;
  total_matching_count: number;
  band_counts: BandCountsDTO;
  bands: SearchBandsDTO;
  generated_at: string;
}

export interface CollegeFilterSearchRequest {
  path_id: UUID;
  score: string;
  filters: Record<string, unknown>;
  page_size: number;
  page_by_band: BandPageRequest;
  sort_mode: SortMode;
}