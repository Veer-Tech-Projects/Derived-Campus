import { apiClient } from "./api-client";

export type LocationDerivedState = "EMPTY" | "PENDING" | "ACCEPTED" | "EXHAUSTED";
export type LocationTriageAction = "ACCEPT" | "REJECT" | "DELETE";

export interface LocationCandidate {
  candidate_id: string;
  raw_address: string;
  latitude: number | null;
  longitude: number | null;
  pincode: string | null;
  parsed_city: string | null;
  parsed_district: string | null;
  parsed_state_code: string | null;
}

export interface GovernanceLocation {
  college_id: string;
  canonical_name: string;
  registry_city: string | null;
  registry_state_code: string | null;
  derived_state: LocationDerivedState;
  canonical_address: string | null;
  candidate_details: LocationCandidate | null;
}

export interface PaginatedLocationResponse {
  total_count: number;
  data: GovernanceLocation[];
}

export interface LocationIngestionStatusResponse {
  is_ingesting: boolean;
  active_tasks: number;
}

export interface LocationBulkDispatchSummary {
  queued: number;
  skipped_locked: number;
  skipped_exhausted: number;
  errors: number;
}

export const fetchLocationColleges = async (
  skip: number = 0,
  limit: number = 50,
  search?: string,
  status?: string // [NEW] Added status parameter
): Promise<PaginatedLocationResponse> => {
  const params = new URLSearchParams({
    skip: skip.toString(),
    limit: limit.toString(),
  });
  if (search) params.append("search", search);
  if (status && status !== "ALL") params.append("status", status); // [NEW]

  const res = await apiClient.get(`/admin/location-governance/colleges?${params.toString()}`);
  return res.data;
};

export const dispatchLocationIngestion = async (collegeId: string, force: boolean = false) => {
  const res = await apiClient.post("/admin/location-governance/dispatch", {
    college_id: collegeId,
    force: force,
  });
  return res.data;
};

export const triageLocationCandidate = async (
  collegeId: string,
  action: LocationTriageAction,
  candidateId?: string | null,
  overrides?: { city?: string; district?: string; state_code?: string; pincode?: string }
) => {
  const res = await apiClient.post(`/admin/location-governance/triage/${collegeId}`, {
    candidate_id: candidateId,
    action: action,
    ...overrides
  });
  return res.data;
};

export const fetchLocationIngestionStatus = async (): Promise<LocationIngestionStatusResponse> => {
  const res = await apiClient.get("/admin/location-governance/status");
  return res.data;
};

export const dispatchBulkLocationIngestion = async (
  collegeIds: string[],
  force: boolean = false
): Promise<LocationBulkDispatchSummary> => {
  const res = await apiClient.post("/admin/location-governance/dispatch-batch", {
    college_ids: collegeIds,
    force: force,
  });
  return res.data;
};