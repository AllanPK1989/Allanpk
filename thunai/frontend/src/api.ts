// Thin client for the Thunai REST API (see /api/docs on the server).
import type { Lang } from "./i18n";

export type Role = "technician" | "supervisor" | "admin";

export interface User {
  id: number;
  employee_id: string;
  name: string;
  role: Role;
  zone: string;
  preferred_language: Lang;
  skill_level: string;
  phone: string;
  active: boolean;
  locked: boolean;
  entra_upn?: string; // Microsoft account for the Copilot agent (SPEC 13.3)
  entra_linked?: boolean; // bound on the person's first use in Teams
}

export interface Machine {
  id: number;
  machine_no: string;
  name: string;
  machine_type: string;
  zone: string;
  line: string;
  make: string;
  model: string;
  plc_model: string;
  key_components: string;
  criticality: string;
  status: string;
  qr_code: string;
  notes: string;
  active: boolean;
  components?: { id: number; name: string; category: string; part_no: string; location: string }[];
}

export interface LogText {
  original: string;
  original_lang: string;
  en: string;
  ta: string;
  ai_filled: boolean;
  unsure: boolean;
}

export type TextField = "issue" | "root_cause" | "corrective_action";

export interface Log {
  id: number;
  log_no: string;
  machine_no: string;
  machine_name: string;
  zone: string;
  shift: string;
  shift_date: string | null;
  reported_at: string;
  start_at: string | null;
  end_at: string | null;
  downtime_min: number | null;
  alarm_code: string;
  status: "draft" | "open" | "closed" | "verified" | "rejected";
  source: string;
  escalated: boolean;
  needs_confirmation: boolean;
  technician_id: number | null;
  technician_name: string;
  verified_by: string | null;
  reject_reason: string;
  ai_session_id: number | null;
  texts: Record<TextField, LogText>;
  parts?: { part_no: string; description: string; qty: number }[];
  media?: { id: number; kind: string; transcript: string; available: boolean }[];
  classification?: { symptom_category: string; component_name: string; failure_mode: string } | null;
}

export interface FaultCard {
  id: number;
  ref: string;
  symptom: string;
  symptom_ta: string;
  causes: { cause: string; cause_ta?: string; count: number }[];
  steps_en: string[];
  steps_ta: string[];
  parts: string[];
  tools: string[];
  avg_fix_min: number | null;
  version: number;
  status: "draft" | "approved" | "needs_review" | "rejected" | "retired";
  review_note: string;
  replaces_id: number | null;
  history: { version: number; symptom: string; steps_en: string[]; archived_at: string }[];
  source_log_ids: number[];
  flagged_log_ids: number[];
  parts_stock?: PartInfo[];
  // detail view
  scope?: "machine" | "type";
  scope_name?: string;
  machine_no?: string | null;
  source_logs?: Log[];
  flagged_logs?: Log[];
}

export interface KPI {
  breakdowns: number;
  downtime_min: number;
  mttr_min: number | null;
  mtbf_h: number | null;
  period_days: number;
}

export interface MachinePage {
  machine: Machine;
  open_logs: Log[];
  timeline: Log[];
  top_faults: { symptom: string; symptom_ta: string; count: number; last: string; avg_downtime_min: number | null }[];
  fault_cards: FaultCard[];
  kpi: KPI;
  tips: Tip[];
  documents: DocumentInfo[];
  spare_parts: PartInfo[];
  active_alarm: MachineAlarm | null;
  alarms_24h: { code: string; count: number; first: string; last: string; message: string; active: boolean }[];
}

/** A spare part as the stores system last reported it (Phase 3). */
export interface PartInfo {
  part_no: string;
  description: string;
  unit: string;
  stock_qty: number | null;
  min_qty: number | null;
  location: string;
  stock_at: string | null;
  low: boolean;
  alt_part_nos: string[];
}

/** An alarm from the PLC/SCADA feed; `meaning` comes from the alarm list. */
export interface MachineAlarm {
  id: number;
  machine_no: string;
  code: string;
  message: string;
  raised_at: string;
  cleared_at: string | null;
  source: string;
  meaning: Alarm | null;
}

/** What the Copilot agent read from a photo sent in Teams (SPEC 13.1). */
export interface PhotoObservation {
  usable: boolean;
  shows_en?: string;
  readings?: { label: string; value: string; unit: string; legible: boolean }[];
  screen_text?: string;
  alarm_codes?: string[];
  damage_en?: string;
}

export interface Tip {
  id: number;
  ref: string;
  machine_no: string;
  machine_name: string;
  author: string;
  original: string;
  en: string;
  ta: string;
  status: "pending" | "approved" | "rejected";
  reject_reason: string;
  created_at: string;
}

export interface DocumentInfo {
  id: number;
  active?: boolean;
  title: string;
  kind: string;
  pages: number;
  status: string;
  scope: "machine" | "type";
  machine_no: string | null;
  type_name: string;
  mime: string;
  created_at: string;
}

export interface Alarm {
  code: string;
  message: string;
  cause: string;
  remedy: string;
}

export interface Evidence {
  items: {
    ref: string;
    kind: "fault_card" | "log" | "tip" | "doc" | "alarm" | "scada" | "photo";
    tier: number;
    label: string;
    machine_no: string;
    when: string;
    text_en: string;
    data: Record<string, string | number | boolean | null | { cause: string; cause_ta?: string; count: number }[]>;
  }[];
  logs_this_machine: number;
  last_date: string;
  fault_cards: string[];
  general: boolean;
}

