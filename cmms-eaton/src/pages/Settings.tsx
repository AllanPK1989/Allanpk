import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Icon } from "../components/icons";
import { useToast } from "../components/Toast";
import { Badge, Button, Card, ChipSelect, Confirm, Empty, Field, KV, Notice, PageHeader, Search, Tabs, usePaged } from "../components/ui";
import { formatDateTime, shiftHours } from "../lib/dates";
import { downloadText, downloadWorkbook, snapshotSheets } from "../lib/excel";
import { newId, nowIso } from "../lib/ids";
import { can } from "../lib/permissions";
import { STORAGE_MODES, type StorageMode } from "../store/adapters";
import { migrate, SNAPSHOT_FILE } from "../store/snapshot";
import { useCurrentUser, useStore } from "../store/StoreProvider";
import { SHIFTS, type Line, type Settings as PlantSettings, type Shift } from "../types";

type Tab = "plant" | "shifts" | "lines" | "lists" | "storage" | "backup" | "audit";

export function Settings() {
  const user = useCurrentUser();
  const [params, setParams] = useSearchParams();
  const tabs = [
    { id: "plant" as Tab, label: "Plant", show: can(user, "settings.manage") },
    { id: "shifts" as Tab, label: "Shifts", show: can(user, "settings.manage") },
    { id: "lines" as Tab, label: "Lines", show: can(user, "settings.manage") },
    { id: "lists" as Tab, label: "Lists", show: can(user, "settings.manage") },
    { id: "storage" as Tab, label: "Data storage", show: can(user, "storage.manage") },
    { id: "backup" as Tab, label: "Backup & export", show: can(user, "data.export") },
    { id: "audit" as Tab, label: "Audit log", show: can(user, "audit.view") },
  ].filter((t) => t.show);
  const requested = params.get("tab") as Tab | null;
  const tab = tabs.some((t) => t.id === requested) ? (requested as Tab) : tabs[0]?.id;

  if (!tab) {
    return (
      <Notice tone="warning" icon="lock">
        Your role has no settings to manage.
      </Notice>
    );
  }

  return (
    <div>
      <PageHeader title="Settings" />
      <Tabs<Tab> tabs={tabs} active={tab} onChange={(t) => setParams({ tab: t }, { replace: true })} />
      {tab === "plant" && <PlantTab />}
      {tab === "shifts" && <ShiftsTab />}
      {tab === "lines" && <LinesTab />}
      {tab === "lists" && <ListsTab />}
      {tab === "storage" && <StorageTab />}
      {tab === "backup" && <BackupTab />}
      {tab === "audit" && <AuditTab />}
    </div>
  );
}

function useSettingsForm() {
  const { snapshot, mutate } = useStore();
  const user = useCurrentUser();
  const toast = useToast();
  const save = (patch: Partial<PlantSettings>, summary: string) => {
    mutate(
      (d) => {
        Object.assign(d.settings, patch);
      },
      { entity: "settings", entityId: "plant", action: "update", summary: `${summary} by ${user.name}` },
    );
    toast.success("Settings saved");
  };
  return { settings: snapshot.settings, save };
}

function PlantTab() {
  const { settings, save } = useSettingsForm();
  const [f, setF] = useState({ ...settings });
  useEffect(() => setF({ ...settings }), [settings]);
  const set = <K extends keyof PlantSettings>(k: K, v: PlantSettings[K]) => setF((s) => ({ ...s, [k]: v }));
  return (
    <Card title="Plant">
      <div className="form-grid">
        <Field label="Plant name">
          <input value={f.plantName} onChange={(e) => set("plantName", e.target.value)} />
        </Field>
        <Field label="Site code">
          <input value={f.siteCode} onChange={(e) => set("siteCode", e.target.value)} />
        </Field>
        <Field label="Time zone" hint="Informational; dates use the device clock">
          <input value={f.timezone} onChange={(e) => set("timezone", e.target.value)} />
        </Field>
        <Field label="Currency code">
          <input value={f.currency} onChange={(e) => set("currency", e.target.value.toUpperCase())} maxLength={3} />
        </Field>
        <Field label="Work order prefix" hint="Numbers look like WO-2026-00042">
          <input value={f.woPrefix} onChange={(e) => set("woPrefix", e.target.value.toUpperCase())} />
        </Field>
        <Field label="Planned production hours per day" hint="Plant-wide MTBF and availability; two shifts = 16">
          <input type="number" min={1} max={24} value={f.plannedHoursPerDay} onChange={(e) => set("plannedHoursPerDay", Number(e.target.value) || 16)} />
        </Field>
        <Field label="Default PM lead (days)" hint="How many days before due a PM work order is generated">
          <input type="number" min={0} value={f.pmLeadDays} onChange={(e) => set("pmLeadDays", Number(e.target.value) || 0)} />
        </Field>
      </div>
      <div className="mt-16">
        <Button variant="primary" onClick={() => save({ plantName: f.plantName.trim(), siteCode: f.siteCode.trim(), timezone: f.timezone.trim(), currency: f.currency.trim() || "INR", woPrefix: f.woPrefix.trim() || "WO", plannedHoursPerDay: f.plannedHoursPerDay, pmLeadDays: f.pmLeadDays }, "Plant settings updated")}>
          Save
        </Button>
      </div>
    </Card>
  );
}

