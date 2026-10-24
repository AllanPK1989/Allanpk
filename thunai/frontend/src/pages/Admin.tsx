// Admin console for maintenance engineering (English UI). All changes are written to the audit trail.
import { useCallback, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, downloadFile } from "../api";
import type { Machine, User } from "../api";
import { ErrorNote, Header, Icon, Page, Spinner } from "../components";
import { useApp } from "../state";

const TABS = [
  ["machines", "Machines"],
  ["import", "Import"],
  ["users", "Users"],
  ["glossary", "Glossary"],
  ["settings", "Settings"],
  ["export", "Export"],
  ["usage", "AI usage"],
  ["audit", "Audit"],
] as const;
type Tab = (typeof TABS)[number][0];

export default function Admin() {
  const [params, setParams] = useSearchParams();
  const tab = (params.get("tab") as Tab) || "machines";
  return (
    <>
      <Header title="Admin" />
      <Page>
        <div className="tabs tabs-scroll" role="tablist">
          {TABS.map(([key, label]) => (
            <button key={key} role="tab" aria-selected={tab === key} className={`tab ${tab === key ? "on" : ""}`} onClick={() => setParams({ tab: key })}>
              {label}
            </button>
          ))}
        </div>
        {tab === "machines" && <MachinesTab />}
        {tab === "import" && <ImportTab />}
        {tab === "users" && <UsersTab />}
        {tab === "glossary" && <GlossaryTab />}
        {tab === "settings" && <SettingsTab />}
        {tab === "export" && <ExportTab />}
        {tab === "usage" && <UsageTab />}
        {tab === "audit" && <AuditTab />}
      </Page>
    </>
  );
}

function useLoad<T>(path: string): [T | null, unknown, () => void] {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<unknown>(null);
  const load = useCallback(() => {
    api.get<T>(path).then(setData).catch(setError);
  }, [path]);
  useEffect(load, [load]);
  return [data, error, load];
}

function Form({ children, onSubmit }: { children: ReactNode; onSubmit: () => Promise<void> }) {
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  return (
    <form
      className="admin-form"
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        setError(null);
        try {
          await onSubmit();
        } catch (err) {
          setError(err);
        } finally {
          setBusy(false);
        }
      }}
    >
      {children}
      <ErrorNote error={error} />
      <button className="btn btn-primary" disabled={busy}>
        Save
      </button>
    </form>
  );
}

