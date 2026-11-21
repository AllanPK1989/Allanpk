import DOMPurify from "dompurify";
import { marked } from "marked";
import { type ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { pct } from "./format";
import type { Chart } from "./types";

export function Change({ v, digits = 2, className = "" }: { v: number | null | undefined; digits?: number; className?: string }) {
  const cls = v === null || v === undefined ? "flat" : v > 0 ? "up" : v < 0 ? "down" : "flat";
  return <span className={`chg ${cls} ${className}`}>{pct(v, digits)}</span>;
}

export function Card({ title, actions, children, className = "" }: { title?: ReactNode; actions?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`card ${className}`}>
      {(title || actions) && (
        <header className="card-head">
          {title && <h2>{title}</h2>}
          {actions && <div className="card-actions">{actions}</div>}
        </header>
      )}
      {children}
    </section>
  );
}

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className="spinner" role="status">
      <span className="dot" />
      <span>{label}…</span>
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>;
}

export function ErrorNote({ error }: { error: unknown }) {
  if (!error) return null;
  return <div className="error-note">{error instanceof Error ? error.message : String(error)}</div>;
}

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "good" | "bad" | "warn" | "info" }) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

export function DemoBanner({ show }: { show: boolean }) {
  if (!show) return null;
  return <div className="demo-banner">Demo data: prices, fundamentals and news are made up.</div>;
}

export function Tabs<T extends string>({ tabs, value, onChange }: { tabs: { id: T; label: string }[]; value: T; onChange: (t: T) => void }) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((t) => (
        <button key={t.id} role="tab" aria-selected={value === t.id} className={value === t.id ? "active" : ""} onClick={() => onChange(t.id)}>
          {t.label}
        </button>
      ))}
    </div>
  );
}

/** Render markdown from the model safely (sanitised in the browser too). */
export function Markdown({ text }: { text: string }) {
  const html = useMemo(() => {
    const raw = marked.parse(text || "", { async: false, gfm: true, breaks: false }) as string;
    return DOMPurify.sanitize(raw, { ADD_ATTR: ["target"] });
  }, [text]);
  return <div className="prose" dangerouslySetInnerHTML={{ __html: html }} />;
}

/** Server-rendered HTML (already sanitised server-side; sanitised again here). */
export function SafeHtml({ html }: { html: string }) {
  const clean = useMemo(() => DOMPurify.sanitize(html), [html]);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.querySelectorAll("a[href^='http']").forEach((a) => {
      a.setAttribute("target", "_blank");
      a.setAttribute("rel", "noopener noreferrer");
    });
  }, [clean]);
  return <div ref={ref} className="prose" dangerouslySetInnerHTML={{ __html: clean }} />;
}

export function sentimentTone(s: string): "good" | "bad" | "warn" | "neutral" {
  return s === "positive" ? "good" : s === "negative" ? "bad" : s === "mixed" ? "warn" : "neutral";
}