export interface Step {
  step_no: number;
  kind: "safety" | "check" | "action";
  action_en: string;
  action_ta: string;
  check_en: string;
  check_ta: string;
  expected_result_en: string;
  expected_result_ta: string;
  tools: string[];
  safety_note_en: string;
  safety_note_ta: string;
  authorised_only: boolean;
  if_ok_next: number;
  if_not_ok_next: number;
  source_refs: string[];
  confidence: number;
  general: boolean;
  injected: boolean;
  evidence: Evidence;
  parts?: PartInfo[];
}

export interface Question {
  id: string;
  text_en: string;
  text_ta: string;
  options: { value: string; label_en: string; label_ta: string }[];
  answer: string | null;
}

export interface Session {
  id: number;
  machine_no: string;
  machine_name: string;
  language: Lang;
  problem_text: string;
  alarm_code: string;
  questions: Question[];
  steps: Step[];
  step_responses: { step_no: number; response: string }[];
  procedure: {
    summary_en?: string;
    summary_ta?: string;
    likely_causes?: { cause_en: string; cause_ta: string; likelihood: number; source_refs: string[] }[];
    confidence?: number;
    low_confidence?: boolean;
    no_history?: boolean;
    refused?: boolean;
    refuse_reason_en?: string;
    refuse_reason_ta?: string;
    call_supervisor?: boolean;
    error?: string;
  };
  outcome: "in_progress" | "resolved" | "escalated" | "refused" | "failed" | "abandoned";
  feedback: string;
  resulting_log_id: number | null;
  channel?: "app" | "copilot";
  photos?: { media_id: number }[]; // PWA photos: attachments only
  observations?: PhotoObservation[];
}

export interface Supervisor {
  name: string;
  phone: string;
  zone: string;
}

export interface Meta {
  app: string;
  version: string;
  copilot?: { enabled: boolean; teams_url: string };
  stt_provider: string;
}

/** Skill-gap analytics (Phase 3). Null figures: fewer events than min_events. */
export interface Skills {
  days: number;
  zone: string;
  min_events: number;
  technicians: {
    key: string;
    name: string;
    employee_id: string;
    zone: string;
    in_thunai: boolean;
    fixes: number;
    verified: number;
    median_downtime_min: number | null;
    vs_team: number | null;
    sessions: number;
    escalated: number;
    escalation_pct: number | null;
    cant_do: number;
    cant_do_authorised: number;
    tips: number;
    machine_types: string[];
  }[];
  types: string[];
  matrix: { key: string; name: string; cells: Record<string, number> }[];
  machine_types: {
    name: string;
    breakdowns: number;
    fixers: number;
    fixer_names: string[];
    median_downtime_min: number | null;
    sessions: number;
    escalation_pct: number | null;
  }[];
  suggestions: { kind: "single_person" | "pair" | "authorisation"; machine_type: string | null; technician: string | null; partner: string | null; text_en: string }[];
}

export interface CopilotUsage {
  days: number;
  enabled: boolean;
  ready: boolean;
  tenant_set: boolean;
  audience_set: boolean;
  scope: string;
  teams_url: string;
  users_active: number;
  users_with_account: number;
  users_linked: number;
  sessions_by_channel: Record<string, number>;
  calls: number;
  by_tool: { operation: string; calls: number; ok: number; users: number; last_at: string | null }[];
  recent_errors: { at: string; operation: string; status_code: number; error: string }[];
}

export interface IntegrationKey {
  id: number;
  name: string;
  key_prefix: string;
  scopes: string[];
  active: boolean;
  last_used_at: string | null;
  created_at: string;
  token?: string;
}
export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

/** Network down (as opposed to a server error): the caller may queue the work offline. */
export class OfflineError extends Error {}

let token: string | null = null;
let onUnauthorized: () => void = () => {};

export function setToken(value: string | null) {
  token = value;
}

export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn;
}

async function request<T>(method: string, path: string, body?: unknown, raw = false): Promise<T> {
  const headers: Record<string, string> = {};
  if (token) headers.authorization = `Bearer ${token}`;
  let payload: BodyInit | undefined;
  if (body instanceof FormData) payload = body;
  else if (body !== undefined) {
    headers["content-type"] = "application/json";
    payload = JSON.stringify(body);
  }
  let response: Response;
  try {
    response = await fetch(path, { method, headers, body: payload });
  } catch {
    throw new OfflineError("offline");
  }
  if (response.status === 401 && token) onUnauthorized();
  if (!response.ok) {
    let detail: unknown = undefined;
    try {
      detail = (await response.json()).detail;
    } catch {
      /* not JSON */
    }
    const message =
      typeof detail === "string"
        ? detail
        : detail && typeof detail === "object" && "message" in detail
          ? String((detail as { message: string }).message)
          : `HTTP ${response.status}`;
    throw new ApiError(response.status, message, detail);
  }
  if (raw) return (await response.blob()) as T;
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body ?? {}),
  patch: <T>(path: string, body: unknown) => request<T>("PATCH", path, body),
  put: <T>(path: string, body: unknown) => request<T>("PUT", path, body),
  blob: (path: string) => request<Blob>("GET", path, undefined, true),
  upload: <T>(path: string, form: FormData) => request<T>("POST", path, form),
};

export async function downloadFile(path: string, filename: string) {
  const blob = await api.blob(path);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

/** Opens an authenticated file (manual, drawing) in a new tab. */
export async function openFile(path: string) {
  const win = window.open("", "_blank");
  const blob = await api.blob(path);
  const url = URL.createObjectURL(blob);
  if (win) win.location.href = url;
  else window.location.href = url;
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}
