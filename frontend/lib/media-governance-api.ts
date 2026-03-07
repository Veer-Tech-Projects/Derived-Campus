import { apiClient } from "./api-client";

// ============================================================
// 1. STRICT TYPE CONTRACTS (Matches Pydantic & SQLAlchemy Models)
// ============================================================

export type GovernanceMediaType = "LOGO" | "CAMPUS_HERO";
export type GovernanceMediaStatus = "PENDING" | "ACCEPTED" | "REJECTED" | "DELETED";
export type GovernanceDerivedState = "EMPTY" | "PENDING" | "ACCEPTED" | "EXHAUSTED" | "GRAVEYARD";
export type GovernanceTriageAction = "ACCEPT" | "REJECT" | "DELETE";

export interface TriageTarget {
  collegeId: string;
  collegeName: string;
  mediaId: string;
  mediaType: GovernanceMediaType;
  sourceUrl: string;
}

export interface MediaDetailState {
  media_id: string | null;
  status: GovernanceMediaStatus | null;
  exhausted: boolean;
  source_url: string | null;
}

export interface GovernanceCollege {
  college_id: string;
  canonical_name: string;
  city: string | null;
  derived_state: GovernanceDerivedState;
  media_details: {
    LOGO: MediaDetailState;
    CAMPUS_HERO: MediaDetailState;
  };
}

export interface PaginatedGovernanceResponse {
  total_count: number;
  data: GovernanceCollege[];
}

export interface DispatchResponse {
  message: string;
  media_type: GovernanceMediaType;
}

export interface TriageResponse {
  message: string;
  media_id: string;
}

// ============================================================
// 2. API WRAPPERS (Utilizing Centralized Axios Client)
// ============================================================

export const fetchGovernanceColleges = async (
  skip: number = 0,
  limit: number = 50,
  search?: string
): Promise<PaginatedGovernanceResponse> => {
  const params = new URLSearchParams({
    skip: skip.toString(),
    limit: limit.toString(),
  });
  
  if (search) {
    params.append("search", search);
  }

  const res = await apiClient.get(`/admin/media-governance/colleges?${params.toString()}`);
  return res.data;
};

export const dispatchMediaIngestion = async (
  collegeId: string,
  mediaType: GovernanceMediaType,
  force: boolean = false
): Promise<DispatchResponse> => {
  const res = await apiClient.post("/admin/media-governance/dispatch", {
    college_id: collegeId,
    media_type: mediaType,
    force: force,
  });
  return res.data;
};

export const triageMediaCandidate = async (
  collegeId: string,
  mediaId: string,
  action: GovernanceTriageAction
): Promise<TriageResponse> => {
  const res = await apiClient.post(`/admin/media-governance/triage/${collegeId}`, {
    media_id: mediaId,
    action: action,
  });
  return res.data;
};


export interface IngestionStatusResponse {
  is_ingesting: boolean;
  active_tasks: number;
}

export interface BulkDispatchSummary {
  queued: number;
  skipped_locked: number;
  skipped_exhausted: number;
  errors: number;
}

export const fetchMediaIngestionStatus = async (): Promise<IngestionStatusResponse> => {
  const res = await apiClient.get("/admin/media-governance/status");
  return res.data;
};

export const dispatchBulkMediaIngestion = async (
  collegeIds: string[],
  force: boolean = false
): Promise<BulkDispatchSummary> => {
  const res = await apiClient.post("/admin/media-governance/dispatch-batch", {
    college_ids: collegeIds,
    force: force,
  });
  return res.data;
};