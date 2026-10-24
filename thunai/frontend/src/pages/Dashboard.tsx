// Supervisor dashboard (SPEC 11.2). Single-series bars use one validated blue; every value is also
// printed next to its bar, so the hover/focus tooltip only adds detail and never gates it.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, downloadFile } from "../api";
import type { PartInfo } from "../api";
import { ErrorNote, Header, Icon, Page, PartChip, Spinner } from "../components";
import { useApp } from "../state";

interface Row {
  name: string;
  downtime_min: number;
  breakdowns: number;
}

interface Data {
  days: number;
  machines: number;
  totals: { open_breakdowns: number; breakdowns: number; downtime_min: number; mttr_min: number | null; logs_verified_pct: number | null };
  open_breakdowns: { id: number; log_no: string; machine_no: string; issue: string; issue_ta: string; hours_open: number; escalated: boolean }[];
  downtime_by_zone: Row[];
  downtime_by_shift: Row[];
  machines_table: { machine_no: string; name: string; zone: string; criticality: string; breakdowns: number; downtime_min: number; mttr_min: number | null; mtbf_h: number | null }[];
  top_faults: { symptom: string; symptom_ta: string; count: number; machines: string[]; avg_downtime_min: number | null; last: string }[];
  knowledge: {
    machines_covered: number;
    machines_uncovered: { machine_no: string; name: string }[];
    cards_live: number;
    cards_draft: number;
    cards_needs_review: number;
    tips_approved: number;
    tips_pending: number;
  };
  ask_thunai: { sessions: number; resolved: number; escalated: number; refused: number; failed: number; helpful: number; not_helpful: number; cost_usd: number };
  parts: { used: { part_no: string; description: string; times: number; qty: number; stock: PartInfo | null }[]; low_stock: PartInfo[] };
  pm: { overdue: { machine_no: string; zone: string; task_code: string; title: string; days_overdue: number }[]; tasks: number; breakdowns_while_overdue: number };
}

const PERIODS = [7, 30, 90];
const hours = (min: number) => (min / 60).toFixed(min >= 600 ? 0 : 1);

