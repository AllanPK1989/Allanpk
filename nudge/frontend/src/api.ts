// Thin client for the Nudge API (see /api/docs on the server).

export type Lane = "inbox" | "today" | "upcoming" | "waiting" | "overdue" | "done";
export type Priority = "high" | "normal" | "low";

export interface Basket {
  id: number;
  name: string;
  color: string;
  icon: string;
  position: number;
  archived: boolean;
  open?: number;
}

export interface ShortTask {
  id: number;
  title: string;
  basket: Basket | null;
  status: "open" | "waiting" | "done" | "dropped";
  priority: Priority;
  lane: Lane;
  overdue: boolean;
  due_date: string | null;
  due_time: string | null;
  person: string;
  waiting_days: number | null;
  focus: boolean;
  repeat_label: string;
  age_days: number;
  checklist_done: number;
  checklist_total?: number;
  closed_at: string | null;
  ai_fields: string[];
  inbox: boolean;
  next_nudge_at: string | null;
  nudge_count: number;
}

export interface Task extends ShortTask {
  notes: string;
  basket_id: number | null;
  remind_at: string | null;
  waiting_since: string | null;
  nudge_every_days: number | null;
  repeat_rule: string;
  source: string;
  transcript: string;
  follows_task_id: number | null;
  checklist: { id: number; text: string; done: boolean }[];
  closing_note: string;
  created_at: string;
  updated_at: string;
  last_activity_at: string;
  history?: { at: string; kind: string; detail: Record<string, unknown> }[];
  follows?: { id: number; title: string; status: string } | null;
  followed_by?: { id: number; title: string; status: string }[];
}

export interface BasketTile {
  basket: Basket;
  open: number;
  overdue: number;
  waiting: number;
  due_today: number;
  oldest_days: number;
  cleared_30: number;
  cleared_pct: number;
}

export interface RadarGroup {
  person: string;
  count: number;
  oldest_days: number;
  items: ShortTask[];
}

export interface Dashboard {
  greeting: string;
  today: string;
  kpis: { overdue: number; due_today: number; waiting: number; closed_week: number };
  lanes: Record<Exclude<Lane, "done">, number>;
  closed_today: number;
  focus: ShortTask[];
  today_list: ShortTask[];
  baskets: BasketTile[];
  radar: RadarGroup[];
  aging: { label: string; count: number }[];
  trend: { week_start: string; created: number; closed: number }[];
  stale: ShortTask[];
  stale_count: number;
  open_total: number;
}

export interface Briefing {
  kind: "briefing";
  greeting: string;
  date: string;
  text: string;
  overdue: ShortTask[];
  due_today: ShortTask[];
  focus: ShortTask[];
  nudges: ShortTask[];
  waiting_count: number;
  stale: ShortTask[];
  inbox_count: number;
}

export interface Wrapup {
  kind: "wrapup";
  date: string;
  text: string;
  closed_today: ShortTask[];
  carried: ShortTask[];
  due_tomorrow: ShortTask[];
  weekly_review_ready: boolean;
}

export interface Review {
  week_start: string;
  week_end: string;
  offset: number;
  closed_count: number;
  created_count: number;
  dropped_count: number;
  closed: ShortTask[];
  by_day: { date: string; closed: number }[];
  by_basket: { name: string; count: number }[];
  slipped: ShortTask[];
  oldest: ShortTask[];
  waiting_longest: ShortTask[];
  stale: ShortTask[];
  next_week_count: number;
  open_total: number;
}

export interface Person {
  person: string;
  waiting: ShortTask[];
  open: ShortTask[];
  recent_done: ShortTask[];
  oldest_waiting_days: number;
}

export interface Draft {
  title: string;
  notes: string;
  basket_id: number | null;
  basket: Basket | null;
  due_date: string | null;
  due_time: string | null;
  priority: Priority;
  person: string;
  waiting: boolean;
  repeat_rule: string;
  repeat_label: string;
  checklist: string[];
  guessed: string[];
}

export interface Interpretation {
  transcript: string;
  intent: "create" | "complete" | "reschedule" | "query" | "unclear";
  drafts: Draft[];
  targets: { task_id: number; title: string; due_date: string | null; due_time: string | null }[];
  answer: string;
  matches: ShortTask[];
  understood_by: "claude" | "rules";
  warning: string;
  saved?: Task[];
}

export interface Settings {
  display_name: string;
  timezone: string;
  briefing_time: string;
  wrapup_time: string;
  overdue_nag_time: string;
  nudge_time: string;
  quiet_start: string;
  quiet_end: string;
  stale_days: number;
  default_nudge_days: number;
  digest_email: string;
  email_briefing: boolean;
  email_wrapup: boolean;
  push_reminders: boolean;
  push_nudges: boolean;
  push_briefing: boolean;
  push_wrapup: boolean;
  push_overdue: boolean;
}

export interface SystemStatus {
  version: string;
  demo: boolean;
  ai: { provider: string; model: string; calls_this_month: number; failed_this_month: number; cost_usd_this_month: number; avg_latency_ms: number };
  voice: { provider: string; ready: boolean; model?: string };
  email_configured: boolean;
  outbox: { name: string; size: number }[];
  push_devices: number;
  backups: { name: string; size: number }[];
}

export interface SettingsResponse {
  settings: Settings;
  status: SystemStatus;
  recent_notifications: { at: string; kind: string; channel: string; title: string; delivered: number; error: string }[];
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export class OfflineError extends Error {
  constructor() {
    super("You're offline");
  }
}

let onUnauthorized: () => void = () => {};
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn;
}

async function request<T>(method: string, path: string, body?: unknown, form?: FormData): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, {
      method,
      credentials: "same-origin",
      headers: {
        ...(method !== "GET" ? { "X-Nudge": "1" } : {}),
        ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      },
      body: form ?? (body !== undefined ? JSON.stringify(body) : undefined),
    });
  } catch {
    throw new OfflineError();
  }
  if (res.status === 401 && !path.startsWith("/api/auth/")) {
    onUnauthorized();
  }
  if (!res.ok) {
    let msg = res.statusText || "Something went wrong";
    try {
      const data = await res.json();
      if (typeof data.detail === "string") msg = data.detail;
      else if (Array.isArray(data.detail) && data.detail[0]?.msg) msg = data.detail[0].msg;
    } catch {
      /* not JSON */
    }
    throw new ApiError(res.status, msg);
  }
  const type = res.headers.get("content-type") || "";
  return (type.includes("application/json") ? res.json() : res.text()) as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body ?? {}),
  patch: <T>(path: string, body: unknown) => request<T>("PATCH", path, body),
  del: <T>(path: string) => request<T>("DELETE", path),
  upload: <T>(path: string, form: FormData) => request<T>("POST", path, undefined, form),
};

export function errorText(e: unknown): string {
  if (e instanceof ApiError || e instanceof OfflineError) return e.message;
  return "Something went wrong. Please try again.";
}
