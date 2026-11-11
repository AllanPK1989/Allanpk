import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import QRCode from "qrcode";
import { AssetForm } from "../components/AssetForm";
import { Icon } from "../components/icons";
import { useToast } from "../components/Toast";
import { Badge, Button, Card, Confirm, Empty, Field, KV, Modal, PageHeader, PlanStateBadge, PriorityBadge, Stat, StatusBadge, usePaged } from "../components/ui";
import { WorkOrderForm } from "../components/WorkOrderForm";
import { formatDate, formatDateTime, formatHours, formatMinutes, todayKey } from "../lib/dates";
import { assetMetrics, hoursPerDayForLine, lastNDays } from "../lib/kpi";
import { nowIso } from "../lib/ids";
import { can } from "../lib/permissions";
import { planState } from "../lib/pm";
import { isOpenStatus, PRIORITY_RANK, WO_TYPE_LABEL } from "../lib/workorders";
import { useCurrentUser, useStore } from "../store/StoreProvider";
import { ASSET_STATUS_LABELS } from "../types";

export function AssetDetail() {
  const { id } = useParams();
  const { snapshot, mutate, linesById, usersById, assetsById } = useStore();
  const user = useCurrentUser();
  const navigate = useNavigate();
  const toast = useToast();
  const [edit, setEdit] = useState(false);
  const [newComponent, setNewComponent] = useState(false);
  const [breakdown, setBreakdown] = useState(false);
  const [meterOpen, setMeterOpen] = useState(false);
  const [retire, setRetire] = useState(false);
  const [qr, setQr] = useState<string>("");
  const [days, setDays] = useState(90);
  const today = todayKey();

  const asset = snapshot.assets.find((a) => a.id === id);

  useEffect(() => {
    if (!asset) return;
    const url = `${location.origin}${location.pathname}#/assets/${asset.id}`;
    QRCode.toDataURL(url, { margin: 1, width: 160 }).then(setQr).catch(() => setQr(""));
  }, [asset]);

  const wos = useMemo(() => snapshot.workOrders.filter((w) => w.assetId === asset?.id), [snapshot.workOrders, asset?.id]);
  const open = wos.filter((w) => isOpenStatus(w.status)).sort((a, b) => PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority]);
  const history = wos.filter((w) => !isOpenStatus(w.status)).sort((a, b) => (b.completedAt ?? b.updatedAt).localeCompare(a.completedAt ?? a.updatedAt));
  const paged = usePaged(history, 20);

  if (!asset) return <Empty icon="box" title="Asset not found" action={<Button onClick={() => navigate("/assets")}>Back to assets</Button>} />;

  const line = asset.lineId ? linesById.get(asset.lineId) : undefined;
  const parent = asset.parentId ? assetsById.get(asset.parentId) : undefined;
  const children = snapshot.assets.filter((a) => a.parentId === asset.id);
  const plans = snapshot.pmPlans.filter((p) => p.assetId === asset.id);
  const parts = snapshot.parts.filter((p) => p.assetIds.includes(asset.id) && p.active);
  const metrics = assetMetrics(snapshot.workOrders, asset.id, lastNDays(days, today), hoursPerDayForLine(line, snapshot.settings));
  const manage = can(user, "asset.manage");

  const retireAsset = () => {
    mutate(
      (d) => {
        const a = d.assets.find((x) => x.id === asset.id);
        if (!a) return;
        a.status = "retired";
        a.active = false;
        a.updatedAt = nowIso();
        for (const p of d.pmPlans) if (p.assetId === a.id) p.active = false;
      },
      { entity: "asset", entityId: asset.id, action: "retire", summary: `Asset ${asset.assetNo} retired` },
    );
    toast.success("Asset retired; its PM plans are inactive");
  };

  return (
    <div className="stack">
      <Link to="/assets" className="flex small">
        <Icon name="arrow-left" size={14} /> Assets
      </Link>
      <PageHeader
        title={
          <span className="flex flex-wrap">
            {asset.assetNo}
            <Badge tone={asset.criticality === "A" ? "critical" : asset.criticality === "B" ? "warning" : "neutral"}>Criticality {asset.criticality}</Badge>
            <Badge tone={asset.status === "down" ? "critical" : asset.status === "maintenance" ? "warning" : asset.status === "retired" ? "neutral" : "good"} dot>
              {ASSET_STATUS_LABELS[asset.status]}
            </Badge>
          </span>
        }
        subtitle={
          <>
            {asset.name}
            {parent && (
              <>
                {" "}
                · part of <Link to={`/assets/${parent.id}`}>{parent.assetNo}</Link>
              </>
            )}
            {line && ` · ${line.code} ${line.name}`}
          </>
        }
        actions={
          <>
            {can(user, "wo.request") && asset.status !== "retired" && (
              <Button variant="primary" icon="zap" onClick={() => setBreakdown(true)}>
                Report breakdown
              </Button>
            )}
            {can(user, "asset.meter") && asset.meterUnit && (
              <Button icon="gauge" onClick={() => setMeterOpen(true)}>
                Update meter
              </Button>
            )}
            {manage && (
              <>
                <Button icon="plus" onClick={() => setNewComponent(true)}>
                  Add component
                </Button>
                <Button icon="edit" onClick={() => setEdit(true)}>
                  Edit
                </Button>
                {asset.status !== "retired" && (
                  <Button variant="ghost" onClick={() => setRetire(true)}>
                    Retire
                  </Button>
                )}
              </>
            )}
          </>
        }
      />

      <div className="grid grid-stats">
        <Stat label={`Breakdowns, ${days} days`} value={metrics.breakdowns} tone={metrics.breakdowns > 3 ? "critical" : undefined} />
        <Stat label="Downtime" value={formatMinutes(metrics.downtimeMinutes)} />
        <Stat label="MTTR" value={formatHours(metrics.mttrHours)} />
        <Stat label="MTBF" value={metrics.mtbfHours === null ? "—" : `${Math.round(metrics.mtbfHours)} h`} hint={`${hoursPerDayForLine(line, snapshot.settings)} planned h/day`} />
        <Stat label="Open work orders" value={open.length} tone={open.some((w) => w.type === "breakdown") ? "critical" : undefined} />
      </div>
      <div className="flex">
        <span className="small muted">Period</span>
        <select value={days} onChange={(e) => setDays(Number(e.target.value))} style={{ width: "auto" }} aria-label="Period">
          <option value={30}>30 days</option>
          <option value={90}>90 days</option>
          <option value={365}>365 days</option>
        </select>
      </div>

      <div className="grid grid-3">
        <div className="stack span-2">
          <Card title="Open work orders" tight>
            {open.length === 0 ? (
              <Empty icon="check" title="No open work orders" />
            ) : (
              <ul className="list">
                {open.map((w) => (
                  <li key={w.id}>
                    <Link className="row" to={`/work-orders/${w.id}`}>
                      <div className="grow">
                        <div className="title">
                          {w.woNo} · {w.title}
                        </div>
                        <div className="meta">
                          {WO_TYPE_LABEL[w.type]} · {w.assignedToUserIds.map((u) => usersById.get(u)?.name).filter(Boolean).join(", ") || "Unassigned"} · {formatDateTime(w.createdAt)}
                        </div>
                      </div>
                      <PriorityBadge priority={w.priority} />
                      <StatusBadge status={w.status} />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card title="PM plans" actions={can(user, "pm.manage") ? <Link to="/pm">Manage plans</Link> : undefined} tight>
            {plans.length === 0 ? (
              <Empty icon="calendar" title="No PM plan for this asset" />
            ) : (
              <table className="data">
                <thead>
                  <tr>
                    <th>Plan</th>
                    <th>Next due</th>
                    <th>State</th>
                    <th>Last done</th>
                  </tr>
                </thead>
                <tbody>
                  {plans.map((p) => (
                    <tr key={p.id} className="clickable" onClick={() => navigate(`/pm?plan=${p.id}`)}>
                      <td>
                        <div className="primary-cell">{p.code}</div>
                        <div className="sub-cell">{p.name}</div>
                      </td>
                      <td>
                        {formatDate(p.nextDueAt)}
                        {p.nextDueMeter !== null && <div className="sub-cell">at {p.nextDueMeter} {asset.meterUnit}</div>}
                      </td>
                      <td>
                        <PlanStateBadge state={planState(p, asset, today)} />
                      </td>
                      <td>{formatDate(p.lastDoneAt)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
          <Card title={`History · ${history.length} work orders`} tight>
            {history.length === 0 ? (
              <Empty icon="history" title="No completed work yet" />
            ) : (
              <>
                <table className="data responsive">
                  <thead>
                    <tr>
                      <th>Work order</th>
                      <th>Type</th>
                      <th>Completed</th>
                      <th>Downtime</th>
                      <th>Root cause / action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paged.visible.map((w) => (
                      <tr key={w.id} className="clickable" onClick={() => navigate(`/work-orders/${w.id}`)}>
                        <td data-label="Work order">
                          <div className="primary-cell">{w.woNo}</div>
                          <div className="sub-cell">{w.title}</div>
                        </td>
                        <td data-label="Type">{WO_TYPE_LABEL[w.type]}</td>
                        <td data-label="Completed">{formatDate(w.completedAt ?? w.updatedAt)}</td>
                        <td data-label="Downtime">{w.type === "breakdown" ? formatMinutes(w.downtimeMinutes) : "—"}</td>
                        <td data-label="Root cause / action" className="small">
                          {w.rootCause && <div>{w.rootCause}</div>}
                          <div className="muted">{w.actionTaken}</div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {paged.more && (
                  <div className="table-foot">
                    <span>Showing {paged.visible.length} of {paged.total}</span>
                    <Button size="sm" onClick={paged.showMore}>Show more</Button>
                  </div>
                )}
              </>
            )}
          </Card>
        </div>
        <div className="stack">
          <Card title="Details">
            <KV
              items={[
                { k: "Category", v: asset.category || "—" },
                { k: "Make", v: asset.make || "—" },
                { k: "Model", v: asset.model || "—" },
                { k: "Serial no", v: asset.serialNo || "—" },
                { k: "Location", v: asset.location || "—" },
                { k: "Installed", v: formatDate(asset.installDate) },
                { k: "Meter", v: asset.meterUnit ? `${asset.meterReading} ${asset.meterUnit} (${formatDate(asset.meterUpdatedAt)})` : "No meter" },
                ...asset.specs.map((s) => ({ k: s.key, v: s.value })),
              ]}
            />
            {asset.notes && <p className="mt-8 small" style={{ whiteSpace: "pre-wrap" }}>{asset.notes}</p>}
          </Card>
          {children.length > 0 && (
            <Card title="Components" tight>
              <ul className="list">
                {children.map((c) => (
                  <li key={c.id}>
                    <Link className="row" to={`/assets/${c.id}`}>
                      <div className="grow">
                        <div className="title">{c.assetNo}</div>
                        <div className="meta">{c.name}</div>
                      </div>
                      <Badge tone={c.status === "down" ? "critical" : "neutral"}>{ASSET_STATUS_LABELS[c.status]}</Badge>
                    </Link>
                  </li>
                ))}
              </ul>
            </Card>
          )}
          {can(user, "part.view") && (
            <Card title="Spare parts" tight>
              {parts.length === 0 ? (
                <Empty icon="package" title="No parts linked" />
              ) : (
                <ul className="list">
                  {parts.map((p) => (
                    <li key={p.id}>
                      <Link className="row" to={`/parts/${p.id}`}>
                        <div className="grow">
                          <div className="title">{p.partNo}</div>
                          <div className="meta">{p.name}</div>
                        </div>
                        <Badge tone={p.stock <= p.minStock ? "warning" : "neutral"}>
                          {p.stock} {p.unit}
                        </Badge>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          )}
          <Card title="QR code">
            <div className="center">
              {qr ? <img src={qr} alt={`QR code for ${asset.assetNo}`} width={160} height={160} /> : <span className="muted">Generating…</span>}
              <div className="small muted">Scan to open this asset. Print all codes from the QR sheet.</div>
            </div>
          </Card>
        </div>
      </div>

      <AssetForm open={edit} asset={asset} onClose={() => setEdit(false)} />
      <AssetForm open={newComponent} parentId={asset.id} onClose={() => setNewComponent(false)} />
      <WorkOrderForm open={breakdown} onClose={() => setBreakdown(false)} initialType="breakdown" initialAssetId={asset.id} onCreated={(wid) => navigate(`/work-orders/${wid}`)} />
      <MeterModal open={meterOpen} onClose={() => setMeterOpen(false)} assetId={asset.id} />
      <Confirm open={retire} onClose={() => setRetire(false)} title={`Retire ${asset.assetNo}?`} text="The asset is marked retired and its PM plans become inactive. History is kept." confirmLabel="Retire" danger onConfirm={retireAsset} />
    </div>
  );
}

function MeterModal({ open, onClose, assetId }: { open: boolean; onClose: () => void; assetId: string }) {
  const { assetsById, mutate } = useStore();
  const user = useCurrentUser();
  const toast = useToast();
  const asset = assetsById.get(assetId);
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (open) {
      setValue(String(asset?.meterReading ?? ""));
      setError(null);
    }
  }, [open, asset?.meterReading]);
  if (!asset) return null;
  const submit = () => {
    const n = Number(value);
    if (!Number.isFinite(n) || n < 0) return setError("Enter a number");
    if (n < asset.meterReading) return setError(`Reading is lower than the current ${asset.meterReading}. Meters normally only go up; edit the asset if the meter was replaced.`);
    mutate(
      (d) => {
        const a = d.assets.find((x) => x.id === assetId);
        if (!a) return;
        a.meterReading = n;
        a.meterUpdatedAt = nowIso();
        a.updatedAt = a.meterUpdatedAt;
      },
      { entity: "asset", entityId: assetId, action: "meter", summary: `${asset.assetNo} meter set to ${n} ${asset.meterUnit} by ${user.name}` },
    );
    toast.success("Meter updated");
    onClose();
  };
  return (
    <Modal title={`Meter reading · ${asset.assetNo}`} open={open} onClose={onClose} size="narrow" footer={<><Button onClick={onClose}>Cancel</Button><Button variant="primary" onClick={submit}>Save</Button></>}>
      <Field label={`Current reading (${asset.meterUnit})`} required error={error} hint={`Last update ${formatDate(asset.meterUpdatedAt)}`}>
        <input type="number" min={0} value={value} onChange={(e) => setValue(e.target.value)} autoFocus />
      </Field>
    </Modal>
  );
}
