// Shared request/response types between is-scoping-backend and the Next.js frontend.
// Generated from FastAPI endpoint contracts — keep in sync with backend/main.py.

// ── /search ──────────────────────────────────────────────────────
// Note: search_accounts() returns Snowflake column names in UPPER_CASE.

export interface AccountResult {
  ACCOUNT_ID: string;
  ACCOUNT_NAME: string;
  INDUSTRY?: string;
  SALES_SEGMENT?: string;
  EMPLOYEE_COUNT?: number;
  ACCOUNT_FAMILY_MRR?: number;
  CUSTOMER_TIER?: string;
}

// ── /accounts/select ─────────────────────────────────────────────

export interface SelectAccountRequest {
  account: AccountResult;  // full row from /search — sent back to avoid re-query
}

// ── /lookup ──────────────────────────────────────────────────────

export interface SfData {
  accountName: string;
  accountId?: string;
  opportunityId?: string;
  accountFamilyMRR?: number;
  ddProducts?: string[];
  prefill: Record<string, string | string[]>;
}

// ── /diagnose ────────────────────────────────────────────────────

export interface DiagnoseRequest {
  answers: Record<string, string | string[]>;
}

export interface DiagnosisField {
  value: string;
  triggers: Array<[string, string]>;
}

export interface Diagnosis {
  shape: DiagnosisField;
  motion: DiagnosisField;
  binding_constraints: DiagnosisField[];
  triggers: Array<{ signal: string; value: string; contributed_to: string[] }>;
  customer_ownership: string[];
}

export interface Flag {
  t: "blk" | "wrn" | "inf" | "ok";
  m: string;
}

export interface DiagnoseResponse {
  diagnosis: Diagnosis;
  recommendation: {
    key: string;
    sMin: number | null;
    sMax: number | null;
  };
  flags: Flag[];
  next_steps: string[];
  service_motion: string;
}

// ── /scoping/governed_handoff ───────────────────────────────────

export interface GovernedHandoffRequest {
  org_id: string;
  engagement_id?: string;
  answers: Record<string, string | string[]>;
  sf_data?: SfData;
  scoping_summary?: string;
}

export interface GovernedHandoffResponse {
  target_mcp: "dd-governed-onboarding-mcp";
  tool: "initialize_engagement";
  arguments: {
    org_id: string;
    engagement_id: string;
    products_in_scope: string[];
    engagement_type: string;
    session_count: number | null;
    source_opportunity_id: string;
    scoping_summary: string;
    scoping_payload: Record<string, unknown>;
  };
  next_tool: "batch_submit_intake";
  notes: string[];
}

// ── /prose ───────────────────────────────────────────────────────

export interface ProseRequest {
  diagnosis: Diagnosis;
  answers: Record<string, string | string[]>;
}

export interface ProseResponse {
  diagnosis_paragraph: string | null;
  consequence_paragraph: string | null;
}

// ── /phase1/motions ──────────────────────────────────────────────

export interface Motion {
  label: string;
  ask: string;
  desc: string;
  icon: string;
}

export type MotionsResponse = Record<string, Motion>;

// ── /phase1/estimate ─────────────────────────────────────────────

export interface EstimateRequest {
  motion: string;
  answers: Record<string, string | string[]>;
}

export interface EstimateResponse {
  days_min: number | null;
  days_max: number | null;
  pm_required: boolean;
  label?: string;  // present only for Resident Architect (no numeric range)
}
