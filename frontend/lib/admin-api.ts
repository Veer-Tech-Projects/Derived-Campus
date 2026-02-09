// frontend/lib/admin-api.ts

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// --- TYPE DEFINITIONS ---

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

// [NEW] Seat Policy Types
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

// --- DOMAIN 1: INGESTION (AIRLOCK) ---

export const fetchArtifacts = async (): Promise<Artifact[]> => {
  const res = await fetch(`${API_BASE}/ingestion/artifacts`, { cache: 'no-store' });
  if (!res.ok) throw new Error("Failed to fetch artifacts");
  return res.json();
};

export const triggerDirtyIngestion = async () => {
  const res = await fetch(`${API_BASE}/ingestion/apply-dirty`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Failed to trigger ingestion");
  return res.json();
};

// --- DOMAIN 2: IDENTITY (TRIAGE) ---

export const fetchCandidates = async (): Promise<Candidate[]> => {
  const res = await fetch(`${API_BASE}/identity/candidates`, { cache: 'no-store' });
  if (!res.ok) throw new Error("Failed to fetch candidates");
  return res.json();
};

export const linkCandidate = async (candidateIds: number[], targetUuid: string, userEmail: string) => {
  const res = await fetch(`${API_BASE}/identity/link`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ candidate_ids: candidateIds, target_registry_uuid: targetUuid, user_email: userEmail }),
  });
  if (!res.ok) throw new Error("Link failed");
  return res.json();
};

export const promoteNewCollege = async (candidateIds: number[], officialName: string, userEmail: string) => {
  const res = await fetch(`${API_BASE}/identity/promote-new`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ candidate_ids: candidateIds, official_name: officialName, user_email: userEmail }),
  });
  if (!res.ok) throw new Error("Promotion failed");
  return res.json();
};

// --- DOMAIN 3: REGISTRY ---

export const fetchRegistry = async (): Promise<RegistryCollege[]> => {
  const res = await fetch(`${API_BASE}/registry/colleges`, { cache: 'no-store' });
  if (!res.ok) throw new Error("Failed to fetch registry");
  return res.json();
};

export const updateCanonicalName = async (collegeId: string, newName: string) => {
  const res = await fetch(`${API_BASE}/registry/promote-alias`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ college_id: collegeId, alias_text: newName }),
  });
  if (!res.ok) throw new Error("Update failed");
  return res.json();
};

// --- DOMAIN 4: CONFIGURATION (DASHBOARD) ---

export const fetchDashboardStats = async (): Promise<DashboardStats> => {
  const res = await fetch(`${API_BASE}/config/dashboard-stats`, { cache: 'no-store' });
  if (!res.ok) throw new Error("Failed to fetch stats");
  return res.json();
};

export const fetchExamConfigs = async (): Promise<ExamConfig[]> => {
  const res = await fetch(`${API_BASE}/config/exams`, { cache: 'no-store' });
  if (!res.ok) throw new Error("Failed to fetch exams");
  return res.json();
};

export const updateExamMode = async (examCode: string, mode: "BOOTSTRAP" | "CONTINUOUS") => {
  const res = await fetch(`${API_BASE}/config/exams/${examCode}/mode`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ingestion_mode: mode }),
  });
  if (!res.ok) throw new Error("Failed to update mode");
  return res.json();
};

// --- DOMAIN 5: SEAT POLICY (NEW) ---

export const fetchPendingSeatViolations = async (skip = 0, limit = 50): Promise<SeatPolicyViolation[]> => {
  const res = await fetch(`${API_BASE}/admin/triage/seat-policy/pending?skip=${skip}&limit=${limit}`, { 
    cache: 'no-store' 
  });
  if (!res.ok) throw new Error("Failed to fetch violations");
  return res.json();
};

export const promoteSeatBucket = async (violationId: string) => {
  const res = await fetch(`${API_BASE}/admin/triage/seat-policy/${violationId}/promote`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Promotion failed");
  return res.json();
};

export const ignoreSeatBucket = async (violationId: string) => {
  const res = await fetch(`${API_BASE}/admin/triage/seat-policy/${violationId}/ignore`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Ignore failed");
  return res.json();
};



export const approveBatchArtifacts = async (artifactIds: string[]) => {
  const res = await fetch(`${API_BASE}/ingestion/approve-batch`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ artifact_ids: artifactIds }),
  });
  if (!res.ok) throw new Error("Batch approval failed");
  return res.json();
};


export const fetchIngestionStatus = async () => {
  const res = await fetch(`${API_BASE}/ingestion/status`);
  if (!res.ok) return { is_ingesting: false };
  return res.json() as Promise<{ is_ingesting: boolean }>;
};