function ShiftsTab() {
  const { settings, save } = useSettingsForm();
  const { snapshot } = useStore();
  const [shifts, setShifts] = useState(settings.shifts);
  const [defaults, setDefaults] = useState<Shift[]>(settings.defaultLineShifts);
  useEffect(() => {
    setShifts(settings.shifts);
    setDefaults(settings.defaultLineShifts);
  }, [settings]);
  const linesWithC = snapshot.lines.filter((l) => l.active && l.shifts.includes("C"));
  return (
    <div className="stack">
      <Card title="Shift timings">
        <p className="text-2">Shifts A and B run plant-wide. Shift C runs only on the lines flagged under Lines. Breakdowns are stamped with the shift from the stop time.</p>
        <div className="form-grid">
          {SHIFTS.map((s) => (
            <div key={s} className="flex">
              <strong style={{ width: 60 }}>Shift {s}</strong>
              <Field label="Start">
                <input type="time" value={shifts[s].start} onChange={(e) => setShifts({ ...shifts, [s]: { ...shifts[s], start: e.target.value } })} />
              </Field>
              <Field label="End">
                <input type="time" value={shifts[s].end} onChange={(e) => setShifts({ ...shifts, [s]: { ...shifts[s], end: e.target.value } })} />
              </Field>
              <span className="small muted nowrap">{shiftHours(shifts[s]).toFixed(1)} h</span>
            </div>
          ))}
        </div>
        <Field label="Shifts a new line runs by default" className="mt-16">
          <ChipSelect options={SHIFTS.map((s) => ({ value: s, label: `Shift ${s}` }))} value={defaults} onChange={setDefaults} />
        </Field>
        <div className="mt-16 flex">
          <Button variant="primary" onClick={() => save({ shifts, defaultLineShifts: defaults.length ? defaults : ["A", "B"] }, "Shift timings updated")}>
            Save
          </Button>
          <span className="small muted">Lines running shift C: {linesWithC.length ? linesWithC.map((l) => l.code).join(", ") : "none"}</span>
        </div>
      </Card>
    </div>
  );
}

