const CURRENCY_SYMBOL: Record<string, string> = { INR: "₹", USD: "$", EUR: "€", GBP: "£", JPY: "¥", HKD: "HK$" };

/** Indian-style grouping for INR (1,23,456), western elsewhere. */
export function num(v: number | null | undefined, digits = 2, currency = ""): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  const locale = currency === "INR" || currency === "" ? "en-IN" : "en-US";
  return v.toLocaleString(locale, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function money(v: number | null | undefined, currency = "INR", digits = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  const sym = CURRENCY_SYMBOL[currency] ?? (currency ? `${currency} ` : "");
  return `${v < 0 ? "−" : ""}${sym}${num(Math.abs(v), digits, currency)}`;
}

/** ₹12.3 L / ₹4.5 Cr for large rupee amounts. */
export function compactInr(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  const a = Math.abs(v);
  const sign = v < 0 ? "−" : "";
  if (a >= 1e12) return `${sign}₹${num(a / 1e12, 2)} lakh Cr`;
  if (a >= 1e10) return `${sign}₹${num(a / 1e7, 0)} Cr`;
  if (a >= 1e7) return `${sign}₹${(a / 1e7).toFixed(2)} Cr`;
  if (a >= 1e5) return `${sign}₹${(a / 1e5).toFixed(2)} L`;
  return `${sign}₹${num(a, 0)}`;
}

export function compact(v: number | null | undefined, currency = ""): string {
  if (v === null || v === undefined) return "–";
  if (currency === "INR") return compactInr(v);
  const a = Math.abs(v);
  const s = CURRENCY_SYMBOL[currency] ?? "";
  if (a >= 1e12) return `${s}${(v / 1e12).toFixed(2)}T`;
  if (a >= 1e9) return `${s}${(v / 1e9).toFixed(2)}B`;
  if (a >= 1e6) return `${s}${(v / 1e6).toFixed(2)}M`;
  return `${s}${num(v, 0, "USD")}`;
}

export function pct(v: number | null | undefined, digits = 2, signed = true): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  return `${signed && v > 0 ? "+" : ""}${v.toFixed(digits)}%`;
}

export function priceDigits(v: number | null | undefined): number {
  if (v === null || v === undefined) return 2;
  const a = Math.abs(v);
  return a >= 1000 ? 2 : a >= 1 ? 2 : 4;
}

export function ago(iso: string | null | undefined): string {
  if (!iso) return "";
  const t = new Date(iso).getTime();
  const s = Math.max(0, (Date.now() - t) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  if (s < 86400 * 7) return `${Math.floor(s / 86400)}d ago`;
  return new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
}

export function when(iso: string): string {
  return new Date(iso).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

export const CLASS_LABEL: Record<string, string> = {
  stock: "Stock", etf: "ETF", mutual_fund: "Mutual fund", crypto: "Crypto", index: "Index", commodity: "Commodity",
  forex: "FX", bond: "Bond / yield",
};

export const BUCKET_LABEL: Record<string, string> = {
  equity_india: "Indian equity", equity_global: "Global equity", debt: "Debt", gold: "Gold & silver", crypto: "Crypto",
  commodities: "Commodities", cash: "Cash / FX", hybrid: "Hybrid",
};
