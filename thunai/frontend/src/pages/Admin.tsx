// Admin console for maintenance engineering (English UI). All changes are written to the audit trail.
import { useCallback, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, downloadFile, openFile } from "../api";
import type { CopilotUsage, DocumentInfo, IntegrationKey, Machine, User } from "../api";
import { ErrorNote, Header, Icon, Page, Spinner, formatTime } from "../components";
import { useApp } from "../state";

const TABS = [
  ["machines", "Machines"],
  ["import", "Import"],
  ["documents", "Documents"],
  ["integrations", "Integrations"],
  ["users", "Users"],
  ["glossary", "Glossary"],
  ["settings", "Settings"],
  ["export", "Export"],
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
        {tab === "documents" && <DocumentsTab />}
        {tab === "integrations" && <IntegrationsTab />}
        {tab === "users" && <UsersTab />}
        {tab === "glossary" && <GlossaryTab />}
        {tab === "settings" && <SettingsTab />}
        {tab === "export" && <ExportTab />}
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
  const upload = async (kind: "machines" | "logs" | "parts", file: File | undefined) => {
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
      <section className="card">
        <h3>Spare parts and stock (Excel or CSV)</h3>
        <p className="muted">
          A stock list from the stores system. Rows are matched by part number; Thunai never changes stock itself. Fill
          machine_type or machine_no so the part shows for the right machines.
        </p>
        <div className="row-wrap">
          <button className="btn btn-ghost" onClick={() => void downloadFile("/api/admin/templates/parts.xlsx", "thunai-parts-template.xlsx")}>
            <Icon name="download" /> Template
          </button>
          <label className="btn btn-primary file-btn">
            Upload .xlsx / .csv
            <input type="file" accept=".xlsx,.csv" hidden onChange={(e) => void upload("parts", e.target.files?.[0])} />
          </label>
        </div>
      </section>
      <ErrorNote error={error} />
      {result !== null && <pre className="summary">{JSON.stringify(result, null, 2)}</pre>}
    </>
  );
}

const SCOPES = [
  ["alarms", "Alarms (PLC / SCADA)"],
  ["parts", "Spare parts stock"],
] as const;

