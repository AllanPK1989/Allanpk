import { type FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { api, enc } from "../api";
import { Bars, Card, Change, DemoBanner, Empty, ErrorNote, Spinner, Tabs, useAsync } from "../components";
import { BUCKET_LABEL, compactInr, money, num, pct, priceDigits } from "../format";
import type { Portfolio } from "../types";

type Tab = "holdings" | "risk" | "tax" | "rebalance" | "trades";
type Tx = { id: number; symbol: string; name: string; side: string; quantity: number; price: number; trade_date: string; fees: number; fx_rate: number | null; note: string };

export default function PortfolioPage() {
  const [tab, setTab] = useState<Tab>("holdings");
  const pf = useAsync(() => api.get<Portfolio>("/portfolio"), []);
  const reb = useAsync(() => api.get<RebalancePlan>("/portfolio/rebalance"), [pf.data]);
  const t = pf.data?.totals;
  return (
    <div className="page">
      <DemoBanner show={!!pf.data?.demo} />
      <h1>Portfolio</h1>
      {pf.loading && <Spinner />}
      <ErrorNote error={pf.error} />
      {t && (
        <div className="kpis wide">
          <div className="kpi big"><span className="kpi-label">Value</span><span className="kpi-value">{compactInr(t.value)}</span></div>
          <div className="kpi"><span className="kpi-label">Invested</span><span className="kpi-value">{compactInr(t.invested)}</span></div>
          <div className="kpi"><span className="kpi-label">Total P&amp;L</span><span className={`kpi-value ${t.pnl >= 0 ? "up" : "down"}`}>{compactInr(t.pnl)}</span><Change v={t.pnl_pct} /></div>
          <div className="kpi"><span className="kpi-label">Today</span><span className={`kpi-value ${t.day_change >= 0 ? "up" : "down"}`}>{compactInr(t.day_change)}</span><Change v={t.day_change_pct ?? null} /></div>
          <div className="kpi"><span className="kpi-label">XIRR</span><span className="kpi-value">{t.xirr_pct === null ? "–" : `${t.xirr_pct.toFixed(1)}%`}</span></div>
          <div className="kpi"><span className="kpi-label">Realised</span><span className="kpi-value">{compactInr(t.realized)}</span></div>
        </div>
      )}
      <Tabs<Tab> tabs={[{ id: "holdings", label: "Holdings" }, { id: "risk", label: "Risk" }, { id: "tax", label: "Tax" },
        { id: "rebalance", label: "Rebalance" }, { id: "trades", label: "Trades & import" }]} value={tab} onChange={setTab} />

      {tab === "holdings" && pf.data && (
        pf.data.holdings.length === 0 ? <Card><Empty>No holdings yet. Add trades or import a broker CSV in “Trades & import”.</Empty></Card> : (
          <>
            <Card title="Holdings">
              <div className="table-wrap">
                <table className="table">
                  <thead>
                    <tr><th>Instrument</th><th className="r">Qty</th><th className="r">Avg cost</th><th className="r">Price</th><th className="r">Value ₹</th><th className="r">P&amp;L</th><th className="r">Today</th><th className="r">XIRR</th><th className="r">Weight</th></tr>
                  </thead>
                  <tbody>
                    {pf.data.holdings.filter((h) => h.open).map((h) => (
                      <tr key={h.symbol}>
                        <td><Link to={`/instrument/${enc(h.symbol)}`}>{h.name}</Link><div className="muted small">{h.symbol} · {BUCKET_LABEL[h.bucket] ?? h.bucket}</div></td>
                        <td className="r num">{num(h.quantity, h.quantity % 1 ? 4 : 0)}</td>
                        <td className="r num">{money(h.avg_cost, h.currency, priceDigits(h.avg_cost))}</td>
                        <td className="r num">{money(h.price, h.currency, priceDigits(h.price))}</td>
                        <td className="r num">{num(h.value, 0)}</td>
                        <td className={`r num ${(h.pnl ?? 0) >= 0 ? "up" : "down"}`}>{num(h.pnl, 0)}<div className="small">{pct(h.pnl_pct)}</div></td>
                        <td className="r"><Change v={h.day_change_pct} /></td>
                        <td className="r num">{pct(h.xirr_pct, 1, false)}</td>
                        <td className="r num">{h.weight_pct.toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {pf.data.note && <p className="muted small">{pf.data.note}</p>}
            </Card>
            <div className="grid-2">
              <Card title="Allocation vs your target">
                {reb.data ? <Bars rows={reb.data.rows.map((r) => ({ label: r.label, value: r.actual_pct, target: r.target_pct }))} /> : <Spinner />}
                <p className="muted small">Target is the model mix for your “{reb.data?.profile}” risk profile (change it in Settings).</p>
              </Card>
              <Card title="Concentration">
                {pf.data.concentration && (
                  <table className="kv"><tbody>
                    <tr><td>Largest holding</td><td>{pf.data.concentration.largest} ({pf.data.concentration.largest_pct}%)</td></tr>
                    <tr><td>Top 5 holdings</td><td>{pf.data.concentration.top5_pct}%</td></tr>
                    <tr><td>Effective number of holdings</td><td>{pf.data.concentration.effective_holdings}</td></tr>
                  </tbody></table>
                )}
              </Card>
            </div>
          </>
        )
      )}
      {tab === "risk" && <RiskView />}
      {tab === "tax" && <TaxView />}
      {tab === "rebalance" && <RebalanceView plan={reb.data} loading={reb.loading} />}
      {tab === "trades" && <TradesView onChange={pf.reload} />}
    </div>
  );
}

type Risk = { available: boolean; reason?: string; days: number; annual_return_pct: number; volatility_pct: number; sharpe: number | null;
  max_drawdown_pct: number; var95_1d_pct: number; beta?: number; correlation_to_benchmark?: number; benchmark: string;
  correlation?: { symbols: string[]; matrix: number[][] }; risk_contribution_pct?: Record<string, number> };

function RiskView() {
  const r = useAsync(() => api.get<Risk>("/portfolio/risk"), []);
  if (r.loading) return <Spinner />;
  if (!r.data?.available) return <Card><Empty>{r.data?.reason ?? "Unavailable"}</Empty></Card>;
  const d = r.data;
  return (
    <div className="grid-2">
      <Card title="Past-year risk of today's mix">
        <table className="kv"><tbody>
          <tr><td>Annualised return</td><td>{pct(d.annual_return_pct, 1)}</td></tr>
          <tr><td>Volatility</td><td>{pct(d.volatility_pct, 1, false)}</td></tr>
          <tr><td>Sharpe ratio</td><td>{d.sharpe ?? "–"}</td></tr>
          <tr><td>Max drawdown</td><td>{pct(d.max_drawdown_pct, 1)}</td></tr>
          <tr><td>1-day VaR (95%)</td><td>{pct(d.var95_1d_pct, 2)}</td></tr>
          <tr><td>Beta to {d.benchmark}</td><td>{d.beta ?? "–"}</td></tr>
          <tr><td>Correlation to {d.benchmark}</td><td>{d.correlation_to_benchmark ?? "–"}</td></tr>
        </tbody></table>
        <p className="muted small">Based on {d.days} trading days, in each asset's own currency.</p>
      </Card>
      {d.risk_contribution_pct && (
        <Card title="Share of portfolio risk">
          <Bars rows={Object.entries(d.risk_contribution_pct).sort((a, b) => b[1] - a[1]).map(([k, v]) => ({ label: k, value: Math.max(0, v) }))} />
        </Card>
      )}
      {d.correlation && (
        <Card title="Correlation (top holdings)" className="span-2">
          <div className="table-wrap">
            <table className="table corr">
              <thead><tr><th></th>{d.correlation.symbols.map((s) => <th key={s}>{s}</th>)}</tr></thead>
              <tbody>
                {d.correlation.matrix.map((row, i) => (
                  <tr key={i}><th>{d.correlation!.symbols[i]}</th>{row.map((v, j) => <td key={j} style={{ background: `rgba(15,118,110,${Math.max(0, v) * 0.45})` }}>{v.toFixed(2)}</td>)}</tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}

type TaxRow = { tax_class: string; label: string; term: string; gross_gain: number; taxable_after_setoff: number; exempt: number; rate_pct: number; tax_incl_cess: number };
type TaxEst = { rows: TaxRow[]; total_tax: number; ltcg_exemption_left: number; notes: string[] };
type TaxView = {
  financial_year: string; slab_rate_pct: number;
  holdings: { symbol: string; name: string; label: string; short_term_gain: number; long_term_gain: number }[];
  if_sold_today: TaxEst; realized_this_fy: TaxEst; ltcg_harvest_room: number;
  turning_long_term_soon: { symbol: string; name: string; quantity: number; becomes_long_term_on: string; days_left: number; tax_saved_by_waiting: number }[];
  tax_loss_candidates: { symbol: string; name: string; loss: number }[];
};

function TaxTable({ est }: { est: TaxEst }) {
  if (!est.rows.length) return <Empty>No taxable gains.</Empty>;
  return (
    <div className="table-wrap">
      <table className="table">
        <thead><tr><th>Type</th><th>Term</th><th className="r">Gain</th><th className="r">Exempt</th><th className="r">Rate</th><th className="r">Tax incl. cess</th></tr></thead>
        <tbody>
          {est.rows.map((r) => (
            <tr key={r.tax_class + r.term}><td>{r.label}</td><td>{r.term}</td><td className="r num">{num(r.taxable_after_setoff, 0)}</td><td className="r num">{num(r.exempt, 0)}</td><td className="r">{r.rate_pct}%</td><td className="r num">{num(r.tax_incl_cess, 0)}</td></tr>
          ))}
          <tr className="total"><td colSpan={5}>Total</td><td className="r num">{money(est.total_tax, "INR", 0)}</td></tr>
        </tbody>
      </table>
    </div>
  );
}

function TaxView() {
  const r = useAsync(() => api.get<TaxView>("/portfolio/tax"), []);
  if (r.loading) return <Spinner />;
  if (!r.data) return <ErrorNote error={r.error} />;
  const d = r.data;
  return (
    <div className="grid-2">
      <Card title={`Booked this year (${d.financial_year})`}><TaxTable est={d.realized_this_fy} /></Card>
      <Card title="If you sold everything today"><TaxTable est={d.if_sold_today} /></Card>
      <Card title="Opportunities">
        <p>Equity LTCG you could still book tax-free this year: <strong>{money(d.ltcg_harvest_room, "INR", 0)}</strong></p>
        {d.turning_long_term_soon.length > 0 && (
          <>
            <h3>Turning long-term soon (worth waiting before selling)</h3>
            <ul>{d.turning_long_term_soon.map((s) => <li key={s.symbol + s.becomes_long_term_on}>{s.name}: {s.days_left} days (on {s.becomes_long_term_on}), saves about {money(s.tax_saved_by_waiting, "INR", 0)}</li>)}</ul>
          </>
        )}
        {d.tax_loss_candidates.length > 0 && (
          <>
            <h3>Losses you could book to offset gains</h3>
            <ul>{d.tax_loss_candidates.map((s) => <li key={s.symbol}>{s.name}: {money(s.loss, "INR", 0)}</li>)}</ul>
          </>
        )}
      </Card>
      <Card title="Gains by holding">
        <div className="table-wrap"><table className="table"><thead><tr><th>Holding</th><th className="r">Short-term</th><th className="r">Long-term</th></tr></thead>
          <tbody>{d.holdings.map((h) => <tr key={h.symbol}><td>{h.name}<div className="muted small">{h.label}</div></td><td className="r num">{num(h.short_term_gain, 0)}</td><td className="r num">{num(h.long_term_gain, 0)}</td></tr>)}</tbody>
        </table></div>
        <p className="muted small">Slab rate {d.slab_rate_pct}% (Settings). FY 2025-26 rules; estimates only. Confirm with a chartered accountant.</p>
      </Card>
    </div>
  );
}

type RebalancePlan = { profile: string; total_value: number; needs_rebalance: boolean;
  rows: { bucket: string; label: string; target_pct: number; actual_pct: number; drift_pts: number; action_amount: number; needs_action: boolean }[] };

function RebalanceView({ plan, loading }: { plan?: RebalancePlan; loading: boolean }) {
  if (loading || !plan) return <Spinner />;
  return (
    <Card title={`Rebalancing against the “${plan.profile}” model`}>
      <p>{plan.needs_rebalance ? "Some buckets have drifted more than 5 points from target." : "Your allocation is within 5 points of target everywhere."}</p>
      <div className="table-wrap"><table className="table">
        <thead><tr><th>Bucket</th><th className="r">Target</th><th className="r">Actual</th><th className="r">Drift</th><th className="r">Add (+) / trim (−)</th></tr></thead>
        <tbody>{plan.rows.map((r) => (
          <tr key={r.bucket} className={r.needs_action ? "flag" : ""}><td>{r.label}</td><td className="r">{r.target_pct}%</td><td className="r">{r.actual_pct.toFixed(1)}%</td>
            <td className="r">{r.drift_pts > 0 ? "+" : ""}{r.drift_pts.toFixed(1)}</td><td className="r num">{money(r.action_amount, "INR", 0)}</td></tr>
        ))}</tbody>
      </table></div>
      <p className="muted small">Prefer fixing drift with new money (SIPs) before selling, to avoid taxes and costs. Ask the adviser for a specific plan.</p>
    </Card>
  );
}

function TradesView({ onChange }: { onChange: () => void }) {
  const txs = useAsync(() => api.get<{ transactions: Tx[] }>("/transactions"), []);
  const [form, setForm] = useState({ symbol: "", side: "buy", quantity: "", price: "", trade_date: new Date().toISOString().slice(0, 10), fees: "", fx_rate: "" });
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState<unknown>();
  const [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setErr(undefined);
    setBusy(true);
    try {
      await api.post("/transactions", { symbol: form.symbol.trim(), side: form.side, quantity: Number(form.quantity), price: Number(form.price),
        trade_date: form.trade_date, fees: Number(form.fees || 0), fx_rate: form.fx_rate ? Number(form.fx_rate) : null });
      setMsg(`Added ${form.side} of ${form.symbol}.`);
      setForm({ ...form, symbol: "", quantity: "", price: "", fees: "", fx_rate: "" });
      txs.reload();
      onChange();
    } catch (e2) {
      setErr(e2);
    } finally {
      setBusy(false);
    }
  };
  const upload = async (file: File) => {
    setErr(undefined);
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await api.upload<{ format: string; added: number; skipped: string[]; warnings: string[] }>("/portfolio/import", fd);
      setMsg(`Imported ${r.added} trades (${r.format.replace("_", " ")}).${r.skipped.length ? ` Skipped: ${r.skipped.join(", ")}.` : ""} ${r.warnings.join(" ")}`);
      txs.reload();
      onChange();
    } catch (e2) {
      setErr(e2);
    } finally {
      setBusy(false);
    }
  };
  const remove = async (id: number) => {
    if (!window.confirm("Delete this trade?")) return;
    await api.del(`/transactions/${id}`);
    txs.reload();
    onChange();
  };
  return (
    <div className="grid-2">
      <Card title="Add a trade">
        <form className="form" onSubmit={submit}>
          <label>Symbol or name<input value={form.symbol} onChange={(e) => setForm({ ...form, symbol: e.target.value })} placeholder="RELIANCE.NS, AAPL, MF:122639, CRYPTO:BTC_USDT" required /></label>
          <div className="row">
            <label>Side<select value={form.side} onChange={(e) => setForm({ ...form, side: e.target.value })}><option value="buy">Buy</option><option value="sell">Sell</option></select></label>
            <label>Date<input type="date" value={form.trade_date} onChange={(e) => setForm({ ...form, trade_date: e.target.value })} required /></label>
          </div>
          <div className="row">
            <label>Quantity<input type="number" step="any" min="0" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} required /></label>
            <label>Price per unit<input type="number" step="any" min="0" value={form.price} onChange={(e) => setForm({ ...form, price: e.target.value })} required /></label>
          </div>
          <div className="row">
            <label>Fees<input type="number" step="any" min="0" value={form.fees} onChange={(e) => setForm({ ...form, fees: e.target.value })} /></label>
            <label>FX rate (₹ per unit, foreign only)<input type="number" step="any" min="0" value={form.fx_rate} onChange={(e) => setForm({ ...form, fx_rate: e.target.value })} placeholder="e.g. 83.2" /></label>
          </div>
          <button className="btn primary" disabled={busy}>Add trade</button>
        </form>
      </Card>
      <Card title="Import from your broker">
        <p className="small">Upload a CSV: a Zerodha tradebook (best: it has dates), Zerodha or Groww holdings, or a generic file with columns <code>symbol, side, quantity, price, date</code> (optional <code>fees, fx_rate</code>).</p>
        <input type="file" accept=".csv,text/csv" onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} disabled={busy} />
      </Card>
      {(msg || !!err) && <div className="span-2">{msg && <div className="ok-note">{msg}</div>}<ErrorNote error={err} /></div>}
      <Card title="All trades" className="span-2">
        {txs.data && txs.data.transactions.length === 0 && <Empty>No trades yet.</Empty>}
        {txs.data && txs.data.transactions.length > 0 && (
          <div className="table-wrap"><table className="table">
            <thead><tr><th>Date</th><th>Instrument</th><th>Side</th><th className="r">Qty</th><th className="r">Price</th><th className="r">Fees</th><th></th></tr></thead>
            <tbody>{txs.data.transactions.map((t) => (
              <tr key={t.id}><td>{t.trade_date}</td><td>{t.name}<div className="muted small">{t.symbol}</div></td><td>{t.side}</td>
                <td className="r num">{num(t.quantity, t.quantity % 1 ? 4 : 0)}</td><td className="r num">{num(t.price, priceDigits(t.price))}</td><td className="r num">{num(t.fees)}</td>
                <td><button className="link-btn danger" onClick={() => remove(t.id)}>Delete</button></td></tr>
            ))}</tbody>
          </table></div>
        )}
      </Card>
    </div>
  );
}
