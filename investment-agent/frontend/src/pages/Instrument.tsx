import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, enc } from "../api";
import { Badge, Card, Change, DemoBanner, Empty, ErrorNote, PriceChart, SafeHtml, sentimentTone, Spinner, Tabs, useAsync } from "../components";
import { ago, CLASS_LABEL, compact, money, num, pct, priceDigits } from "../format";
import type { Chart, Instrument, NewsItem, Quote } from "../types";

type Signal = { name: string; effect: string; text: string };
type Technical = {
  available: boolean; reason?: string; score: number; stance: string; signals: Signal[]; as_of: string;
  indicators: Record<string, number | null>; returns_pct: Record<string, number | null>;
  high_52w: number; low_52w: number; from_52w_high_pct: number; volatility_annual_pct: number; max_drawdown_1y_pct: number;
  levels: { support: number[]; resistance: number[] };
};
type Valuation = { available: boolean; reason?: string; method?: string; fair_value?: { bear: number; base: number; bull: number }; upside_pct?: number; assumptions?: Record<string, number> };
type Fundamental = {
  available: boolean; reason?: string; kind?: string; name?: string; sector?: string; industry?: string; summary?: string;
  metrics?: Record<string, number | string | null>; scores?: Record<string, number>; valuation?: Valuation; next_earnings?: string[];
  category?: string; fund_house?: string; expense_ratio_pct?: number | null;
};
type Fund = {
  available: boolean; nav: number; as_of: string; returns_pct: Record<string, number | null>;
  rolling_1y: { min: number; median: number; max: number; positive_pct: number } | null;
  rolling_3y: { min: number; median: number; max: number; positive_pct: number } | null;
  risk: Record<string, number | null>; benchmark?: { name: string; returns_pct: Record<string, number | null> };
};
type Analysis = {
  instrument: Instrument; quote: Quote; technical: Technical; fundamental: Fundamental; fund?: Fund; chart: Chart;
  news: NewsItem[]; position: Record<string, number | string | null> | null;
  latest_report: { id: number; verdict: string; html: string; ai_generated: boolean; created_at: string } | null; demo: boolean;
};

type Tab = "overview" | "fundamentals" | "news" | "report";
const METRIC_LABELS: [string, string, "pct" | "x" | "num" | "money"][] = [
  ["pe", "P/E", "x"], ["forward_pe", "Forward P/E", "x"], ["pb", "P/B", "x"], ["ev_ebitda", "EV/EBITDA", "x"],
  ["peg", "PEG", "x"], ["dividend_yield_pct", "Dividend yield", "pct"], ["roe_pct", "ROE", "pct"], ["roa_pct", "ROA", "pct"],
  ["net_margin_pct", "Net margin", "pct"], ["operating_margin_pct", "Operating margin", "pct"],
  ["revenue_growth_pct", "Revenue growth (yoy)", "pct"], ["earnings_growth_pct", "Earnings growth (yoy)", "pct"],
  ["revenue_cagr_pct", "Revenue CAGR (3y)", "pct"], ["debt_to_equity", "Debt / equity", "x"], ["current_ratio", "Current ratio", "x"],
  ["interest_coverage", "Interest cover", "x"], ["beta", "Beta", "num"], ["analyst_target_mean", "Analyst target (mean)", "money"],
];