function MachinesTab() {
  const { toast } = useApp();
  const [machines, error, reload] = useLoad<Machine[]>("/api/machines?include_inactive=true&limit=1000");
  const [form, setForm] = useState({ machine_no: "", name: "", machine_type: "", zone: "", line: "", plc_model: "", criticality: "B" });
  const [showForm, setShowForm] = useState(false);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm({ ...form, [k]: e.target.value });

  const toggle = async (m: Machine) => {
    await api.patch(`/api/machines/${encodeURIComponent(m.machine_no)}`, { active: !m.active });
    reload();
  };

  return (
    <>
      <div className="row-between">
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
          <Icon name="plus" /> Add machine
        </button>
        <Link className="btn btn-ghost" to="/admin/qr">
          <Icon name="qr" /> Print QR stickers
        </Link>
      </div>
      {showForm && (
        <Form
          onSubmit={async () => {
            await api.post("/api/machines", form);
            toast("Machine added");
            setShowForm(false);
            reload();
          }}
        >
          <input className="input" placeholder="Machine number" required value={form.machine_no} onChange={set("machine_no")} />
          <input className="input" placeholder="Name" required value={form.name} onChange={set("name")} />
          <input className="input" placeholder="Machine type (shares knowledge)" value={form.machine_type} onChange={set("machine_type")} />
          <input className="input" placeholder="Zone" value={form.zone} onChange={set("zone")} />
          <input className="input" placeholder="Line" value={form.line} onChange={set("line")} />
          <input className="input" placeholder="PLC model" value={form.plc_model} onChange={set("plc_model")} />
          <select className="input" value={form.criticality} onChange={set("criticality")}>
            {["A", "B", "C"].map((c) => (
              <option key={c}>{c}</option>
            ))}
          </select>
        </Form>
      )}
      <ErrorNote error={error} />
      {!machines && !error && <Spinner />}
      <table className="table">
        <thead>
          <tr>
            <th>No</th>
            <th>Name</th>
            <th>Zone</th>
            <th>Active</th>
          </tr>
        </thead>
        <tbody>
          {machines?.map((m) => (
            <tr key={m.id} className={m.active ? "" : "inactive"}>
              <td className="mono">
                <Link to={`/m/${encodeURIComponent(m.machine_no)}`}>{m.machine_no}</Link>
              </td>
              <td>{m.name}</td>
              <td>{m.zone}</td>
              <td>
                <button className="btn btn-small" onClick={() => void toggle(m)}>
                  {m.active ? "Active" : "Inactive"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

function ImportTab() {
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState<unknown>(null);
  const [verified, setVerified] = useState(true);
  const upload = async (kind: "machines" | "logs", file: File | undefined) => {
    if (!file) return;
    setError(null);
    setResult(null);
    const form = new FormData();
    form.append("file", file);
    if (kind === "logs") form.append("mark_verified", String(verified));
    try {
      setResult(await api.upload(`/api/admin/import/${kind}`, form));
    } catch (e) {
      setError(e);
    }
  };
  return (
    <>
      <section className="card">
        <h3>Machine master (Excel)</h3>
        <p className="muted">One row per machine. Existing machine numbers are updated; new ones get a QR code.</p>
        <div className="row-wrap">
          <button className="btn btn-ghost" onClick={() => void downloadFile("/api/admin/templates/machines.xlsx", "thunai-machines-template.xlsx")}>
            <Icon name="download" /> Template
          </button>
          <label className="btn btn-primary file-btn">
            Upload .xlsx
            <input type="file" accept=".xlsx" hidden onChange={(e) => void upload("machines", e.target.files?.[0])} />
          </label>
        </div>
      </section>
      <section className="card">
        <h3>Historical breakdowns (Excel)</h3>
        <p className="muted">Seeds the knowledge base. Logs are translated and classified in the background.</p>
        <label className="check-row">
          <input type="checkbox" checked={verified} onChange={(e) => setVerified(e.target.checked)} />
          <span>Mark imported logs as verified (official register)</span>
        </label>
        <div className="row-wrap">
          <button className="btn btn-ghost" onClick={() => void downloadFile("/api/admin/templates/logs.xlsx", "thunai-logs-template.xlsx")}>
            <Icon name="download" /> Template
          </button>
          <label className="btn btn-primary file-btn">
            Upload .xlsx
            <input type="file" accept=".xlsx" hidden onChange={(e) => void upload("logs", e.target.files?.[0])} />
          </label>
        </div>
      </section>
      <ErrorNote error={error} />
      {result !== null && <pre className="summary">{JSON.stringify(result, null, 2)}</pre>}
    </>
  );
}

function UsersTab() {
  const { toast } = useApp();
  const [users, error, reload] = useLoad<User[]>("/api/admin/users");
  const blank = { employee_id: "", name: "", role: "technician", zone: "", preferred_language: "ta", phone: "", pin: "" };
  const [form, setForm] = useState(blank);
  const [showForm, setShowForm] = useState(false);
  const set = (k: keyof typeof blank) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm({ ...form, [k]: e.target.value });

  const resetPin = async (u: User) => {
    const pin = window.prompt(`New 4-digit PIN for ${u.name}`);
    if (!pin) return;
    try {
      await api.post(`/api/admin/users/${u.id}/pin`, { pin });
      toast("PIN changed");
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed");
    }
  };
  const toggle = async (u: User) => {
    try {
      await api.patch(`/api/admin/users/${u.id}`, { active: !u.active });
      reload();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed");
    }
  };

  return (
    <>
      <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
        <Icon name="plus" /> Add user
      </button>
      {showForm && (
        <Form
          onSubmit={async () => {
            await api.post("/api/admin/users", form);
            toast("User added");
            setForm(blank);
            setShowForm(false);
            reload();
          }}
        >
          <input className="input" placeholder="Employee ID" required value={form.employee_id} onChange={set("employee_id")} />
          <input className="input" placeholder="Name" required value={form.name} onChange={set("name")} />
          <select className="input" value={form.role} onChange={set("role")}>
            <option value="technician">Technician</option>
            <option value="supervisor">Supervisor</option>
            <option value="admin">Admin</option>
          </select>
          <input className="input" placeholder="Zone" value={form.zone} onChange={set("zone")} />
          <select className="input" value={form.preferred_language} onChange={set("preferred_language")}>
            <option value="ta">Tamil</option>
            <option value="en">English</option>
          </select>
          <input className="input" placeholder="Phone (supervisors)" value={form.phone} onChange={set("phone")} />
          <input className="input" placeholder="4-digit PIN" inputMode="numeric" maxLength={4} required value={form.pin} onChange={set("pin")} />
        </Form>
      )}
      <ErrorNote error={error} />
      <table className="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Role</th>
            <th>Zone</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {users?.map((u) => (
            <tr key={u.id} className={u.active ? "" : "inactive"}>
              <td className="mono">{u.employee_id}</td>
              <td>
                {u.name}
                {u.locked && <span className="chip chip-rejected"> locked</span>}
              </td>
              <td>{u.role}</td>
              <td>{u.zone}</td>
              <td className="row-wrap">
                <button className="btn btn-small" onClick={() => void resetPin(u)}>
                  PIN
                </button>
                <button className="btn btn-small" onClick={() => void toggle(u)}>
                  {u.active ? "Deactivate" : "Activate"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

interface Term {
  id: number;
  term_en: string;
  term_ta: string;
  spoken_variants: string[];
  category: string;
  active: boolean;
}

function GlossaryTab() {
  const [terms, error, reload] = useLoad<Term[]>("/api/glossary");
  const [form, setForm] = useState({ term_en: "", term_ta: "", spoken: "", category: "" });
  return (
    <>
      <p className="muted">Used by speech recognition, translation and Tamil output. Technical terms stay in English in Tamil text.</p>
      <Form
        onSubmit={async () => {
          await api.post("/api/admin/glossary", {
            term_en: form.term_en,
            term_ta: form.term_ta,
            spoken_variants: form.spoken.split(",").map((s) => s.trim()).filter(Boolean),
            category: form.category,
          });
          setForm({ term_en: "", term_ta: "", spoken: "", category: "" });
          reload();
        }}
      >
        <input className="input" placeholder="English term" required value={form.term_en} onChange={(e) => setForm({ ...form, term_en: e.target.value })} />
        <input className="input" placeholder="Tamil term" value={form.term_ta} onChange={(e) => setForm({ ...form, term_ta: e.target.value })} />
        <input className="input" placeholder="Spoken forms, comma separated" value={form.spoken} onChange={(e) => setForm({ ...form, spoken: e.target.value })} />
        <input className="input" placeholder="Category" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} />
      </Form>
      <ErrorNote error={error} />
      <table className="table">
        <thead>
          <tr>
            <th>English</th>
            <th>Tamil</th>
            <th>Spoken forms</th>
          </tr>
        </thead>
        <tbody>
          {terms?.map((g) => (
            <tr key={g.id}>
              <td>{g.term_en}</td>
              <td>{g.term_ta}</td>
              <td className="muted">{g.spoken_variants.join(", ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

type Settings = Record<string, unknown> & { shifts: { name: string; start: string; end: string }[] };

const NUMBER_SETTINGS: [string, string][] = [
  ["planned_hours_per_day", "Planned hours per day (MTBF)"],
  ["kpi_period_days", "KPI period (days)"],
  ["similar_logs_threshold", "Similar logs for a fault card (Phase 2)"],
  ["similarity_cutoff", "Similarity cut-off (0 to 1)"],
  ["low_confidence_threshold", "Low-confidence threshold (0 to 1)"],
  ["audio_retention_days", "Keep audio (days)"],
  ["max_clarifying_questions", "Max clarifying questions"],
];

function SettingsTab() {
  const { toast } = useApp();
  const [settings, error, reload] = useLoad<Settings>("/api/admin/settings");
  const [shifts, setShifts] = useState<Settings["shifts"]>([]);
  useEffect(() => {
    if (settings) setShifts(settings.shifts);
  }, [settings]);
  if (!settings) return error ? <ErrorNote error={error} /> : <Spinner />;

  const saveNumber = async (key: string, value: string) => {
    try {
      await api.put(`/api/admin/settings/${key}`, { value: Number(value) });
      toast("Saved");
      reload();
    } catch (e) {
      toast(e instanceof Error ? e.message : "Failed");
    }
  };

  return (
    <>
      <section className="card">
        <h3>Shift calendar (plant time)</h3>
        {shifts.map((s, i) => (
          <div key={i} className="part-row">
            <input className="input qty" value={s.name} onChange={(e) => setShifts(shifts.map((x, j) => (j === i ? { ...x, name: e.target.value } : x)))} />
            <input className="input" type="time" value={s.start} onChange={(e) => setShifts(shifts.map((x, j) => (j === i ? { ...x, start: e.target.value } : x)))} />
            <input className="input" type="time" value={s.end} onChange={(e) => setShifts(shifts.map((x, j) => (j === i ? { ...x, end: e.target.value } : x)))} />
          </div>
        ))}
        <button
          className="btn btn-primary"
          onClick={async () => {
            try {
              await api.put("/api/admin/settings/shifts", { value: shifts });
              toast("Saved");
            } catch (e) {
              toast(e instanceof Error ? e.message : "Failed");
            }
          }}
        >
          Save shifts
        </button>
      </section>
      <section className="card">
        {NUMBER_SETTINGS.map(([key, label]) => (
          <label key={key} className="field">
            <span>{label}</span>
            <input className="input" defaultValue={String(settings[key])} inputMode="decimal" onBlur={(e) => void saveNumber(key, e.target.value)} />
          </label>
        ))}
      </section>
    </>
  );
}

function ExportTab() {
  const [since, setSince] = useState("");
  const [until, setUntil] = useState("");
  const [zone, setZone] = useState("");
  const [error, setError] = useState<unknown>(null);
  const run = async () => {
    const q = new URLSearchParams();
    if (since) q.set("since", since);
    if (until) q.set("until", until);
    if (zone) q.set("zone", zone);
    try {
      await downloadFile(`/api/export/logs.xlsx?${q}`, `thunai-logs-${since || "all"}-${until || "today"}.xlsx`);
    } catch (e) {
      setError(e);
    }
  };
  return (
    <section className="card">
      <h3>Excel export: logs and KPIs</h3>
      <div className="grid-2">
        <label className="field">
          <span>From</span>
          <input className="input" type="date" value={since} onChange={(e) => setSince(e.target.value)} />
        </label>
        <label className="field">
          <span>To</span>
          <input className="input" type="date" value={until} onChange={(e) => setUntil(e.target.value)} />
        </label>
      </div>
      <input className="input" placeholder="Zone (optional)" value={zone} onChange={(e) => setZone(e.target.value)} />
      <ErrorNote error={error} />
      <button className="btn btn-primary" onClick={() => void run()}>
        <Icon name="download" /> Download .xlsx
      </button>
    </section>
  );
}

interface Usage {
  days: number;
  sessions: number;
  total_cost_usd: number;
  cost_per_100_sessions_usd: number | null;
  by_purpose: { purpose: string; model: string; calls: number; input_tokens: number; output_tokens: number; cost_usd: number; ok: number }[];
}

function UsageTab() {
  const [usage, error] = useLoad<Usage>("/api/admin/ai-usage?days=30");
  if (!usage) return error ? <ErrorNote error={error} /> : <Spinner />;
  return (
    <>
      <div className="kpis">
        <div className="kpi">
          <span className="kpi-value">{usage.sessions}</span>
          <span className="kpi-label">Sessions (30 days)</span>
        </div>
        <div className="kpi">
          <span className="kpi-value">${usage.total_cost_usd.toFixed(2)}</span>
          <span className="kpi-label">AI cost</span>
        </div>
        <div className="kpi">
          <span className="kpi-value">{usage.cost_per_100_sessions_usd != null ? `$${usage.cost_per_100_sessions_usd}` : "–"}</span>
          <span className="kpi-label">per 100 sessions</span>
        </div>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>Purpose</th>
            <th>Model</th>
            <th>Calls</th>
            <th>Tokens in/out</th>
            <th>Cost</th>
          </tr>
        </thead>
        <tbody>
          {usage.by_purpose.map((r) => (
            <tr key={`${r.purpose}-${r.model}`}>
              <td>{r.purpose}</td>
              <td className="mono">{r.model}</td>
              <td>
                {r.ok}/{r.calls}
              </td>
              <td>
                {r.input_tokens} / {r.output_tokens}
              </td>
              <td>${r.cost_usd.toFixed(4)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

interface AuditRow {
  id: number;
  at: string;
  user: string;
  entity: string;
  entity_id: string;
  action: string;
  before: unknown;
  after: unknown;
}

function AuditTab() {
  const [rows, error] = useLoad<AuditRow[]>("/api/admin/audit?limit=200");
  return (
    <>
      <ErrorNote error={error} />
      <table className="table">
        <thead>
          <tr>
            <th>When</th>
            <th>Who</th>
            <th>What</th>
            <th>Change</th>
          </tr>
        </thead>
        <tbody>
          {rows?.map((r) => (
            <tr key={r.id}>
              <td className="small">{new Date(r.at).toLocaleString("en-IN")}</td>
              <td>{r.user}</td>
              <td>
                {r.entity} {r.entity_id} · {r.action}
              </td>
              <td className="mono small">{r.after ? JSON.stringify(r.after).slice(0, 120) : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
