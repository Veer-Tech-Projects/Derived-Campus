import {
  BandPageRequest,
  CollegeFilterSearchRequest,
  SortMode,
  UUID,
} from "../types/contracts";

export const COLLEGE_FILTER_DEFAULT_PAGE_SIZE = 10;

export const COLLEGE_FILTER_DEFAULT_BAND_PAGES: BandPageRequest = Object.freeze({
  safe: 1,
  moderate: 1,
  hard: 1,
  suggested: 1,
});

export const COLLEGE_FILTER_DEFAULT_SORT_MODE: SortMode = "best_fit";

type BuildSearchRequestArgs = {
  finalPathId: UUID;
  score: string;
  filters: Record<string, string>;
  pageByBand?: BandPageRequest;
  pageSize?: number;
  sortMode?: SortMode;
};

export function buildCollegeFilterSearchRequest({
  finalPathId,
  score,
  filters,
  pageByBand = COLLEGE_FILTER_DEFAULT_BAND_PAGES,
  pageSize = COLLEGE_FILTER_DEFAULT_PAGE_SIZE,
  sortMode = COLLEGE_FILTER_DEFAULT_SORT_MODE,
}: BuildSearchRequestArgs): CollegeFilterSearchRequest {
  return {
    path_id: finalPathId,
    score,
    filters,
    page_size: pageSize,
    page_by_band: pageByBand,
    sort_mode: sortMode,
  };
}