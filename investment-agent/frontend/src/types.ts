export interface Quote {
  symbol: string;
  price: number | null;
  prev_close: number | null;
  change: number | null;
  change_pct: number | null;
  currency: string;
  day_high?: number | null;
  day_low?: number | null;
  volume?: number | null;
  year_high?: number | null;
  year_low?: number | null;
  market_cap?: number | null;
  as_of?: string | null;
}

export interface Instrument {
  id: number;
  symbol: string;
  name: string;
  asset_class: string;
  region: string;
  exchange: string;
  currency: string;
  followed: boolean;
  pinned: boolean;
  source: string;
  alert_pct: number | null;
  meta: Record<string, unknown>;
  quote?: Quote | null;
  held?: boolean;
}

export interface SearchResult {
  symbol: string;
  name: string;
  asset_class: string;
  region: string;
  exchange: string;
  currency: string;
  meta: Record<string, unknown>;
}

export interface NewsItem {
  id: number;
  title: string;
  url: string;
  source: string;
  published_at: string;
  summary: string;
  sentiment: string;
  impact: string;
  category: string;
  scope: string;
  symbols: string[];
}

export interface MarketRow {
  symbol: string;
  label: string;
  group: string;
  price: number | null;
  change_pct: number | null;
}

export interface Overview {
  markets: MarketRow[];
  rates: { id: string; label: string; value: number; date: string }[];
  demo: boolean;
}

export interface Holding {
  symbol: string;
  name: string;
  asset_class: string;
  bucket: string;
  currency: string;
  quantity: number;
  price: number | null;
  avg_cost: number | null;
  value: number | null;
  invested: number;
  pnl: number | null;
  pnl_pct: number | null;
  day_change: number;
  day_change_pct: number | null;
  realized: number;
  xirr_pct: number | null;
  weight_pct: number;
  open: boolean;
}

export interface Portfolio {
  holdings: Holding[];
  totals: {
    value: number;
    invested: number;
    pnl: number;
    pnl_pct: number | null;
    day_change: number;
    day_change_pct?: number | null;
    realized: number;
    xirr_pct: number | null;
  };
  allocation: Record<string, number>;
  concentration?: { hhi: number; effective_holdings: number; top5_pct: number; largest: string; largest_pct: number };
  demo: boolean;
  note?: string;
}

export interface Status {
  app: string;
  demo: boolean;
  ai: boolean;
  email: boolean;
  push: boolean;
  models: { analysis: string; news: string };
  jobs: Record<string, { status: string; started_at: string; finished_at: string | null }>;
  push_subscriptions: number;
}

export interface DigestSummary {
  id: number;
  kind: string;
  title: string;
  created_at: string;
  ai_generated: boolean;
  emailed: boolean;
  pushed: boolean;
}

export interface Chart {
  dates: string[];
  close: (number | null)[];
  sma50: (number | null)[];
  sma200: (number | null)[];
}

export type Settings = {
  risk_profile: "conservative" | "moderate" | "aggressive";
  horizon_years: number;
  age: number | null;
  tax_slab_pct: number;
  ltcg_exemption_used: number;
  risk_free_pct: number;
  rbi_repo_rate_pct: number | null;
  alert_pct: number;
  alert_pct_crypto: number;
  email_digests: boolean;
  email_alerts: boolean;
  push_digests: boolean;
  push_alerts: boolean;
  digests_enabled: { morning: boolean; evening: boolean; weekly: boolean };
  goals_notes: string;
};