export default function Dashboard() {
  const { lang } = useApp();
  const [days, setDays] = useState(30);
  const [zone, setZone] = useState("");
  const [zones, setZones] = useState<string[]>([]);
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api.get<string[]>("/api/machines/zones").then(setZones).catch(() => {});
  }, []);

  useEffect(() => {
    setData(null);
    const q = new URLSearchParams({ days: String(days), ...(zone ? { zone } : {}) });
    api.get<Data>(`/api/dashboard?${q}`).then(setData).catch(setError);
  }, [days, zone]);

  const exportXlsx = () => {
    const q = new URLSearchParams({ days: String(days), ...(zone ? { zone } : {}) });
    void downloadFile(`/api/export/dashboard.xlsx?${q}`, `thunai-dashboard-${days}d.xlsx`).catch(setError);
  };

  return (
    <>
      <Header title="Dashboard" />
      <Page>
        <div className="filters" role="group" aria-label="Filters">
          <div className="segmented" role="radiogroup" aria-label="Period">
            {PERIODS.map((p) => (
              <button key={p} role="radio" aria-checked={days === p} className={days === p ? "on" : ""} onClick={() => setDays(p)}>
                {p} days
              </button>
            ))}
          </div>
          <select className="input filter-select" value={zone} onChange={(e) => setZone(e.target.value)} aria-label="Zone">
            <option value="">All zones</option>
            {zones.map((z) => (
              <option key={z}>{z}</option>
            ))}
          </select>
          <button className="btn btn-ghost btn-small" onClick={exportXlsx}>
            <Icon name="download" size={18} /> Excel
          </button>
        </div>
        <ErrorNote error={error} />
        {!data && !error && <Spinner label="Loading" />}
        {data && (
          <>
            <section className="stat-grid" aria-label="Totals">
              <Stat label="Open breakdowns now" value={data.totals.open_breakdowns} alert={data.totals.open_breakdowns > 0} />
              <Stat label={`Breakdowns, last ${data.days} days`} value={data.totals.breakdowns} />
              <Stat label="Downtime (hours)" value={hours(data.totals.downtime_min)} />
              <Stat label="MTTR (min)" value={data.totals.mttr_min ?? "–"} />
              <Stat label="Logs verified" value={data.totals.logs_verified_pct != null ? `${data.totals.logs_verified_pct}%` : "–"} />
            </section>

            {data.open_breakdowns.length > 0 && (
              <section>
                <h2 className="section-title">Open breakdowns</h2>
                {data.open_breakdowns.map((o) => (
                  <Link key={o.id} to={`/log/${o.id}`} className="list-item list-item-alert">
                    <div>
                      <strong className="mono">{o.machine_no}</strong> · {o.log_no}
                      {o.escalated && <span className="chip chip-open"> escalated</span>}
                      <div className="clamp">{lang === "ta" && o.issue_ta ? o.issue_ta : o.issue}</div>
                    </div>
                    <span className="count">{o.hours_open} h</span>
                  </Link>
                ))}
              </section>
            )}

            <section className="chart-card">
              <h2 className="chart-title">Downtime by zone</h2>
              <p className="chart-sub">Minutes of breakdown downtime, closed and verified logs</p>
              <BarList rows={data.downtime_by_zone} />
            </section>
            <section className="chart-card">
              <h2 className="chart-title">Downtime by shift</h2>
              <p className="chart-sub">Shift from the plant's shift calendar</p>
              <BarList rows={data.downtime_by_shift} />
            </section>

            <section>
              <h2 className="section-title">Machines, most downtime first</h2>
              <div className="table-wrap">
                <table className="table table-full">
                  <thead>
                    <tr>
                      <th>Machine</th>
                      <th className="num">Breakdowns</th>
                      <th className="num">Downtime (min)</th>
                      <th className="num">MTTR (min)</th>
                      <th className="num">MTBF (h)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.machines_table.map((m) => (
                      <tr key={m.machine_no}>
                        <td>
                          <Link className="mono" to={`/m/${encodeURIComponent(m.machine_no)}`}>
                            {m.machine_no}
                          </Link>
                          <div className="muted small">{m.name}</div>
                        </td>
                        <td className="num">{m.breakdowns}</td>
                        <td className="num">{m.downtime_min}</td>
                        <td className="num">{m.mttr_min ?? "–"}</td>
                        <td className="num">{m.mtbf_h ?? "–"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section>
              <h2 className="section-title">Top repeat faults</h2>
              {data.top_faults.length === 0 && <p className="muted">No breakdowns in this period.</p>}
              {data.top_faults.map((f) => (
                <div key={f.symptom} className="fault-row">
                  <div>
                    <strong>{lang === "ta" && f.symptom_ta ? f.symptom_ta : f.symptom}</strong>
                    <div className="muted small">
                      {f.machines.join(", ")}
                      {f.avg_downtime_min != null && ` · avg ${f.avg_downtime_min} min`}
                    </div>
                  </div>
                  <span className="count">{f.count}×</span>
                </div>
              ))}
            </section>

            <section>
              <h2 className="section-title">Spare parts used in breakdowns</h2>
              {data.parts.used.length === 0 && <p className="muted">No parts recorded in this period.</p>}
              {data.parts.used.length > 0 && (
                <div className="table-wrap">
                  <table className="table table-full">
                    <thead>
                      <tr>
                        <th>Part</th>
                        <th className="num">Times</th>
                        <th className="num">Stock now</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.parts.used.map((r) => (
                        <tr key={`${r.part_no}|${r.description}`}>
                          <td>
                            {r.part_no && <span className="mono">{r.part_no} </span>}
                            {r.description}
                            {!r.stock && <div className="muted small">Not in the catalogue</div>}
                          </td>
                          <td className="num">{r.times}</td>
                          <td className={`num ${r.stock?.low ? "text-warn" : ""}`}>
                            {r.stock ? (r.stock.stock_qty ?? "–") : "–"}
                            {r.stock?.low && " (low)"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {data.parts.low_stock.length > 0 && (
                <>
                  <h3 className="chart-title">Low stock for these machines</h3>
                  <div className="parts-list">
                    {data.parts.low_stock.map((p) => (
                      <PartChip key={p.part_no} part={p} />
                    ))}
                  </div>
                </>
              )}
            </section>

            <section>
              <h2 className="section-title">PM tasks overdue</h2>
              {data.pm.tasks === 0 && <p className="muted">No PM plan imported yet (Admin → Import → PM plan).</p>}
              {data.pm.tasks > 0 && data.pm.overdue.length === 0 && <p className="muted">No PM task is overdue.</p>}
              {data.pm.overdue.map((r) => (
                <div key={`${r.machine_no}|${r.task_code}`} className="fault-row pm-overdue">
                  <div>
                    <strong>{r.title || r.task_code}</strong>
                    <div className="muted small">
                      <Link className="mono" to={`/m/${encodeURIComponent(r.machine_no)}`}>
                        {r.machine_no}
                      </Link>{" "}
                      · {r.task_code} · {r.zone}
                    </div>
                  </div>
                  <span className="chip chip-open">+{r.days_overdue} d</span>
                </div>
              ))}
              {data.pm.tasks > 0 && (
                <p className="muted small">
                  Breakdowns while a PM task on that machine was overdue: at least {data.pm.breakdowns_while_overdue} of {data.totals.breakdowns}.
                </p>
              )}
            </section>

            <section className="chart-card">
              <h2 className="chart-title">Knowledge coverage</h2>
              <Meter value={data.knowledge.machines_covered} total={data.machines} label="machines have a fault card (own or for their type)" />
              <div className="stat-grid compact">
                <Stat label="Cards in use" value={data.knowledge.cards_live} />
                <Stat label="Drafts waiting" value={data.knowledge.cards_draft} link="/review" />
                <Stat label="Cards needing review" value={data.knowledge.cards_needs_review} link="/review" alert={data.knowledge.cards_needs_review > 0} />
                <Stat label="Expert tips" value={data.knowledge.tips_approved} />
                <Stat label="Tips waiting" value={data.knowledge.tips_pending} link="/review" />
              </div>
              {data.knowledge.machines_uncovered.length > 0 && (
                <details>
                  <summary>Machines without a fault card ({data.knowledge.machines_uncovered.length})</summary>
                  <ul className="plain-list">
                    {data.knowledge.machines_uncovered.map((m) => (
                      <li key={m.machine_no}>
                        <Link className="mono" to={`/m/${encodeURIComponent(m.machine_no)}`}>
                          {m.machine_no}
                        </Link>{" "}
                        <span className="muted">{m.name}</span>
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </section>

            <section>
              <h2 className="section-title">Ask Thunai</h2>
              <div className="stat-grid compact">
                <Stat label="Sessions" value={data.ask_thunai.sessions} />
                <Stat label="Machine running after" value={data.ask_thunai.resolved} />
                <Stat label="Escalated" value={data.ask_thunai.escalated} />
                <Stat label="Helpful / not helpful" value={`${data.ask_thunai.helpful} / ${data.ask_thunai.not_helpful}`} />
                <Stat label="AI cost" value={`$${data.ask_thunai.cost_usd.toFixed(2)}`} />
              </div>
            </section>
          </>
        )}
      </Page>
    </>
  );
}

function Stat({ label, value, alert = false, link }: { label: string; value: string | number; alert?: boolean; link?: string }) {
  const body = (
    <>
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
    </>
  );
  return link ? (
    <Link to={link} className={`stat ${alert ? "stat-alert" : ""}`}>
      {body}
    </Link>
  ) : (
    <div className={`stat ${alert ? "stat-alert" : ""}`}>{body}</div>
  );
}

/** Horizontal bars, one series. The value sits at the bar's tip; the tooltip adds the count. */
function BarList({ rows }: { rows: Row[] }) {
  const max = Math.max(1, ...rows.map((r) => r.downtime_min));
  if (!rows.length) return <p className="muted">No breakdowns in this period.</p>;
  return (
    <ul className="bars" role="list">
      {rows.map((r) => {
        const label = `${r.name}: ${r.downtime_min} min downtime, ${r.breakdowns} breakdown${r.breakdowns === 1 ? "" : "s"}`;
        return (
          <li key={r.name} className="bar-row" tabIndex={0} aria-label={label}>
            <span className="bar-name">{r.name}</span>
            <span className="bar-track">
              <span className="bar" style={{ width: `${Math.max(2, (r.downtime_min / max) * 100)}%` }} />
              <span className="bar-value">{r.downtime_min} min</span>
            </span>
            <span className="bar-tip" role="tooltip">
              {label}
            </span>
          </li>
        );
      })}
    </ul>
  );
}

function Meter({ value, total, label }: { value: number; total: number; label: string }) {
  const pct = total ? Math.round((value / total) * 100) : 0;
  return (
    <div className="meter-wrap">
      <div className="meter" role="meter" aria-valuemin={0} aria-valuemax={total} aria-valuenow={value} aria-label={label}>
        <span style={{ width: `${pct}%` }} />
      </div>
      <p>
        <strong>
          {value} of {total}
        </strong>{" "}
        {label}
      </p>
    </div>
  );
}