/** Price line with 50/200-day averages. Pure SVG, scales to its container. */
export function PriceChart({ chart, height = 240 }: { chart: Chart; height?: number }) {
  const [hover, setHover] = useState<number | null>(null);
  const wrap = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(640);
  useEffect(() => {
    const el = wrap.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setWidth(el.clientWidth || 640));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const n = chart.close.length;
  if (n < 2) return <Empty>No price history.</Empty>;
  const vals = [...chart.close, ...chart.sma50, ...chart.sma200].filter((v): v is number => v !== null);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const pad = { l: 8, r: 56, t: 10, b: 22 };
  const w = Math.max(280, width);
  const x = (i: number) => pad.l + (i / (n - 1)) * (w - pad.l - pad.r);
  const y = (v: number) => pad.t + (1 - (v - min) / (max - min || 1)) * (height - pad.t - pad.b);
  const path = (s: (number | null)[]) => {
    let d = "";
    s.forEach((v, i) => {
      if (v === null) return;
      d += `${d && s[i - 1] !== null ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`;
    });
    return d;
  };
  const first = chart.close.find((v) => v !== null) ?? 0;
  const last = chart.close[n - 1] ?? 0;
  const up = last >= first;
  const area = `${path(chart.close)} L${x(n - 1)},${height - pad.b} L${x(0)},${height - pad.b} Z`;
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => min + f * (max - min));
  const hi = hover ?? n - 1;
  const onMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    const i = Math.round(((e.clientX - r.left - pad.l) / (w - pad.l - pad.r)) * (n - 1));
    setHover(Math.max(0, Math.min(n - 1, i)));
  };
  return (
    <div ref={wrap} className="chart">
      <div className="chart-legend">
        <span>{chart.dates[hi]}</span>
        <strong>{chart.close[hi]?.toLocaleString("en-IN", { maximumFractionDigits: 2 })}</strong>
        <span className="lg sma50">50d {chart.sma50[hi]?.toLocaleString("en-IN", { maximumFractionDigits: 2 }) ?? "–"}</span>
        <span className="lg sma200">200d {chart.sma200[hi]?.toLocaleString("en-IN", { maximumFractionDigits: 2 }) ?? "–"}</span>
      </div>
      <svg width={w} height={height} onPointerMove={onMove} onPointerLeave={() => setHover(null)} role="img" aria-label="Price chart">
        <defs>
          <linearGradient id="area" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor={up ? "var(--up)" : "var(--down)"} stopOpacity="0.22" />
            <stop offset="100%" stopColor={up ? "var(--up)" : "var(--down)"} stopOpacity="0" />
          </linearGradient>
        </defs>
        {ticks.map((t, i) => (
          <g key={i}>
            <line x1={pad.l} x2={w - pad.r} y1={y(t)} y2={y(t)} className="grid" />
            <text x={w - pad.r + 6} y={y(t) + 4} className="axis">{t.toLocaleString("en-IN", { maximumFractionDigits: t < 10 ? 2 : 0 })}</text>
          </g>
        ))}
        <path d={area} fill="url(#area)" />
        <path d={path(chart.sma200)} className="line sma200" />
        <path d={path(chart.sma50)} className="line sma50" />
        <path d={path(chart.close)} className={`line price ${up ? "up" : "down"}`} />
        <line x1={x(hi)} x2={x(hi)} y1={pad.t} y2={height - pad.b} className="cursor" />
        {chart.close[hi] !== null && <circle cx={x(hi)} cy={y(chart.close[hi] as number)} r={3.5} className={`pt ${up ? "up" : "down"}`} />}
        <text x={pad.l} y={height - 6} className="axis">{chart.dates[0]}</text>
        <text x={w - pad.r} y={height - 6} className="axis" textAnchor="end">{chart.dates[n - 1]}</text>
      </svg>
    </div>
  );
}

/** Horizontal bars for allocation-style data. */
export function Bars({ rows }: { rows: { label: string; value: number; target?: number }[] }) {
  const max = Math.max(100, ...rows.map((r) => Math.max(r.value, r.target ?? 0)));
  return (
    <div className="bars">
      {rows.map((r) => (
        <div className="bar-row" key={r.label}>
          <div className="bar-label">{r.label}</div>
          <div className="bar-track">
            <div className="bar-fill" style={{ width: `${(r.value / max) * 100}%` }} />
            {r.target !== undefined && <div className="bar-target" style={{ left: `${(r.target / max) * 100}%` }} title={`Target ${r.target}%`} />}
          </div>
          <div className="bar-val">
            {r.value.toFixed(1)}%{r.target !== undefined && <small> / {r.target}%</small>}
          </div>
        </div>
      ))}
    </div>
  );
}

export function useAsync<T>(fn: () => Promise<T>, deps: unknown[]): { data: T | undefined; error: unknown; loading: boolean; reload: () => void } {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<unknown>();
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(undefined);
    fn()
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  return { data, error, loading, reload: () => setTick((t) => t + 1) };
}