/** Integration keys for PLC / SCADA gateways and the stores system (SPEC 12.1). */
function IntegrationsTab() {
  const { toast } = useApp();
  const [keys, keysError, reloadKeys] = useLoad<IntegrationKey[]>("/api/admin/integration-keys");
  const [keyForm, setKeyForm] = useState({ name: "", scopes: ["alarms"] as string[] });
  const [secret, setSecret] = useState<{ label: string; value: string } | null>(null);
  const [error, setError] = useState<unknown>(null);

  const toggleIn = (list: string[], value: string) => (list.includes(value) ? list.filter((v) => v !== value) : [...list, value]);
  const act = async (fn: () => Promise<unknown>, done?: string) => {
    setError(null);
    try {
      await fn();
      if (done) toast(done);
    } catch (e) {
      setError(e);
    }
  };

  return (
    <>
      <CopilotCard />
      <p className="muted">
        Connect PLC / SCADA gateways (machine alarms) and the stores system (spare-parts stock). API reference:{" "}
        <a href="/api/docs#/integrations">/api/docs</a>.
        Calls send the key in the <code>X-Thunai-Key</code> header.
      </p>
      <ErrorNote error={error ?? keysError} />
      {secret && (
        <div className="note note-warn" role="alert">
          <strong>{secret.label}: copy it now. It is shown only once.</strong>
          <p className="mono secret">{secret.value}</p>
          <div className="row-wrap">
            <button className="btn btn-ghost btn-small" onClick={() => void navigator.clipboard?.writeText(secret.value).then(() => toast("Copied"))}>
              Copy
            </button>
            <button className="btn btn-ghost btn-small" onClick={() => setSecret(null)}>
              Done
            </button>
          </div>
        </div>
      )}

      <section className="card">
        <h3>Integration keys</h3>
        <Form
          onSubmit={async () => {
            const k = await api.post<IntegrationKey>("/api/admin/integration-keys", keyForm);
            setSecret({ label: `Key for ${k.name}`, value: k.token ?? "" });
            setKeyForm({ name: "", scopes: ["alarms"] });
            reloadKeys();
          }}
        >
          <label className="field">
            <span>System name</span>
            <input className="input" value={keyForm.name} placeholder="e.g. SCADA gateway Zone 1" onChange={(e) => setKeyForm({ ...keyForm, name: e.target.value })} required />
          </label>
          <fieldset className="field">
            <legend>Allowed to</legend>
            {SCOPES.map(([value, label]) => (
              <label key={value} className="check-row">
                <input type="checkbox" checked={keyForm.scopes.includes(value)} onChange={() => setKeyForm({ ...keyForm, scopes: toggleIn(keyForm.scopes, value) })} />
                <span>{label}</span>
              </label>
            ))}
          </fieldset>
        </Form>
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Scopes</th>
              <th>Last used</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {keys?.map((k) => (
              <tr key={k.id} className={k.active ? "" : "row-inactive"}>
                <td>
                  {k.name}
                  <div className="mono small muted">{k.key_prefix}…</div>
                </td>
                <td className="small">{k.scopes.join(", ")}</td>
                <td className="small">{k.last_used_at ? new Date(k.last_used_at).toLocaleString("en-IN") : "never"}</td>
                <td>
                  <button className="btn btn-ghost btn-small" onClick={() => void act(async () => { await api.patch(`/api/admin/integration-keys/${k.id}`, { active: !k.active }); reloadKeys(); })}>
                    {k.active ? "Deactivate" : "Activate"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

    </>
  );
}

const KINDS = [
  ["manual", "Manual"],
  ["sop", "SOP"],
  ["drawing", "Drawing"],
  ["alarm_list", "Alarm list (Excel or CSV)"],
  ["other", "Other"],
] as const;

function DocumentsTab() {
  const { toast } = useApp();
  const [docs, error, reload] = useLoad<DocumentInfo[]>("/api/documents?include_inactive=true");
  const [machines] = useLoad<Machine[]>("/api/machines?limit=1000");
  const [form, setForm] = useState({ title: "", kind: "manual", scope: "machine", machine_no: "", machine_type: "" });
  const [file, setFile] = useState<File | null>(null);
  const [uploadError, setUploadError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const types = [...new Set((machines ?? []).map((m) => m.machine_type).filter(Boolean))].sort();

  const upload = async () => {
    if (!file) return;
    setBusy(true);
    setUploadError(null);
    const body = new FormData();
    body.append("file", file);
    body.append("title", form.title || file.name);
    body.append("kind", form.kind);
    if (form.scope === "machine") body.append("machine_no", form.machine_no);
    else body.append("machine_type", form.machine_type);
    try {
      await api.upload("/api/documents", body);
      toast("Uploaded. Text is extracted in the background.");
      setFile(null);
      setForm({ ...form, title: "" });
      setTimeout(reload, 1500);
    } catch (e) {
      setUploadError(e);
    } finally {
      setBusy(false);
    }
  };

  const toggle = async (d: DocumentInfo) => {
    await api.patch(`/api/documents/${d.id}`, { active: !d.active });
    reload();
  };

  return (
    <>
      <section className="card">
        <h3>Upload a manual, SOP, drawing or alarm list</h3>
        <p className="muted small">
          PDF text is read page by page (scanned drawings are stored but not read). Alarm lists need an alarm_code column;
          message, cause and remedy are optional.{" "}
          <button className="btn btn-ghost btn-small" onClick={() => void downloadFile("/api/admin/templates/alarms.xlsx", "thunai-alarms-template.xlsx")}>
            <Icon name="download" size={16} /> Alarm list template
          </button>
        </p>
        <input className="input" placeholder="Title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
        <select className="input" value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
          {KINDS.map(([k, label]) => (
            <option key={k} value={k}>
              {label}
            </option>
          ))}
        </select>
        <div className="segmented" role="radiogroup" aria-label="Applies to">
          {[
            ["machine", "One machine"],
            ["type", "Machine type"],
          ].map(([k, label]) => (
            <button key={k} role="radio" aria-checked={form.scope === k} className={form.scope === k ? "on" : ""} onClick={() => setForm({ ...form, scope: k })}>
              {label}
            </button>
          ))}
        </div>
        {form.scope === "machine" ? (
          <select className="input" value={form.machine_no} onChange={(e) => setForm({ ...form, machine_no: e.target.value })}>
            <option value="">Choose machine</option>
            {machines?.map((m) => (
              <option key={m.id} value={m.machine_no}>
                {m.machine_no} · {m.name}
              </option>
            ))}
          </select>
        ) : (
          <select className="input" value={form.machine_type} onChange={(e) => setForm({ ...form, machine_type: e.target.value })}>
            <option value="">Choose machine type</option>
            {types.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        )}
        <input className="input" type="file" accept=".pdf,.txt,.md,.csv,.xlsx,image/*" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        <ErrorNote error={uploadError} />
        <button className="btn btn-primary" disabled={busy || !file || (form.scope === "machine" ? !form.machine_no : !form.machine_type)} onClick={() => void upload()}>
          Upload
        </button>
      </section>
      <ErrorNote error={error} />
      <table className="table">
        <thead>
          <tr>
            <th>Title</th>
            <th>For</th>
            <th>Status</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {docs?.map((d) => (
            <tr key={d.id} className={d.active === false ? "inactive" : ""}>
              <td>
                <button className="link-btn" onClick={() => void openFile(`/api/documents/${d.id}/file`)}>
                  {d.title}
                </button>
                <div className="muted small">
                  {d.kind.replace("_", " ")}
                  {d.pages ? ` · ${d.pages} ${d.pages === 1 ? "page" : "pages"}` : ""}
                </div>
              </td>
              <td>{d.scope === "machine" ? d.machine_no : d.type_name}</td>
              <td>{d.status === "no_text" ? "stored (no text)" : d.status}</td>
              <td>
                <button className="btn btn-small" onClick={() => void toggle(d)}>
                  {d.active === false ? "Activate" : "Deactivate"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

function UsersTab() {
  const { toast } = useApp();
  const [users, error, reload] = useLoad<User[]>("/api/admin/users");
  const blank = { employee_id: "", name: "", role: "technician", zone: "", preferred_language: "ta", phone: "", pin: "", entra_upn: "" };
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
  const setAccount = async (u: User) => {
    const upn = window.prompt(`Microsoft account for ${u.name} (e.g. name@eaton.com). Leave empty to remove.`, u.entra_upn ?? "");
    if (upn === null) return;
    try {
      await api.patch(`/api/admin/users/${u.id}`, { entra_upn: upn.trim() });
      toast(upn.trim() ? "Microsoft account saved" : "Microsoft account removed");
      reload();
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
          <input className="input" type="email" placeholder="Microsoft account, for Thunai in Teams (optional)" value={form.entra_upn} onChange={set("entra_upn")} />
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
                {u.entra_upn && (
                  <span className="user-account small">
                    <span className="mono">{u.entra_upn}</span>{" "}
                    <span className={`chip ${u.entra_linked ? "chip-verified" : ""}`}>{u.entra_linked ? "linked" : "not used yet"}</span>
                  </span>
                )}
              </td>
              <td>{u.role}</td>
              <td>{u.zone}</td>
              <td className="row-wrap">
                <button className="btn btn-small" onClick={() => void resetPin(u)}>
                  PIN
                </button>
                <button className="btn btn-small" onClick={() => void setAccount(u)}>
                  Microsoft
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
  ["alarm_prefill_hours", "Machine alarm pre-fills a log for (hours) (Phase 3)"],
  ["skill_min_events", "Minimum events before a skill figure is shown"],
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

const TOOL_NAMES: Record<string, string> = {
  whoAmI: "Who is signed in",
  findMachines: "Find machines",
  getMachine: "Machine status",
  lookupAlarm: "Alarm meaning",
  startTroubleshooting: "Start troubleshooting",
  answerQuestions: "Answer questions",
  getSession: "Session state",
  reportStep: "Step result",
  callSupervisor: "Call supervisor",
  closeSession: "Close session",
  createLog: "Log a fix",
  searchParts: "Spare parts",
  checkSafety: "Safety check",
  listLogsToTranslate: "Logs to translate",
  saveTranslations: "Save translations",
};

/** Microsoft Copilot agent (SPEC 13): set-up state, linked people and tool calls over 30 days. */
function CopilotCard() {
  const [usage, error] = useLoad<CopilotUsage>("/api/admin/copilot-usage?days=30");
  if (!usage) return error ? <ErrorNote error={error} /> : <Spinner />;
  const missing = [
    !usage.enabled && "COPILOT_ENABLED=true",
    !usage.tenant_set && "ENTRA_TENANT_ID",
    !usage.audience_set && "ENTRA_AUDIENCE",
  ].filter(Boolean);
  const inTeams = usage.sessions_by_channel.copilot ?? 0;
  const inApp = usage.sessions_by_channel.app ?? 0;
  return (
    <section className="card">
      <div className="row-between">
        <h3>Microsoft Copilot</h3>
        <span className={`chip ${usage.ready ? "chip-verified" : "chip-draft"}`}>{usage.ready ? "Ready" : "Not set up"}</span>
      </div>
      {usage.ready ? (
        <p className="muted">
          Technicians use the Thunai agent in Teams. Tokens need the <code>{usage.scope}</code> scope.{" "}
          {usage.teams_url ? (
            <a href={usage.teams_url} target="_blank" rel="noreferrer">
              Open the agent
            </a>
          ) : (
            "Set COPILOT_TEAMS_URL to show the Teams link on the home screen."
          )}
        </p>
      ) : (
        <p className="muted">
          Set {missing.join(", ")} in <code>.env</code> and restart. Steps: <code>copilot/SETUP.md</code>.
        </p>
      )}
      <div className="kpis">
        <div className="kpi">
          <span className="kpi-value">
            {usage.users_linked}/{usage.users_with_account}
          </span>
          <span className="kpi-label">Microsoft accounts used / entered</span>
        </div>
        <div className="kpi">
          <span className="kpi-value">{usage.calls}</span>
          <span className="kpi-label">Tool calls (30 days)</span>
        </div>
        <div className="kpi">
          <span className="kpi-value">
            {inTeams}/{inTeams + inApp}
          </span>
          <span className="kpi-label">Sessions in Teams</span>
        </div>
      </div>
      {usage.users_with_account < usage.users_active && (
        <p className="muted small">
          {usage.users_active - usage.users_with_account} active users have no Microsoft account yet (Users tab).
        </p>
      )}
      {usage.by_tool.length > 0 && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Tool</th>
                <th className="num">Calls</th>
                <th className="num">OK</th>
                <th className="num">People</th>
                <th>Last</th>
              </tr>
            </thead>
            <tbody>
              {usage.by_tool.map((r) => (
                <tr key={r.operation}>
                  <td>{TOOL_NAMES[r.operation] ?? r.operation}</td>
                  <td className="num">{r.calls}</td>
                  <td className="num">{r.ok}</td>
                  <td className="num">{r.users}</td>
                  <td className="small">{r.last_at ? formatTime(r.last_at) : "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {usage.recent_errors.length > 0 && (
        <>
          <h4>Recent errors</h4>
          <ul className="plain-list small">
            {usage.recent_errors.map((e, i) => (
              <li key={i}>
                {formatTime(e.at)} · {TOOL_NAMES[e.operation] ?? e.operation} · {e.status_code}
                {e.status_code === 401 && " (sign-in not accepted)"}
                {e.status_code === 403 && " (account not linked or not allowed)"}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
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
