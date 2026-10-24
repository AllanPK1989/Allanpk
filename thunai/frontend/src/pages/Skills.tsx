// Skill-gap analytics (SPEC 12.5): for training and shift planning, not appraisal.
// The coverage table is a heat table: one blue ramp (light = few fixes, dark = many) and every
// count printed in its cell, so the colour only helps scanning and never carries the value alone.
import { useEffect, useState } from "react";
import { api, downloadFile } from "../api";
import type { Skills as Data } from "../api";
import { ErrorNote, Header, Icon, Page, Spinner } from "../components";
import { useApp } from "../state";

const PERIODS = [30, 90, 365];
// Sequential blue steps from the validated reference ramp (100…700), binned by fix count.
const BINS = [
  { min: 5, bg: "#1c5cab", ink: "#ffffff", label: "5+" },
  { min: 3, bg: "#3987e5", ink: "#ffffff", label: "3–4" },
  { min: 2, bg: "#86b6ef", ink: "#0d1726", label: "2" },
  { min: 1, bg: "#cde2fb", ink: "#0d1726", label: "1" },
];
const KIND_LABEL: Record<Data["suggestions"][number]["kind"], string> = {
  single_person: "Knowledge at risk",
  pair: "Pair up",
  authorisation: "Authorisation",
};

const bin = (n: number) => BINS.find((b) => n >= b.min);

