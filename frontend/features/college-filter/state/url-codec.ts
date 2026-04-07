import { BandPageRequest, CollegeBand, UUID } from "../types/contracts";

export type CollegeFilterUrlState = {
  rootPathId: UUID | null;
  educationType: string | null;
  finalPathId: UUID | null;
  score: string;
  filters: Record<string, string>;
  activeBand: CollegeBand | null;
  pageByBand: BandPageRequest;
  applied: boolean;
};

const DEFAULT_PAGE_BY_BAND: BandPageRequest = {
  safe: 1,
  moderate: 1,
  hard: 1,
  suggested: 1,
};

const RESERVED_KEYS = new Set([
  "rootPathId",
  "educationType",
  "finalPathId",
  "score",
  "activeBand",
  "safePage",
  "moderatePage",
  "hardPage",
  "suggestedPage",
  "applied",
]);

function normalizeString(value: string | null | undefined): string {
  return typeof value === "string" ? value.trim() : "";
}

function parsePositiveInteger(value: string | null | undefined, fallback: number): number {
  const raw = normalizeString(value);
  if (!raw) return fallback;

  const parsed = Number(raw);
  if (!Number.isInteger(parsed) || parsed < 1) return fallback;

  return parsed;
}

function isCollegeBand(value: string | null | undefined): value is CollegeBand {
  return value === "SAFE" || value === "MODERATE" || value === "HARD" || value === "SUGGESTED";
}

export function decodeCollegeFilterUrlState(
  searchParams: URLSearchParams
): CollegeFilterUrlState {
  const rootPathId = normalizeString(searchParams.get("rootPathId")) || null;
  const educationType = normalizeString(searchParams.get("educationType")) || null;
  const finalPathId = normalizeString(searchParams.get("finalPathId")) || null;
  const score = normalizeString(searchParams.get("score"));

  const activeBandRaw = normalizeString(searchParams.get("activeBand"));
  const activeBand = isCollegeBand(activeBandRaw) ? activeBandRaw : null;

  const applied = searchParams.get("applied") === "1";

  const filters: Record<string, string> = {};
  for (const [key, value] of searchParams.entries()) {
    if (RESERVED_KEYS.has(key)) continue;

    const normalized = normalizeString(value);
    if (!normalized) continue;

    filters[key] = normalized;
  }

  return {
    rootPathId,
    educationType,
    finalPathId,
    score,
    filters,
    activeBand,
    pageByBand: {
      safe: parsePositiveInteger(searchParams.get("safePage"), DEFAULT_PAGE_BY_BAND.safe),
      moderate: parsePositiveInteger(
        searchParams.get("moderatePage"),
        DEFAULT_PAGE_BY_BAND.moderate
      ),
      hard: parsePositiveInteger(searchParams.get("hardPage"), DEFAULT_PAGE_BY_BAND.hard),
      suggested: parsePositiveInteger(
        searchParams.get("suggestedPage"),
        DEFAULT_PAGE_BY_BAND.suggested
      ),
    },
    applied,
  };
}

export function encodeCollegeFilterUrlState(
  state: CollegeFilterUrlState
): URLSearchParams {
  const params = new URLSearchParams();

  if (state.rootPathId) {
    params.set("rootPathId", state.rootPathId);
  }

  if (state.educationType) {
    params.set("educationType", state.educationType);
  }

  if (state.finalPathId) {
    params.set("finalPathId", state.finalPathId);
  }

  if (normalizeString(state.score)) {
    params.set("score", state.score);
  }

  if (state.activeBand) {
    params.set("activeBand", state.activeBand);
  }

  if (state.pageByBand.safe > 1) {
    params.set("safePage", String(state.pageByBand.safe));
  }

  if (state.pageByBand.moderate > 1) {
    params.set("moderatePage", String(state.pageByBand.moderate));
  }

  if (state.pageByBand.hard > 1) {
    params.set("hardPage", String(state.pageByBand.hard));
  }

  if (state.pageByBand.suggested > 1) {
    params.set("suggestedPage", String(state.pageByBand.suggested));
  }

  if (state.applied) {
    params.set("applied", "1");
  }

  const filterEntries = Object.entries(state.filters).sort(([a], [b]) =>
    a.localeCompare(b)
  );

  for (const [key, value] of filterEntries) {
    const normalized = normalizeString(value);
    if (!normalized) continue;

    params.set(key, normalized);
  }

  return params;
}

export function areBandPagesEqual(a: BandPageRequest, b: BandPageRequest): boolean {
  return (
    a.safe === b.safe &&
    a.moderate === b.moderate &&
    a.hard === b.hard &&
    a.suggested === b.suggested
  );
}