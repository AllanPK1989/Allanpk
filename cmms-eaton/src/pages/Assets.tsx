import { useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AssetForm } from "../components/AssetForm";
import { useToast } from "../components/Toast";
import { Badge, Button, Card, Empty, PageHeader, PlanStateBadge, Search } from "../components/ui";
import { parseCsv } from "../lib/csv";
import { todayKey } from "../lib/dates";
import { downloadWorkbook, snapshotSheets } from "../lib/excel";
import { newId, nowIso } from "../lib/ids";
import { can } from "../lib/permissions";
import { planState, type PlanState } from "../lib/pm";
import { isOpenStatus } from "../lib/workorders";
import { useCurrentUser, useStore } from "../store/StoreProvider";
import type { Asset, AssetStatus, Criticality } from "../types";
import { ASSET_STATUS_LABELS } from "../types";

export function Assets() {
  const { snapshot, mutate, linesById } = useStore();
  const user = useCurrentUser();
  const navigate = useNavigate();
  const toast = useToast();
  const [q, setQ] = useState("");
  const [lineId, setLineId] = useState("");
  const [status, setStatus] = useState("");
  const [crit, setCrit] = useState("");
  const [showComponents, setShowComponents] = useState(true);
  const [formOpen, setFormOpen] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const today = todayKey();
  const manage = can(user, "asset.manage");

  const openCount = useMemo(() => {
    const m = new Map<string, number>();
    for (const w of snapshot.workOrders) if (w.assetId && isOpenStatus(w.status)) m.set(w.assetId, (m.get(w.assetId) ?? 0) + 1);
    return m;
  }, [snapshot.workOrders]);

  const nextPm = useMemo(() => {
    const m = new Map<string, { date: string; state: PlanState }>();
    for (const p of snapshot.pmPlans) {
      if (!p.active) continue;
      const asset = snapshot.assets.find((a) => a.id === p.assetId);
      const state = planState(p, asset, today);
      const cur = m.get(p.assetId);
      if (!cur || p.nextDueAt < cur.date) m.set(p.assetId, { date: p.nextDueAt, state });
    }
    return m;
  }, [snapshot.pmPlans, snapshot.assets, today]);

  const groups = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const matches = (a: Asset) => {
      if (lineId && a.lineId !== lineId) return false;
      if (status && a.status !== status) return false;
      if (crit && a.criticality !== crit) return false;
      if (needle && !`${a.assetNo} ${a.name} ${a.make} ${a.model} ${a.location} ${a.category}`.toLowerCase().includes(needle)) return false;
      return true;
    };
    const top = snapshot.assets.filter((a) => a.parentId === null).sort((a, b) => a.assetNo.localeCompare(b.assetNo));
    const byLine = new Map<string, { asset: Asset; children: Asset[] }[]>();
    for (const a of top) {
      const children = snapshot.assets.filter((c) => c.parentId === a.id).sort((x, y) => x.assetNo.localeCompare(y.assetNo));
      const childMatch = children.filter(matches);
      if (!matches(a) && childMatch.length === 0) continue;
      const key = a.lineId ?? "";
      byLine.set(key, [...(byLine.get(key) ?? []), { asset: a, children: showComponents ? (matches(a) ? children : childMatch) : [] }]);
    }
    return [...byLine.entries()].sort((a, b) => (linesById.get(a[0])?.code ?? "zzz").localeCompare(linesById.get(b[0])?.code ?? "zzz"));
  }, [snapshot.assets, q, lineId, status, crit, showComponents, linesById]);

  const importCsv = async (file: File) => {
    try {
      const rows = parseCsv(await file.text());
      if (rows.length === 0) return toast.error("The file has no rows");
      let created = 0;
      let updated = 0;
      const now = nowIso();
      mutate(
        (d) => {
          for (const r of rows) {
            const no = (r.asset_no ?? r.assetno ?? "").trim();
            if (!no) continue;
            const line = r.line ? d.lines.find((l) => l.code.toLowerCase() === r.line.toLowerCase()) : undefined;
            const parent = r.parent ? d.assets.find((a) => a.assetNo.toLowerCase() === r.parent.toLowerCase()) : undefined;
            const crit = (r.criticality || "B").toUpperCase();
            const st = (r.status || "running").toLowerCase();
            const data = {
              name: r.name || no,
              lineId: line?.id ?? parent?.lineId ?? null,
              parentId: parent?.id ?? null,
              category: r.category ?? "",
              make: r.make ?? "",
              model: r.model ?? "",
              serialNo: r.serial_no ?? "",
              criticality: (["A", "B", "C"].includes(crit) ? crit : "B") as Criticality,
              status: (["running", "down", "maintenance", "retired"].includes(st) ? st : "running") as AssetStatus,
              location: r.location ?? "",
              installDate: r.install_date || null,
              meterUnit: r.meter_unit ?? "",
              meterReading: Number(r.meter_reading) || 0,
              notes: r.notes ?? "",
              updatedAt: now,
            };
            const existing = d.assets.find((a) => a.assetNo.toLowerCase() === no.toLowerCase());
            if (existing) {
              Object.assign(existing, data);
              updated += 1;
            } else {
              d.sequences.asset += 1;
              d.assets.push({ id: newId(), assetNo: no, ...data, meterUpdatedAt: data.meterUnit ? now : null, specs: [], active: true, createdAt: now });
              created += 1;
            }
          }
        },
        { entity: "asset", entityId: "import", action: "import", summary: `Assets imported from ${file.name}` },
      );
      toast.success(`Import done: ${created} created, ${updated} updated`);
    } catch (err) {
      toast.error(`Import failed: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const total = snapshot.assets.filter((a) => a.active).length;
  const down = snapshot.assets.filter((a) => a.status === "down").length;

  return (
    <div>
      <PageHeader
        title="Assets"
        subtitle={`${total} active · ${down} down`}
        actions={
          <>
            <Link to="/assets/qr-sheet" className="btn">
              QR sheet
            </Link>
            {can(user, "data.export") && (
              <Button icon="download" onClick={() => downloadWorkbook("CMMS_Eaton-assets.xlsx", snapshotSheets(snapshot).filter((s) => s.name === "Assets"))}>
                Export
              </Button>
            )}
            {can(user, "data.import") && (
              <>
                <Button icon="upload" onClick={() => fileRef.current?.click()}>
                  Import CSV
                </Button>
                <input ref={fileRef} type="file" accept=".csv,text/csv" className="sr-only" onChange={(e) => { const f = e.target.files?.[0]; if (f) importCsv(f); e.target.value = ""; }} />
              </>
            )}
            {manage && (
              <Button variant="primary" icon="plus" onClick={() => setFormOpen(true)}>
                New asset
              </Button>
            )}
          </>
        }
      />
      <div className="filters">
        <Search value={q} onChange={setQ} placeholder="Search asset no, name, make, location" />
        <select value={lineId} onChange={(e) => setLineId(e.target.value)} aria-label="Line">
          <option value="">All lines</option>
          {snapshot.lines.map((l) => (
            <option key={l.id} value={l.id}>
              {l.code} · {l.name}
            </option>
          ))}
        </select>
        <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
          <option value="">Any status</option>
          {(Object.keys(ASSET_STATUS_LABELS) as AssetStatus[]).map((s) => (
            <option key={s} value={s}>
              {ASSET_STATUS_LABELS[s]}
            </option>
          ))}
        </select>
        <select value={crit} onChange={(e) => setCrit(e.target.value)} aria-label="Criticality">
          <option value="">Any criticality</option>
          <option value="A">A</option>
          <option value="B">B</option>
          <option value="C">C</option>
        </select>
        <label className="check small">
          <input type="checkbox" checked={showComponents} onChange={(e) => setShowComponents(e.target.checked)} /> Show components
        </label>
      </div>
      {groups.length === 0 ? (
        <Card>
          <Empty icon="box" title="No assets match" text={manage ? "Add machines one by one or import a CSV with columns asset_no, name, line, parent, category, make, model, serial_no, criticality, status, location, install_date, meter_unit, meter_reading, notes." : undefined} />
        </Card>
      ) : (
        <div className="stack">
          {groups.map(([lid, rows]) => {
            const line = linesById.get(lid);
            return (
              <Card key={lid || "none"} title={line ? `${line.code} · ${line.name}${line.shifts.length ? ` · shifts ${line.shifts.join(", ")}` : ""}` : "No line"} tight>
                <div className="table-wrap">
                  <table className="data responsive">
                    <thead>
                      <tr>
                        <th>Asset</th>
                        <th>Category</th>
                        <th>Make / model</th>
                        <th>Crit.</th>
                        <th>Status</th>
                        <th className="num">Open WOs</th>
                        <th>Meter</th>
                        <th>Next PM</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.flatMap(({ asset, children }) => [asset, ...children].map((a) => (
                        <tr key={a.id} className={`clickable ${a.parentId ? "indent" : ""}`} onClick={() => navigate(`/assets/${a.id}`)}>
                          <td data-label="Asset">
                            <div className="primary-cell">{a.assetNo}{!a.active && <span className="badge" style={{ marginLeft: 6 }}>inactive</span>}</div>
                            <div className="sub-cell">{a.name}</div>
                          </td>
                          <td data-label="Category">{a.category || "—"}</td>
                          <td data-label="Make / model">{[a.make, a.model].filter(Boolean).join(" ") || "—"}</td>
                          <td data-label="Criticality">
                            <Badge tone={a.criticality === "A" ? "critical" : a.criticality === "B" ? "warning" : "neutral"}>{a.criticality}</Badge>
                          </td>
                          <td data-label="Status">
                            <Badge tone={a.status === "down" ? "critical" : a.status === "maintenance" ? "warning" : a.status === "retired" ? "neutral" : "good"} dot>
                              {ASSET_STATUS_LABELS[a.status]}
                            </Badge>
                          </td>
                          <td data-label="Open WOs" className="num">{openCount.get(a.id) ?? 0}</td>
                          <td data-label="Meter">{a.meterUnit ? `${a.meterReading} ${a.meterUnit}` : "—"}</td>
                          <td data-label="Next PM">{nextPm.has(a.id) ? <PlanStateBadge state={nextPm.get(a.id)!.state} /> : <span className="muted">No plan</span>}</td>
                        </tr>
                      )))}
                    </tbody>
                  </table>
                </div>
              </Card>
            );
          })}
        </div>
      )}
      <AssetForm open={formOpen} onClose={() => setFormOpen(false)} onSaved={(id) => navigate(`/assets/${id}`)} />
    </div>
  );
}