export default function Skills() {
  const { user } = useApp();
  const [days, setDays] = useState(90);
  const [zone, setZone] = useState("");
  const [zones, setZones] = useState<string[]>([]);
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<unknown>(null);
  const isAdmin = user?.role === "admin";

  useEffect(() => {
    if (isAdmin) api.get<string[]>("/api/machines/zones").then(setZones).catch(() => {});
  }, [isAdmin]);

  useEffect(() => {
    setData(null);
    const q = new URLSearchParams({ days: String(days), ...(zone ? { zone } : {}) });
    api.get<Data>(`/api/skills?${q}`).then(setData).catch(setError);
  }, [days, zone]);

  const exportXlsx = () => {
    const q = new URLSearchParams({ days: String(days), ...(zone ? { zone } : {}) });
    void downloadFile(`/api/export/skills.xlsx?${q}`, `thunai-skills-${days}d.xlsx`).catch(setError);
  };

  return (
    <>
      <Header title="Skills" />
      <Page>
        <div className="filters" role="group" aria-label="Filters">
          <div className="segmented" role="radiogroup" aria-label="Period">
            {PERIODS.map((p) => (
              <button key={p} role="radio" aria-checked={days === p} className={days === p ? "on" : ""} onClick={() => setDays(p)}>
                {p} days
              </button>
            ))}
          </div>
          {isAdmin && (
            <select className="input filter-select" value={zone} onChange={(e) => setZone(e.target.value)} aria-label="Zone">
              <option value="">All zones</option>
              {zones.map((z) => (
                <option key={z}>{z}</option>
              ))}
            </select>
          )}
          <button className="btn btn-ghost btn-small" onClick={exportXlsx}>
            <Icon name="download" size={18} /> Excel
          </button>
        </div>
        <ErrorNote error={error} />
        {!data && !error && <Spinner label="Loading" />}
        {data && (
          <>
            <p className="note note-info">
              For training and shift planning, not appraisal. {data.zone ? `Zone: ${data.zone}. ` : ""}Figures need at least{" "}
              {data.min_events} events; fewer show as “–”.
            </p>

            <section>
              <h2 className="section-title">Suggestions</h2>
              {data.suggestions.length === 0 && <p className="muted">Nothing to suggest for this period.</p>}
              {data.suggestions.map((g, i) => (
                <div key={i} className={`suggestion suggestion-${g.kind}`}>
                  <span className="chip">{KIND_LABEL[g.kind]}</span>
                  <p>{g.text_en}</p>
                </div>
              ))}
            </section>

            <section>
              <h2 className="section-title">Who has fixed what</h2>
              {data.matrix.length === 0 ? (
                <p className="muted">No breakdowns with a technician recorded in this period.</p>
              ) : (
                <>
                  <div className="table-wrap">
                    <table className="table heat-table">
                      <thead>
                        <tr>
                          <th scope="col">Technician</th>
                          {data.types.map((t) => (
                            <th key={t} scope="col" className="num">
                              {t}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {data.matrix.map((row) => (
                          <tr key={row.key}>
                            <th scope="row">{row.name}</th>
                            {data.types.map((t) => {
                              const n = row.cells[t] ?? 0;
                              const b = bin(n);
                              return (
                                <td
                                  key={t}
                                  className="num heat-cell"
                                  style={b ? { background: b.bg, color: b.ink } : undefined}
                                  title={`${row.name} · ${t}: ${n} ${n === 1 ? "fix" : "fixes"}`}
                                >
                                  {n || "–"}
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="heat-legend" aria-label="Fixes per cell">
                    <span className="muted small">Fixes:</span>
                    {[...BINS].reverse().map((b) => (
                      <span key={b.label} className="heat-key">
                        <span className="heat-swatch" style={{ background: b.bg }} /> {b.label}
                      </span>
                    ))}
                  </div>
                </>
              )}
            </section>

            <section>
              <h2 className="section-title">Machine types</h2>
              {data.machine_types.map((r) => (
                <div key={r.name} className="skill-row">
                  <div className="row-between">
                    <strong>{r.name}</strong>
                    <span className="muted small">{r.breakdowns} breakdowns</span>
                  </div>
                  <p className={r.breakdowns && r.fixers <= 1 ? "text-warn" : "muted"}>
                    Fixed by {r.fixers} {r.fixers === 1 ? "person" : "people"}
                    {r.fixer_names.length > 0 && `: ${r.fixer_names.join(", ")}`}
                  </p>
                  <dl className="skill-stats">
                    <div>
                      <dt>Median downtime</dt>
                      <dd>{r.median_downtime_min != null ? `${r.median_downtime_min} min` : "–"}</dd>
                    </div>
                    <div>
                      <dt>Supervisor called</dt>
                      <dd>{r.escalation_pct != null ? `${r.escalation_pct}% of ${r.sessions}` : r.sessions ? `${r.sessions} sessions` : "–"}</dd>
                    </div>
                  </dl>
                </div>
              ))}
            </section>

            <section>
              <h2 className="section-title">Technicians</h2>
              {data.technicians.map((r) => (
                <div key={r.key} className="skill-row">
                  <div className="row-between">
                    <strong>{r.name}</strong>
                    <span className="muted small">{r.employee_id || "Imported name"}</span>
                  </div>
                  {r.machine_types.length > 0 && <p className="muted small">{r.machine_types.join(", ")}</p>}
                  <dl className="skill-stats">
                    <div>
                      <dt>Fixes</dt>
                      <dd>
                        {r.fixes}
                        {r.verified > 0 && <span className="muted small"> ({r.verified} verified)</span>}
                      </dd>
                    </div>
                    <div>
                      <dt>Median downtime</dt>
                      <dd>
                        {r.median_downtime_min != null ? `${r.median_downtime_min} min` : "–"}
                        {r.vs_team != null && <span className="muted small"> ({r.vs_team}× team)</span>}
                      </dd>
                    </div>
                    <div>
                      <dt>Ask Thunai</dt>
                      <dd>
                        {r.sessions}
                        {r.escalation_pct != null && <span className="muted small"> ({r.escalation_pct}% called)</span>}
                      </dd>
                    </div>
                    <div>
                      <dt>Can't do</dt>
                      <dd>
                        {r.cant_do}
                        {r.cant_do_authorised > 0 && <span className="muted small"> ({r.cant_do_authorised} authorised-only)</span>}
                      </dd>
                    </div>
                    <div>
                      <dt>Tips</dt>
                      <dd>{r.tips}</dd>
                    </div>
                  </dl>
                </div>
              ))}
            </section>
          </>
        )}
      </Page>
    </>
  );
}