function LinesTab() {
  const { snapshot, mutate } = useStore();
  const user = useCurrentUser();
  const toast = useToast();
  const [rows, setRows] = useState<Line[]>(() => structuredClone(snapshot.lines));
  useEffect(() => setRows(structuredClone(snapshot.lines)), [snapshot.lines]);
  const update = (id: string, patch: Partial<Line>) => setRows((r) => r.map((l) => (l.id === id ? { ...l, ...patch } : l)));
  const add = () => {
    const now = nowIso();
    setRows((r) => [...r, { id: newId(), code: "", name: "", area: "", shifts: [...snapshot.settings.defaultLineShifts], active: true, createdAt: now, updatedAt: now }]);
  };
  const saveAll = () => {
    const cleaned = rows.map((l) => ({ ...l, code: l.code.trim().toUpperCase(), name: l.name.trim(), area: l.area.trim() })).filter((l) => l.code);
    const codes = new Set<string>();
    for (const l of cleaned) {
      if (codes.has(l.code)) return toast.error(`Line code ${l.code} is used twice`);
      codes.add(l.code);
    }
    mutate(
      (d) => {
        const now = nowIso();
        d.lines = cleaned.map((l) => {
          const existing = d.lines.find((x) => x.id === l.id);
          return { ...l, createdAt: existing?.createdAt ?? now, updatedAt: now };
        });
      },
      { entity: "line", entityId: "all", action: "update", summary: `Lines updated by ${user.name}` },
    );
    toast.success("Lines saved");
  };
  return (
    <Card title="Production lines" actions={<Button size="sm" icon="plus" onClick={add}>Add line</Button>} tight>
      <div className="table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th>Code</th>
              <th>Name</th>
              <th>Area</th>
              <th>Shifts</th>
              <th>Active</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((l) => (
              <tr key={l.id}>
                <td style={{ width: 110 }}>
                  <input value={l.code} onChange={(e) => update(l.id, { code: e.target.value })} placeholder="L1" aria-label="Code" />
                </td>
                <td>
                  <input value={l.name} onChange={(e) => update(l.id, { name: e.target.value })} placeholder="Line name" aria-label="Name" />
                </td>
                <td>
                  <input value={l.area} onChange={(e) => update(l.id, { area: e.target.value })} placeholder="Area" aria-label="Area" />
                </td>
                <td>
                  <ChipSelect options={SHIFTS.map((s) => ({ value: s, label: s }))} value={l.shifts} onChange={(v) => update(l.id, { shifts: SHIFTS.filter((s) => v.includes(s)) })} />
                </td>
                <td>
                  <input type="checkbox" checked={l.active} onChange={(e) => update(l.id, { active: e.target.checked })} aria-label="Active" />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="table-foot">
        <span>Tick C only for lines that run the night shift.</span>
        <Button variant="primary" onClick={saveAll}>
          Save lines
        </Button>
      </div>
    </Card>
  );
}

function ListsTab() {
  const { settings, save } = useSettingsForm();
  const [codes, setCodes] = useState(settings.failureCodes.join("\n"));
  const [assetCats, setAssetCats] = useState(settings.assetCategories.join("\n"));
  const [partCats, setPartCats] = useState(settings.partCategories.join("\n"));
  useEffect(() => {
    setCodes(settings.failureCodes.join("\n"));
    setAssetCats(settings.assetCategories.join("\n"));
    setPartCats(settings.partCategories.join("\n"));
  }, [settings]);
  const lines = (s: string) => s.split("\n").map((x) => x.trim()).filter(Boolean);
  return (
    <Card title="Pick lists">
      <div className="grid grid-3">
        <Field label="Failure codes" hint="One per line">
          <textarea rows={10} value={codes} onChange={(e) => setCodes(e.target.value)} />
        </Field>
        <Field label="Asset categories" hint="One per line">
          <textarea rows={10} value={assetCats} onChange={(e) => setAssetCats(e.target.value)} />
        </Field>
        <Field label="Part categories" hint="One per line">
          <textarea rows={10} value={partCats} onChange={(e) => setPartCats(e.target.value)} />
        </Field>
      </div>
      <div className="mt-16">
        <Button variant="primary" onClick={() => save({ failureCodes: lines(codes), assetCategories: lines(assetCats), partCategories: lines(partCats) }, "Pick lists updated")}>
          Save
        </Button>
      </div>
    </Card>
  );
}

function StorageTab() {
  const { storage, setStorageMode, connectFolder, reconnectFolder, disconnectFolder, reloadFromStorage, snapshot, mutate } = useStore();
  const user = useCurrentUser();
  const toast = useToast();
  const [sp, setSp] = useState(snapshot.settings.sharepoint);
  useEffect(() => setSp(snapshot.settings.sharepoint), [snapshot.settings.sharepoint]);

  const choose = async (mode: StorageMode) => {
    await setStorageMode(mode);
    if (mode === "local") toast.success("Data is kept on this device");
  };

  return (
    <div className="stack">
      <Card title="Where the data lives">
        <p className="text-2">
          The whole plant database is one file, <code>{SNAPSHOT_FILE}</code>. Pick where it is kept on this device. The choice is per device; the data itself moves with Backup &amp; export.
        </p>
        <div className="grid grid-3">
          {STORAGE_MODES.map((m) => (
            <button key={m.mode} type="button" className="stat" style={storage.mode === m.mode ? { borderColor: "var(--accent)", boxShadow: "0 0 0 2px var(--accent-weak)" } : undefined} onClick={() => choose(m.mode)} aria-pressed={storage.mode === m.mode}>
              <span className="label flex">
                <Icon name={m.mode === "local" ? "lock" : m.mode === "folder" ? "folder" : "cloud"} size={16} /> {m.label}
                {storage.mode === m.mode && <Badge tone="accent">Selected</Badge>}
              </span>
              <span className="hint">{m.description}</span>
            </button>
          ))}
        </div>
      </Card>

      {storage.mode === "folder" && (
        <Card title="Shared folder">
          {!storage.folderSupported ? (
            <Notice tone="warning" icon="alert">
              This browser cannot open folders. Use Microsoft Edge or Google Chrome on a Windows or Mac PC. Phones keep using "This device".
            </Notice>
          ) : (
            <>
              <KV
                items={[
                  { k: "Folder", v: storage.folderName ?? <span className="muted">Not chosen yet</span> },
                  { k: "Status", v: storage.needsReconnect ? <Badge tone="warning">Needs permission</Badge> : storage.folderName ? <Badge tone="good">Connected</Badge> : <Badge>Not connected</Badge> },
                  { k: "Last saved", v: formatDateTime(storage.lastSavedAt) },
                ]}
              />
              <div className="flex flex-wrap mt-16">
                <Button variant="primary" icon="folder" onClick={connectFolder}>
                  {storage.folderName ? "Choose another folder" : "Choose folder…"}
                </Button>
                {storage.needsReconnect && (
                  <Button icon="refresh" onClick={reconnectFolder}>
                    Reconnect
                  </Button>
                )}
                {storage.folderName && !storage.needsReconnect && (
                  <>
                    <Button icon="refresh" onClick={reloadFromStorage}>
                      Reload from folder
                    </Button>
                    <Button variant="ghost" onClick={disconnectFolder}>
                      Disconnect
                    </Button>
                  </>
                )}
              </div>
            </>
          )}
          <div className="mt-16">
            <Notice tone="accent" icon="info">
              <strong>Using the Eaton SharePoint folder today</strong>
              <ol style={{ margin: "6px 0 0", paddingLeft: 18 }}>
                <li>Open the document library on eaton.sharepoint.com and click <em>Sync</em> so OneDrive keeps a copy on this PC.</li>
                <li>Click <em>Choose folder…</em> above and pick that synced folder. The first PC copies its data into the folder; later PCs load from it.</li>
                <li>Repeat on every PC that uses CMMS_Eaton. Changes made elsewhere are picked up within about 15 seconds.</li>
              </ol>
              <div className="small mt-8">Two people saving at the same second can produce a OneDrive conflict copy; the newest file wins. A direct SharePoint connection (below) will remove that limit.</div>
            </Notice>
          </div>
        </Card>
      )}

      {storage.mode === "sharepoint" && (
        <Card title="SharePoint online (prepared for a later release)">
          <Notice tone="warning" icon="cloud">
            Not connected yet. Until Eaton IT provides an app registration, data stays on this device; use <em>Shared folder</em> with the synced library for shared data. The details below are stored so the connection can be switched on without re-entering them. See <code>docs/SHAREPOINT.md</code>.
          </Notice>
          <div className="form-grid mt-16">
            <Field label="Site URL" hint="e.g. https://eaton.sharepoint.com/sites/PlantMaintenance">
              <input value={sp.siteUrl} onChange={(e) => setSp({ ...sp, siteUrl: e.target.value })} />
            </Field>
            <Field label="Library folder path" hint="e.g. Shared Documents/CMMS_Eaton">
              <input value={sp.libraryPath} onChange={(e) => setSp({ ...sp, libraryPath: e.target.value })} />
            </Field>
            <Field label="Entra tenant ID">
              <input value={sp.tenantId} onChange={(e) => setSp({ ...sp, tenantId: e.target.value })} />
            </Field>
            <Field label="App (client) ID">
              <input value={sp.clientId} onChange={(e) => setSp({ ...sp, clientId: e.target.value })} />
            </Field>
          </div>
          <div className="mt-16">
            <Button
              variant="primary"
              onClick={() => {
                mutate(
                  (d) => {
                    d.settings.sharepoint = { siteUrl: sp.siteUrl.trim(), libraryPath: sp.libraryPath.trim(), tenantId: sp.tenantId.trim(), clientId: sp.clientId.trim() };
                  },
                  { entity: "settings", entityId: "sharepoint", action: "update", summary: `SharePoint connection details saved by ${user.name}` },
                );
                toast.success("SharePoint details saved");
              }}
            >
              Save details
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}

function BackupTab() {
  const { snapshot, replaceSnapshot, resetToDemo, startFresh } = useStore();
  const user = useCurrentUser();
  const toast = useToast();
  const fileRef = useRef<HTMLInputElement>(null);
  const [pending, setPending] = useState<ReturnType<typeof migrate>>(null);
  const [confirmReset, setConfirmReset] = useState<"demo" | "fresh" | null>(null);
  const stamp = new Date().toISOString().slice(0, 16).replace(/[:T]/g, "-");

  const restore = async (file: File) => {
    try {
      const parsed = migrate(JSON.parse(await file.text()));
      if (!parsed) return toast.error("That file is not a CMMS_Eaton backup");
      setPending(parsed);
    } catch {
      toast.error("Could not read the file");
    }
  };

  return (
    <div className="stack">
      <Card title="Export">
        <div className="flex flex-wrap">
          <Button variant="primary" icon="download" onClick={() => downloadText(`CMMS_Eaton-backup-${stamp}.json`, JSON.stringify(snapshot), "application/json")}>
            Download backup (JSON)
          </Button>
          <Button icon="download" onClick={() => downloadWorkbook(`CMMS_Eaton-export-${stamp}.xlsx`, snapshotSheets(snapshot))}>
            Export everything to Excel
          </Button>
        </div>
        <p className="small muted mt-8">The JSON backup restores the complete database, including users. The Excel file is for reading and reporting.</p>
      </Card>
      {can(user, "data.import") && (
        <Card title="Restore">
          <Button icon="upload" onClick={() => fileRef.current?.click()}>
            Restore from backup…
          </Button>
          <input ref={fileRef} type="file" accept="application/json,.json" className="sr-only" onChange={(e) => { const f = e.target.files?.[0]; if (f) restore(f); e.target.value = ""; }} />
          <p className="small muted mt-8">Replaces everything on this device with the backup. Take a backup first if unsure.</p>
        </Card>
      )}
      {can(user, "storage.manage") && (
        <Card title="Reset">
          <div className="flex flex-wrap">
            <Button onClick={() => setConfirmReset("demo")}>Reset to sample data</Button>
            <Button variant="danger" onClick={() => setConfirmReset("fresh")}>
              Start fresh (empty plant)
            </Button>
          </div>
          <p className="small muted mt-8">Start fresh removes every record on this device and asks you to create the owner account again. Export a backup first.</p>
        </Card>
      )}
      <Confirm
        open={pending !== null}
        onClose={() => setPending(null)}
        title="Restore this backup?"
        text={pending ? `Backup from ${formatDateTime(pending.updatedAt)} with ${pending.workOrders.length} work orders, ${pending.assets.length} assets and ${pending.users.length} users. Current data on this device will be replaced.` : ""}
        confirmLabel="Restore"
        danger
        onConfirm={() => {
          if (!pending) return;
          replaceSnapshot(pending, { entity: "system", entityId: "restore", action: "restore", summary: `Backup restored by ${user.name}` });
          toast.success("Backup restored");
        }}
      />
      <Confirm
        open={confirmReset !== null}
        onClose={() => setConfirmReset(null)}
        title={confirmReset === "demo" ? "Replace everything with sample data?" : "Delete everything and start fresh?"}
        text="This cannot be undone. You will be signed out."
        confirmLabel={confirmReset === "demo" ? "Reset to sample data" : "Delete everything"}
        danger
        onConfirm={() => (confirmReset === "demo" ? resetToDemo() : startFresh())}
      />
    </div>
  );
}

function AuditTab() {
  const { snapshot, usersById } = useStore();
  const [q, setQ] = useState("");
  const [entity, setEntity] = useState("");
  const entities = useMemo(() => [...new Set(snapshot.audit.map((a) => a.entity))].sort(), [snapshot.audit]);
  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return snapshot.audit.filter((a) => (!entity || a.entity === entity) && (!needle || `${a.summary} ${a.action} ${usersById.get(a.userId ?? "")?.name ?? ""}`.toLowerCase().includes(needle)));
  }, [snapshot.audit, q, entity, usersById]);
  const paged = usePaged(rows, 100);
  return (
    <div>
      <div className="filters">
        <Search value={q} onChange={setQ} placeholder="Search the audit log" />
        <select value={entity} onChange={(e) => setEntity(e.target.value)} aria-label="Entity">
          <option value="">All entities</option>
          {entities.map((e) => (
            <option key={e} value={e}>
              {e}
            </option>
          ))}
        </select>
      </div>
      <Card tight>
        {rows.length === 0 ? (
          <Empty icon="history" title="No audit entries" />
        ) : (
          <>
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>When</th>
                    <th>Who</th>
                    <th>Entity</th>
                    <th>Action</th>
                    <th>Summary</th>
                  </tr>
                </thead>
                <tbody>
                  {paged.visible.map((a) => (
                    <tr key={a.id}>
                      <td className="nowrap">{formatDateTime(a.at)}</td>
                      <td>{a.userId ? (usersById.get(a.userId)?.name ?? "Unknown") : "System"}</td>
                      <td>{a.entity}</td>
                      <td>{a.action}</td>
                      <td>{a.summary}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="table-foot">
              <span>Showing {paged.visible.length} of {paged.total}</span>
              {paged.more && <Button size="sm" onClick={paged.showMore}>Show more</Button>}
            </div>
          </>
        )}
      </Card>
    </div>
  );
}