export default function InstrumentPage() {
  const { symbol = "" } = useParams();
  const nav = useNavigate();
  const [tab, setTab] = useState<Tab>("overview");
  const [period, setPeriod] = useState<"3mo" | "6mo" | "1y" | "2y" | "5y">("1y");
  const a = useAsync(() => api.get<Analysis>(`/instruments/${enc(symbol)}/analysis`), [symbol]);
  const [chart, setChart] = useState<Chart | null>(null);
  const [report, setReport] = useState<Analysis["latest_report"]>(null);
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState<unknown>();
  const [inst, setInst] = useState<Instrument | null>(null);

  useEffect(() => {
    if (a.data) {
      setChart(a.data.chart);
      setReport(a.data.latest_report);
      setInst(a.data.instrument);
    }
  }, [a.data]);
  useEffect(() => {
    if (!a.data) return;
    if (period === "2y") {
      setChart(a.data.chart);
      return;
    }
    api.get<Chart>(`/instruments/${enc(symbol)}/chart?period=${period}`).then(setChart).catch(() => {});
  }, [period, a.data, symbol]);

  if (a.loading) return <div className="page"><Spinner label="Analysing" /></div>;
  if (a.error || !a.data) return <div className="page"><ErrorNote error={a.error} /><Link to="/">Back</Link></div>;
  const d = a.data;
  const q = d.quote;
  const ccy = q.currency || d.instrument.currency;
  const t = d.technical;
  const f = d.fundamental;

  const act = async (label: string, fn: () => Promise<void>) => {
    setBusy(label);
    setErr(undefined);
    try {
      await fn();
    } catch (e) {
      setErr(e);
    } finally {
      setBusy("");
    }
  };
  const togglePin = () => act("pin", async () => setInst(await api.patch<Instrument>(`/instruments/${enc(symbol)}`, { pinned: !inst?.pinned })));
  const unfollow = () => act("unfollow", async () => {
    await api.del(`/instruments/${enc(symbol)}`);
    nav("/");
  });
  const setAlert = () => act("alert", async () => {
    const v = window.prompt("Alert me when the daily move is at least (%) — leave empty for the default", inst?.alert_pct?.toString() ?? "");
    if (v === null) return;
    const body = v.trim() === "" ? { clear_alert_pct: true } : { alert_pct: Number(v) };
    setInst(await api.patch<Instrument>(`/instruments/${enc(symbol)}`, body));
  });
  const makeReport = () => act("report", async () => {
    setTab("report");
    setReport(await api.post<NonNullable<Analysis["latest_report"]>>(`/instruments/${enc(symbol)}/report`));
  });
  const refreshNews = () => act("news", async () => {
    await api.post(`/instruments/${enc(symbol)}/refresh-news`);
    a.reload();
  });
  const ask = () => nav(`/chat?q=${encodeURIComponent(`Give me your full view on ${d.instrument.name} (${d.instrument.symbol}). Should I buy, hold or sell?`)}`);

  const tabs: { id: Tab; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "fundamentals", label: d.fund ? "Fund" : "Fundamentals" },
    { id: "news", label: `News (${d.news.length})` },
    { id: "report", label: "AI research note" },
  ];

  return (
    <div className="page">
      <DemoBanner show={d.demo} />
      <div className="inst-head">
        <div>
          <div className="muted small">{d.instrument.symbol} · {CLASS_LABEL[d.instrument.asset_class] ?? d.instrument.asset_class}{d.instrument.exchange ? ` · ${d.instrument.exchange}` : ""}</div>
          <h1>{d.instrument.name}</h1>
          <div className="price-line">
            <span className="price">{money(q.price, ccy, priceDigits(q.price))}</span>
            <Change v={q.change_pct} />
            {q.change !== null && <span className="muted">{q.change > 0 ? "+" : ""}{num(q.change, priceDigits(q.price))}</span>}
            {q.as_of && <span className="muted small">as of {ago(q.as_of)}</span>}
          </div>
        </div>
        <div className="inst-actions">
          <button className="btn primary" onClick={ask}>Ask the adviser</button>
          <button className="btn" onClick={makeReport} disabled={!!busy}>{busy === "report" ? "Writing note…" : "AI research note"}</button>
          <button className="btn ghost" onClick={togglePin} aria-pressed={inst?.pinned}>{inst?.pinned ? "★ Pinned" : "☆ Pin"}</button>
          <button className="btn ghost" onClick={setAlert}>Alert {inst?.alert_pct ? `±${inst.alert_pct}%` : "(default)"}</button>
          <button className="btn ghost danger" onClick={unfollow} title="Stop following">Unfollow</button>
        </div>
      </div>
      <ErrorNote error={err} />

      <Card>
        <div className="period-row">
          {(["3mo", "6mo", "1y", "2y", "5y"] as const).map((p) => (
            <button key={p} className={`chip ${period === p ? "active" : ""}`} onClick={() => setPeriod(p)}>{p}</button>
          ))}
        </div>
        {chart && <PriceChart chart={chart} />}
      </Card>

      {d.position && (
        <Card title="Your position">
          <div className="kpis">
            <Kpi label="Quantity" value={num(d.position.quantity as number, (d.position.quantity as number) % 1 ? 4 : 0)} />
            <Kpi label="Avg cost" value={money(d.position.avg_cost as number, ccy)} />
            <Kpi label="Value" value={money(d.position.value as number, "INR", 0)} />
            <Kpi label="P&L" value={money(d.position.pnl as number, "INR", 0)} sub={pct(d.position.pnl_pct as number)} tone={(d.position.pnl as number) >= 0 ? "up" : "down"} />
            <Kpi label="XIRR" value={pct(d.position.xirr_pct as number, 1, false)} />
            <Kpi label="Weight" value={pct(d.position.weight_pct as number, 1, false)} />
          </div>
        </Card>
      )}

      <Tabs tabs={tabs} value={tab} onChange={setTab} />

      {tab === "overview" && (
        <div className="grid-2">
          <Card title="Technical picture" actions={t.available && <Badge tone={t.stance === "bullish" ? "good" : t.stance === "bearish" ? "bad" : "neutral"}>{t.stance} · {t.score > 0 ? "+" : ""}{t.score}</Badge>}>
            {!t.available ? <Empty>{t.reason}</Empty> : (
              <>
                <ul className="signals">
                  {t.signals.map((s) => <li key={s.name} className={s.effect}><strong>{s.name}:</strong> {s.text}</li>)}
                </ul>
                <div className="levels">
                  <div><span className="muted small">Support</span> {t.levels.support.map((l) => num(l)).join(" · ") || "–"}</div>
                  <div><span className="muted small">Resistance</span> {t.levels.resistance.map((l) => num(l)).join(" · ") || "–"}</div>
                </div>
              </>
            )}
          </Card>
          <Card title="Key numbers">
            {t.available && (
              <table className="kv">
                <tbody>
                  <tr><td>Returns 1w / 1m / 3m</td><td>{pct(t.returns_pct["1w"])} · {pct(t.returns_pct["1m"])} · {pct(t.returns_pct["3m"])}</td></tr>
                  <tr><td>Returns 6m / 1y</td><td>{pct(t.returns_pct["6m"])} · {pct(t.returns_pct["1y"])}</td></tr>
                  <tr><td>52-week range</td><td>{num(t.low_52w)} – {num(t.high_52w)} ({pct(t.from_52w_high_pct)} from high)</td></tr>
                  <tr><td>RSI(14) / MACD</td><td>{t.indicators.rsi14 ?? "–"} / {t.indicators.macd ?? "–"}</td></tr>
                  <tr><td>50d / 200d average</td><td>{num(t.indicators.sma50)} / {num(t.indicators.sma200)}</td></tr>
                  <tr><td>Volatility (1y, annual)</td><td>{pct(t.volatility_annual_pct, 1, false)}</td></tr>
                  <tr><td>Max drawdown (1y)</td><td>{pct(t.max_drawdown_1y_pct, 1)}</td></tr>
                  <tr><td>ATR(14)</td><td>{num(t.indicators.atr14)} ({pct(t.indicators.atr_pct, 1, false)})</td></tr>
                  {q.market_cap ? <tr><td>Market cap</td><td>{compact(q.market_cap, ccy)}</td></tr> : null}
                </tbody>
              </table>
            )}
          </Card>
        </div>
      )}

      {tab === "fundamentals" && (d.fund ? <FundView fund={d.fund} f={f} /> : <CompanyView f={f} ccy={ccy} price={q.price} />)}

      {tab === "news" && (
        <Card title="News" actions={<button className="btn small" onClick={refreshNews} disabled={!!busy}>{busy === "news" ? "Fetching…" : "Fetch latest"}</button>}>
          {d.news.length === 0 && <Empty>No stored news yet. Fetch the latest, or wait for the next digest run.</Empty>}
          <NewsList items={d.news} />
        </Card>
      )}

      {tab === "report" && (
        <Card title="AI research note" actions={report && <span className="muted small">{ago(report.created_at)}</span>}>
          {busy === "report" && <Spinner label="The analyst is writing (30–60 seconds)" />}
          {!report && busy !== "report" && <Empty>No note yet. <button className="link-btn" onClick={makeReport}>Write one now</button>.</Empty>}
          {report && busy !== "report" && (
            <>
              {report.verdict && <div className="verdict">Verdict: <strong>{report.verdict}</strong></div>}
              <SafeHtml html={report.html} />
              <p className="muted small">Personal analysis, not advice from a SEBI-registered investment adviser.</p>
            </>
          )}
        </Card>
      )}
    </div>
  );
}

