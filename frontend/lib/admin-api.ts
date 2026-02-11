import { apiClient } from "./api-client";

// ... (Type Definitions remain the same) ...
export interface Artifact {
  id: string;
  pdf_path: string;
  exam_code: string;
  year: number;
  round_name: string;
  round_number?: number;
  status: "PENDING" | "APPROVED" | "INGESTED" | "FAILED";
  requires_reprocessing: boolean;
  created_at: string;
  review_notes?: string;
}

export interface Candidate {
  candidate_id: number;
  raw_name: string;
  source_document: string; 
  reason_flagged: string;
  status: "pending" | "resolved";
  ingestion_run_id: string;
}

export interface RegistryCollege {
  college_id: string;
  canonical_name: string;
  state_code: string;
  aliases: string[];
}

export interface DashboardStats {
  airlock_pending: number;
  triage_pending: number;
  registry_total: number;
  seat_policy_pending: number;
}

export interface ExamConfig {
  exam_code: string;
  is_active: boolean;
  ingestion_mode: "BOOTSTRAP" | "CONTINUOUS";
  last_updated: string;
}

export interface SeatPolicyViolation {
  id: string;
  exam_code: string;
  seat_bucket_code: string;
  violation_type: string;
  source_year: number;
  source_round: number | null;
  source_file: string | null;
  raw_row: Record<string, any>;
  status: 'OPEN' | 'RESOLVED' | 'IGNORED';
  created_at: string;
}

export interface AdminUser {
  id: string;
  username: string;
  email: string;
  role: "SUPERADMIN" | "EDITOR" | "VIEWER";
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface AuditLog {
  id: string;
  admin_username: string;
  action: string;
  target_resource: string | null;
  details: any;
  ip_address: string | null;
  created_at: string;
}

// --- DOMAIN 1: INGESTION (AIRLOCK) ---

export const fetchArtifacts = async (): Promise<Artifact[]> => {
  const res = await apiClient.get("/ingestion/artifacts");
  return res.data;
};

export const triggerDirtyIngestion = async () => {
  const res = await apiClient.post("/ingestion/apply-dirty");
  return res.data;
};

// --- DOMAIN 2: IDENTITY (TRIAGE) ---

export const fetchCandidates = async (): Promise<Candidate[]> => {
  const res = await apiClient.get("/identity/candidates");
  return res.data;
};

// [FIX] Removed userEmail parameter to match Backend Phase 1
export const linkCandidate = async (candidateIds: number[], targetUuid: string) => {
  const res = await apiClient.post("/identity/link", { 
    candidate_ids: candidateIds, 
    target_registry_uuid: targetUuid
    // user_email is now extracted from JWT on backend
  });
  return res.data;
};

// [FIX] Removed userEmail parameter
export const promoteNewCollege = async (candidateIds: number[], officialName: string) => {
  const res = await apiClient.post("/identity/promote-new", { 
    candidate_ids: candidateIds, 
    official_name: officialName
  });
  return res.data;
};

// --- DOMAIN 3: REGISTRY ---

export const fetchRegistry = async (): Promise<RegistryCollege[]> => {
  const res = await apiClient.get("/registry/colleges");
  return res.data;
};

export const updateCanonicalName = async (collegeId: string, newName: string) => {
  const res = await apiClient.post("/registry/promote-alias", { 
    college_id: collegeId, 
    alias_text: newName 
  });
  return res.data;
};

// --- DOMAIN 4: CONFIGURATION (DASHBOARD) ---

export const fetchDashboardStats = async (): Promise<DashboardStats> => {
  const res = await apiClient.get("/config/dashboard-stats");
  return res.data;
};

export const fetchExamConfigs = async (): Promise<ExamConfig[]> => {
  const res = await apiClient.get("/config/exams");
  return res.data;
};

export const updateExamMode = async (examCode: string, mode: "BOOTSTRAP" | "CONTINUOUS") => {
  const res = await apiClient.patch(`/config/exams/${examCode}/mode`, { 
    ingestion_mode: mode 
  });
  return res.data;
};

// --- DOMAIN 5: SEAT POLICY (NEW) ---

export const fetchPendingSeatViolations = async (skip = 0, limit = 50): Promise<SeatPolicyViolation[]> => {
  const res = await apiClient.get(`/admin/triage/seat-policy/pending`, { 
    params: { skip, limit } 
  });
  return res.data;
};

export const promoteSeatBucket = async (violationId: string) => {
  const res = await apiClient.post(`/admin/triage/seat-policy/${violationId}/promote`);
  return res.data;
};

export const ignoreSeatBucket = async (violationId: string) => {
  const res = await apiClient.post(`/admin/triage/seat-policy/${violationId}/ignore`);
  return res.data;
};

export const approveBatchArtifacts = async (artifactIds: string[]) => {
  const res = await apiClient.post("/ingestion/approve-batch", { 
    artifact_ids: artifactIds 
  });
  return res.data;
};

export const fetchIngestionStatus = async () => {
  try {
    const res = await apiClient.get("/ingestion/status");
    return res.data as { is_ingesting: boolean };
  } catch (e) {
    return { is_ingesting: false };
  }
};

// --- DOMAIN 6: TEAM MANAGEMENT (SUPER ADMIN) ---

export const fetchAdmins = async (): Promise<AdminUser[]> => {
  const res = await apiClient.get("/admin/users/");
  return res.data;
};

export const createAdmin = async (data: { username: string; email: string; password: string; role: string }) => {
  const res = await apiClient.post("/admin/users/", data);
  return res.data;
};

export const updateAdmin = async (id: string, data: { role?: string; is_active?: boolean; password?: string }) => {
  const res = await apiClient.patch(`/admin/users/${id}`, data);
  return res.data;
};

export const deleteAdmin = async (id: string) => {
  const res = await apiClient.delete(`/admin/users/${id}`);
  return res.data;
};

// --- DOMAIN 7: AUDIT LOGS ---

export const fetchAuditLogs = async (skip = 0, limit = 100): Promise<AuditLog[]> => {
  const res = await apiClient.get("/admin/audit/", { params: { skip, limit } });
  return res.data;
};