function Kpi({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: "up" | "down" }) {
  return (
    <div className="kpi">
      <span className="kpi-label">{label}</span>
      <span className={`kpi-value ${tone ?? ""}`}>{value}</span>
      {sub && <span className={`small ${tone ?? ""}`}>{sub}</span>}
    </div>
  );
}

function CompanyView({ f, ccy, price }: { f: Fundamental; ccy: string; price: number | null }) {
  if (!f.available) return <Card><Empty>{f.reason}</Empty></Card>;
  const v = f.valuation;
  const m = f.metrics ?? {};
  const fmt = (val: number | string | null | undefined, kind: string) =>
    val === null || val === undefined ? "–" : typeof val === "string" ? val : kind === "pct" ? pct(val, 1, false) : kind === "money" ? money(val, ccy) : kind === "x" ? `${num(val, 2)}x` : num(val, 2);
  return (
    <div className="grid-2">
      <Card title="Scores">
        {f.scores && (
          <div className="scores">
            {Object.entries(f.scores).map(([k, s]) => (
              <div key={k} className="score">
                <span className="kpi-label">{k}</span>
                <div className="score-track"><div className={`score-fill ${s >= 65 ? "good" : s >= 45 ? "mid" : "bad"}`} style={{ width: `${s}%` }} /></div>
                <span className="num">{s}</span>
              </div>
            ))}
          </div>
        )}
        {f.sector && <p className="muted small">{f.sector} · {f.industry}</p>}
        {f.summary && <p className="small">{f.summary}</p>}
        {f.next_earnings && f.next_earnings.length > 0 && <p className="small">Next results: <strong>{f.next_earnings[0]}</strong></p>}
      </Card>
      <Card title="Fair value (model)">
        {!v?.available ? <Empty>{v?.reason}</Empty> : (
          <>
            <div className="fv">
              {(["bear", "base", "bull"] as const).map((k) => (
                <div key={k} className={`fv-cell ${k}`}>
                  <span className="kpi-label">{k}</span>
                  <span className="kpi-value">{money(v.fair_value![k], ccy)}</span>
                </div>
              ))}
            </div>
            {v.upside_pct !== undefined && price !== null && <p>Base case vs price: <Change v={v.upside_pct} digits={1} /></p>}
            <p className="muted small">{v.method}. {Object.entries(v.assumptions ?? {}).map(([k, val]) => `${k.replace(/_/g, " ")}: ${typeof val === "number" ? num(val, val > 1000 ? 0 : 1) : val}`).join(" · ")}</p>
          </>
        )}
      </Card>
      <Card title="Ratios" className="span-2">
        <div className="metric-grid">
          {METRIC_LABELS.map(([k, label, kind]) => (
            <div key={k} className="metric">
              <span className="kpi-label">{label}</span>
              <span className="num">{fmt(m[k] as number | null, kind)}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function FundView({ fund, f }: { fund: Fund; f: Fundamental }) {
  if (!fund.available) return <Card><Empty>Not enough history.</Empty></Card>;
  return (
    <div className="grid-2">
      <Card title="Returns">
        <table className="kv">
          <tbody>
            <tr><td></td><td><strong>Fund</strong></td>{fund.benchmark && <td><strong>{fund.benchmark.name}</strong></td>}</tr>
            {(["1y", "3y_cagr", "5y_cagr"] as const).map((k) => (
              <tr key={k}><td>{k.replace("_cagr", " CAGR")}</td><td>{pct(fund.returns_pct[k])}</td>{fund.benchmark && <td>{pct(fund.benchmark.returns_pct[k])}</td>}</tr>
            ))}
          </tbody>
        </table>
        {f.category && <p className="muted small">{f.category}{f.fund_house ? ` · ${f.fund_house}` : ""}{f.expense_ratio_pct ? ` · expense ratio ${f.expense_ratio_pct}%` : ""}</p>}
      </Card>
      <Card title="Risk">
        <table className="kv">
          <tbody>
            {Object.entries(fund.risk).map(([k, v]) => <tr key={k}><td>{k.replace(/_/g, " ")}</td><td>{v ?? "–"}</td></tr>)}
          </tbody>
        </table>
      </Card>
      {(fund.rolling_1y || fund.rolling_3y) && (
        <Card title="Rolling returns" className="span-2">
          <table className="kv">
            <tbody>
              <tr><td></td><td>Worst</td><td>Median</td><td>Best</td><td>% positive</td></tr>
              {fund.rolling_1y && <tr><td>1-year</td><td>{pct(fund.rolling_1y.min)}</td><td>{pct(fund.rolling_1y.median)}</td><td>{pct(fund.rolling_1y.max)}</td><td>{fund.rolling_1y.positive_pct}%</td></tr>}
              {fund.rolling_3y && <tr><td>3-year (annualised)</td><td>{pct(fund.rolling_3y.min)}</td><td>{pct(fund.rolling_3y.median)}</td><td>{pct(fund.rolling_3y.max)}</td><td>{fund.rolling_3y.positive_pct}%</td></tr>}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}

export function NewsList({ items }: { items: NewsItem[] }) {
  return (
    <ul className="news">
      {items.map((n) => (
        <li key={n.id}>
          <a href={n.url} target="_blank" rel="noopener noreferrer">{n.title}</a>
          <div className="news-meta">
            <span className="muted small">{n.source} · {ago(n.published_at)}</span>
            {n.impact && <Badge tone={n.impact === "high" ? "bad" : n.impact === "medium" ? "warn" : "neutral"}>{n.impact} impact</Badge>}
            {n.sentiment && <Badge tone={sentimentTone(n.sentiment)}>{n.sentiment}</Badge>}
            {n.symbols.slice(0, 3).map((s) => <Link key={s} to={`/instrument/${enc(s)}`} className="sym">{s}</Link>)}
          </div>
          {n.summary && n.summary !== n.title && <p className="small">{n.summary}</p>}
        </li>
      ))}
    </ul>
  );
}
