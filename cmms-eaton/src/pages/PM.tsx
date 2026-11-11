import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useToast } from "../components/Toast";
import { Button, Card, Empty, Field, Modal, Notice, PageHeader, PlanStateBadge, Search, Tabs } from "../components/ui";
import { addDays, addInterval, formatDate, formatMonth, monthStart, parseDateKey, todayKey } from "../lib/dates";
import { newId, nowIso } from "../lib/ids";
import { can } from "../lib/permissions";
import { buildPmWorkOrder, generateDuePMs, hasOpenWorkOrder, intervalLabel, planState, type PlanState } from "../lib/pm";
import { isDoneStatus, isOpenStatus, PRIORITIES, PRIORITY_LABEL } from "../lib/workorders";
import { useCurrentUser, useStore } from "../store/StoreProvider";
import type { IntervalUnit, PMPlan, PMTrigger, Priority } from "../types";

type Tab = "plans" | "calendar";

export function PM() {
  const { snapshot, mutate, assetsById, usersById, linesById } = useStore();
  const user = useCurrentUser();
  const toast = useToast();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const tab = (params.get("tab") as Tab) || "plans";
  const editId = params.get("plan");
  const [q, setQ] = useState("");
  const [stateFilter, setStateFilter] = useState<PlanState | "">("");
  const [lineId, setLineId] = useState("");
  const [newOpen, setNewOpen] = useState(false);
  const today = todayKey();
  const manage = can(user, "pm.manage");

  const setParam = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return snapshot.pmPlans
      .map((p) => ({ plan: p, asset: assetsById.get(p.assetId), state: planState(p, assetsById.get(p.assetId), today) }))
      .filter(({ plan, asset, state }) => {
        if (stateFilter && state !== stateFilter) return false;
        if (lineId && asset?.lineId !== lineId) return false;
        if (needle && !`${plan.code} ${plan.name} ${asset?.assetNo ?? ""} ${asset?.name ?? ""}`.toLowerCase().includes(needle)) return false;
        return true;
      })
      .sort((a, b) => {
        const order: Record<PlanState, number> = { overdue: 0, due: 1, upcoming: 2, ok: 3, inactive: 4 };
        return order[a.state] - order[b.state] || a.plan.nextDueAt.localeCompare(b.plan.nextDueAt);
      });
  }, [snapshot.pmPlans, assetsById, q, stateFilter, lineId, today]);

  const dueNow = rows.filter((r) => (r.state === "due" || r.state === "overdue") && !hasOpenWorkOrder(snapshot.workOrders, r.plan.id)).length;

  const generate = () => {
    let count = 0;
    mutate(
      (d) => {
        count = generateDuePMs(d, user.id, today).length;
      },
      { entity: "pm", entityId: "generate", action: "generate", summary: "PM work orders generated for due plans" },
    );
    toast.success(count ? `${count} PM work order${count === 1 ? "" : "s"} created` : "Nothing to generate: every due plan already has an open work order");
  };

  const createOne = (plan: PMPlan) => {
    const asset = assetsById.get(plan.assetId);
    if (!asset) return;
    let woId = "";
    mutate(
      (d) => {
        const wo = buildPmWorkOrder(d, plan, asset, user.id, today);
        d.workOrders.push(wo);
        woId = wo.id;
      },
      { entity: "pm", entityId: plan.id, action: "generate", summary: `Work order created for ${plan.code}` },
    );
    navigate(`/work-orders/${woId}`);
  };

  return (
    <div>
      <PageHeader
        title="Preventive maintenance"
        subtitle={`${snapshot.pmPlans.filter((p) => p.active).length} active plans · ${dueNow} due without a work order`}
        actions={
          manage && (
            <>
              <Button icon="refresh" onClick={generate} disabled={dueNow === 0}>
                Generate due work orders{dueNow ? ` (${dueNow})` : ""}
              </Button>
              <Button variant="primary" icon="plus" onClick={() => setNewOpen(true)}>
                New PM plan
              </Button>
            </>
          )
        }
      />
      <Tabs<Tab> tabs={[{ id: "plans", label: "Plans", count: snapshot.pmPlans.length }, { id: "calendar", label: "Calendar" }]} active={tab} onChange={(t) => setParam("tab", t === "plans" ? "" : t)} />

      {tab === "plans" && (
        <>
          <div className="filters">
            <Search value={q} onChange={setQ} placeholder="Search plan or asset" />
            <select value={stateFilter} onChange={(e) => setStateFilter(e.target.value as PlanState | "")} aria-label="State">
              <option value="">Any state</option>
              <option value="overdue">Overdue</option>
              <option value="due">Due</option>
              <option value="upcoming">Upcoming</option>
              <option value="ok">Scheduled</option>
              <option value="inactive">Inactive</option>
            </select>
            <select value={lineId} onChange={(e) => setLineId(e.target.value)} aria-label="Line">
              <option value="">Any line</option>
              {snapshot.lines.filter((l) => l.active).map((l) => (
                <option key={l.id} value={l.id}>
                  {l.code} · {l.name}
                </option>
              ))}
            </select>
          </div>
          <Card tight>
            {rows.length === 0 ? (
              <Empty icon="calendar" title="No PM plans" text={manage ? "Create a plan for each asset: frequency, checklist and parts." : undefined} />
            ) : (
              <div className="table-wrap">
                <table className="data responsive">
                  <thead>
                    <tr>
                      <th>Plan</th>
                      <th>Asset</th>
                      <th>Frequency</th>
                      <th>Next due</th>
                      <th>State</th>
                      <th>Assigned</th>
                      <th>Last done</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map(({ plan, asset, state }) => {
                      const openWo = hasOpenWorkOrder(snapshot.workOrders, plan.id);
                      return (
                        <tr key={plan.id}>
                          <td data-label="Plan">
                            <div className="primary-cell">{plan.code}</div>
                            <div className="sub-cell">{plan.name}</div>
                          </td>
                          <td data-label="Asset">
                            {asset ? (
                              <Link to={`/assets/${asset.id}`}>
                                {asset.assetNo}
                                <span className="sub-cell"> · {asset.lineId ? linesById.get(asset.lineId)?.code : ""}</span>
                              </Link>
                            ) : (
                              "—"
                            )}
                          </td>
                          <td data-label="Frequency">
                            {intervalLabel(plan).replace("meter units", asset?.meterUnit ?? "")}
                            <div className="sub-cell">{plan.scheduleMode === "fixed" ? "fixed dates" : "from completion"}</div>
                          </td>
                          <td data-label="Next due">
                            {formatDate(plan.nextDueAt)}
                            {plan.nextDueMeter !== null && asset?.meterUnit && (
                              <div className="sub-cell">
                                at {plan.nextDueMeter} {asset.meterUnit} (now {asset.meterReading})
                              </div>
                            )}
                          </td>
                          <td data-label="State">
                            <PlanStateBadge state={state} />
                          </td>
                          <td data-label="Assigned">{plan.assignedToUserId ? usersById.get(plan.assignedToUserId)?.name : <span className="muted">—</span>}</td>
                          <td data-label="Last done">{formatDate(plan.lastDoneAt)}</td>
                          <td data-label="" className="right nowrap">
                            {openWo ? (
                              <Link to={`/work-orders/${openWo.id}`} className="btn sm">
                                {openWo.woNo}
                              </Link>
                            ) : (
                              manage && (state === "due" || state === "overdue") && (
                                <Button size="sm" onClick={() => createOne(plan)}>
                                  Create WO
                                </Button>
                              )
                            )}{" "}
                            {manage && (
                              <Button size="sm" variant="ghost" icon="edit" aria-label="Edit plan" onClick={() => setParam("plan", plan.id)} />
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </>
      )}

      {tab === "calendar" && <Calendar />}

      <PlanForm open={newOpen || Boolean(editId)} planId={editId} onClose={() => { setNewOpen(false); setParam("plan", ""); }} />
    </div>
  );
}

function Calendar() {
  const { snapshot, assetsById } = useStore();
  const today = todayKey();
  const [month, setMonth] = useState(monthStart(today));
  const first = parseDateKey(month);
  const gridStart = addDays(month, -((first.getDay() + 6) % 7));
  const days = Array.from({ length: 42 }, (_, i) => addDays(gridStart, i));
  const events = useMemo(() => {
    const map = new Map<string, { label: string; cls: string; to: string }[]>();
    const push = (key: string, ev: { label: string; cls: string; to: string }) => map.set(key, [...(map.get(key) ?? []), ev]);
    for (const w of snapshot.workOrders) {
      if (w.type !== "pm" || w.status === "cancelled") continue;
      if (isDoneStatus(w.status) && w.completedAt) push(w.completedAt.slice(0, 10), { label: `${w.woNo} done`, cls: "done", to: `/work-orders/${w.id}` });
      else if (isOpenStatus(w.status) && w.dueDate) push(w.dueDate, { label: w.title, cls: w.dueDate < today ? "overdue" : "", to: `/work-orders/${w.id}` });
    }
    for (const p of snapshot.pmPlans) {
      if (!p.active || (p.trigger === "meter")) continue;
      if (snapshot.workOrders.some((w) => w.pmPlanId === p.id && isOpenStatus(w.status))) continue;
      const asset = assetsById.get(p.assetId);
      push(p.nextDueAt, { label: `${p.code} ${asset?.assetNo ?? ""}`, cls: p.nextDueAt < today ? "overdue" : "", to: `/pm?plan=${p.id}` });
      // Project the next few cycles so the months ahead are not empty.
      let next = p.nextDueAt;
      for (let i = 0; i < 6; i++) {
        next = addInterval(next, p.intervalValue, p.intervalUnit);
        push(next, { label: `${p.code} ${asset?.assetNo ?? ""}`, cls: "", to: `/pm?plan=${p.id}` });
      }
    }
    return map;
  }, [snapshot.workOrders, snapshot.pmPlans, assetsById, today]);

  return (
    <Card
      title={formatMonth(month)}
      actions={
        <>
          <Button size="sm" icon="chevron-left" aria-label="Previous month" onClick={() => setMonth(addInterval(month, -1, "month"))} />
          <Button size="sm" onClick={() => setMonth(monthStart(today))}>
            Today
          </Button>
          <Button size="sm" icon="chevron-right" aria-label="Next month" onClick={() => setMonth(addInterval(month, 1, "month"))} />
        </>
      }
      tight
    >
      <div className="legend" style={{ padding: "10px 16px 0" }}>
        <span><i style={{ background: "var(--accent)" }} /> Planned</span>
        <span><i style={{ background: "var(--critical)" }} /> Overdue</span>
        <span><i style={{ background: "var(--good)" }} /> Completed</span>
      </div>
      <div className="calendar" style={{ margin: 16 }}>
        {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d) => (
          <div className="dow" key={d}>
            {d}
          </div>
        ))}
        {days.map((d) => {
          const inMonth = d.slice(0, 7) === month.slice(0, 7);
          const list = events.get(d) ?? [];
          return (
            <div key={d} className={`day ${inMonth ? "" : "other"} ${d === today ? "today" : ""}`}>
              <span className="d">{parseDateKey(d).getDate()}</span>
              {list.slice(0, 4).map((e, i) => (
                <Link key={i} to={e.to} className={`ev ${e.cls}`} title={e.label}>
                  {e.label}
                </Link>
              ))}
              {list.length > 4 && <span className="small muted">+{list.length - 4} more</span>}
            </div>
          );
        })}
      </div>
    </Card>
  );
}

function PlanForm({ open, planId, onClose }: { open: boolean; planId: string | null; onClose: () => void }) {
  const { snapshot, mutate, assetsById, linesById } = useStore();
  const user = useCurrentUser();
  const toast = useToast();
  const existing = planId ? snapshot.pmPlans.find((p) => p.id === planId) : undefined;
  const manage = can(user, "pm.manage");
  const blank = () => ({
    code: `PM-${String(snapshot.sequences.pm + 1).padStart(3, "0")}`,
    name: "",
    description: "",
    assetId: "",
    trigger: "time" as PMTrigger,
    intervalValue: "1",
    intervalUnit: "month" as IntervalUnit,
    meterInterval: "",
    scheduleMode: "fixed" as PMPlan["scheduleMode"],
    leadDays: String(snapshot.settings.pmLeadDays),
    nextDueAt: addDays(todayKey(), 7),
    estimatedHours: "1",
    priority: "medium" as Priority,
    assignedToUserId: "",
    checklist: "",
    parts: [] as { partId: string; qty: string }[],
    active: true,
  });
  const [f, setF] = useState(blank);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    if (existing) {
      setF({
        code: existing.code,
        name: existing.name,
        description: existing.description,
        assetId: existing.assetId,
        trigger: existing.trigger,
        intervalValue: String(existing.intervalValue),
        intervalUnit: existing.intervalUnit,
        meterInterval: existing.meterInterval === null ? "" : String(existing.meterInterval),
        scheduleMode: existing.scheduleMode,
        leadDays: String(existing.leadDays),
        nextDueAt: existing.nextDueAt,
        estimatedHours: String(existing.estimatedHours),
        priority: existing.priority,
        assignedToUserId: existing.assignedToUserId ?? "",
        checklist: existing.checklist.join("\n"),
        parts: existing.parts.map((p) => ({ partId: p.partId, qty: String(p.qty) })),
        active: existing.active,
      });
    } else setF(blank());
    setError(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, planId]);

  const set = <K extends keyof typeof f>(key: K, value: (typeof f)[K]) => setF((s) => ({ ...s, [key]: value }));
  const asset = assetsById.get(f.assetId);
  const technicians = snapshot.users.filter((u) => u.active && (u.role === "technician" || u.role === "maintenance_supervisor"));
  const usesTime = f.trigger !== "meter";
  const usesMeter = f.trigger !== "time";

  const submit = () => {
    setError(null);
    if (!f.name.trim()) return setError("Give the plan a name");
    if (!f.assetId) return setError("Select the asset");
    if (usesTime && !(Number(f.intervalValue) > 0)) return setError("Interval must be more than zero");
    if (usesMeter && !(Number(f.meterInterval) > 0)) return setError("Meter interval must be more than zero");
    if (usesMeter && !asset?.meterUnit) return setError("This asset has no meter. Set a meter unit on the asset first.");
    if (!f.nextDueAt) return setError("Set the next due date");
    const now = nowIso();
    const meterInterval = usesMeter ? Number(f.meterInterval) : null;
    mutate(
      (d) => {
        const data = {
          code: f.code.trim() || `PM-${String(d.sequences.pm + 1).padStart(3, "0")}`,
          name: f.name.trim(),
          description: f.description.trim(),
          assetId: f.assetId,
          trigger: f.trigger,
          intervalValue: Number(f.intervalValue) || 1,
          intervalUnit: f.intervalUnit,
          meterInterval,
          scheduleMode: f.scheduleMode,
          leadDays: Math.max(0, Number(f.leadDays) || 0),
          nextDueAt: f.nextDueAt,
          estimatedHours: Number(f.estimatedHours) || 0,
          priority: f.priority,
          assignedToUserId: f.assignedToUserId || null,
          checklist: f.checklist.split("\n").map((s) => s.trim()).filter(Boolean),
          parts: f.parts.filter((p) => p.partId && Number(p.qty) > 0).map((p) => ({ partId: p.partId, qty: Number(p.qty) })),
          active: f.active,
          updatedAt: now,
        };
        const a = d.assets.find((x) => x.id === f.assetId);
        if (existing) {
          const p = d.pmPlans.find((x) => x.id === existing.id);
          if (!p) return;
          Object.assign(p, data);
          if (meterInterval && p.nextDueMeter === null && a) {
            p.lastDoneMeter = a.meterReading;
            p.nextDueMeter = a.meterReading + meterInterval;
          }
          if (!meterInterval) {
            p.nextDueMeter = null;
          }
        } else {
          d.sequences.pm += 1;
          d.pmPlans.push({
            id: newId(),
            ...data,
            lastDoneAt: null,
            lastDoneMeter: meterInterval && a ? a.meterReading : null,
            nextDueMeter: meterInterval && a ? a.meterReading + meterInterval : null,
            createdAt: now,
          });
        }
      },
      { entity: "pm_plan", entityId: existing?.id ?? f.code, action: existing ? "update" : "create", summary: `PM plan ${f.code} ${existing ? "updated" : "created"}` },
    );
    toast.success(existing ? "Plan updated" : "Plan created");
    onClose();
  };

  if (!manage && open) {
    return (
      <Modal title={existing ? `${existing.code} · ${existing.name}` : "PM plan"} open={open} onClose={onClose}>
        {existing ? (
          <div className="stack">
            <p>{existing.description}</p>
            <ul>
              {existing.checklist.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
          </div>
        ) : null}
      </Modal>
    );
  }

  return (
    <Modal
      title={existing ? `Edit ${existing.code}` : "New PM plan"}
      open={open}
      onClose={onClose}
      size="wide"
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit}>
            {existing ? "Save plan" : "Create plan"}
          </Button>
        </>
      }
    >
      <div className="form-grid">
        <Field label="Code">
          <input value={f.code} onChange={(e) => set("code", e.target.value)} />
        </Field>
        <Field label="Asset" required>
          <select value={f.assetId} onChange={(e) => set("assetId", e.target.value)}>
            <option value="">Select asset</option>
            {snapshot.assets.filter((a) => a.active).sort((a, b) => a.assetNo.localeCompare(b.assetNo)).map((a) => (
              <option key={a.id} value={a.id}>
                {a.assetNo} · {a.name}
                {a.lineId ? ` (${linesById.get(a.lineId)?.code ?? ""})` : ""}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Name" required className="full">
          <input value={f.name} onChange={(e) => set("name", e.target.value)} placeholder="e.g. Monthly lubrication and inspection" />
        </Field>
        <Field label="Trigger">
          <select value={f.trigger} onChange={(e) => set("trigger", e.target.value as PMTrigger)}>
            <option value="time">Calendar (every N days/weeks/months)</option>
            <option value="meter">Meter (every N hours/cycles)</option>
            <option value="both">Calendar and meter, whichever first</option>
          </select>
        </Field>
        <Field label="Schedule mode" hint={f.scheduleMode === "fixed" ? "Next date counts from the planned date" : "Next date counts from the completion date"}>
          <select value={f.scheduleMode} onChange={(e) => set("scheduleMode", e.target.value as PMPlan["scheduleMode"])}>
            <option value="fixed">Fixed dates</option>
            <option value="floating">Floating from completion</option>
          </select>
        </Field>
        {usesTime && (
          <>
            <Field label="Every" required>
              <div className="flex">
                <input type="number" min={1} value={f.intervalValue} onChange={(e) => set("intervalValue", e.target.value)} style={{ width: 90 }} />
                <select value={f.intervalUnit} onChange={(e) => set("intervalUnit", e.target.value as IntervalUnit)}>
                  <option value="day">day(s)</option>
                  <option value="week">week(s)</option>
                  <option value="month">month(s)</option>
                  <option value="year">year(s)</option>
                </select>
              </div>
            </Field>
            <Field label="Next due date" required>
              <input type="date" value={f.nextDueAt} onChange={(e) => set("nextDueAt", e.target.value)} />
            </Field>
          </>
        )}
        {usesMeter && (
          <Field label={`Meter interval${asset?.meterUnit ? ` (${asset.meterUnit})` : ""}`} required hint={asset?.meterUnit ? `Current reading ${asset.meterReading} ${asset.meterUnit}` : "Asset needs a meter unit"}>
            <input type="number" min={1} value={f.meterInterval} onChange={(e) => set("meterInterval", e.target.value)} />
          </Field>
        )}
        <Field label="Create work order (days before due)">
          <input type="number" min={0} value={f.leadDays} onChange={(e) => set("leadDays", e.target.value)} />
        </Field>
        <Field label="Estimated hours">
          <input type="number" min={0} step={0.25} value={f.estimatedHours} onChange={(e) => set("estimatedHours", e.target.value)} />
        </Field>
        <Field label="Priority">
          <select value={f.priority} onChange={(e) => set("priority", e.target.value as Priority)}>
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {PRIORITY_LABEL[p]}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Default technician">
          <select value={f.assignedToUserId} onChange={(e) => set("assignedToUserId", e.target.value)}>
            <option value="">Assign when generated</option>
            {technicians.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Checklist" hint="One step per line; copied to every work order" className="full">
          <textarea value={f.checklist} onChange={(e) => set("checklist", e.target.value)} rows={5} />
        </Field>
        <div className="full">
          <div className="field">
            <span className="label">Planned parts</span>
          </div>
          {f.parts.map((p, i) => (
            <div className="flex mb-8" key={i}>
              <select value={p.partId} onChange={(e) => set("parts", f.parts.map((x, j) => (j === i ? { ...x, partId: e.target.value } : x)))}>
                <option value="">Select part</option>
                {snapshot.parts.filter((x) => x.active).map((x) => (
                  <option key={x.id} value={x.id}>
                    {x.partNo} · {x.name}
                  </option>
                ))}
              </select>
              <input type="number" min={0} step="any" value={p.qty} style={{ width: 90 }} onChange={(e) => set("parts", f.parts.map((x, j) => (j === i ? { ...x, qty: e.target.value } : x)))} aria-label="Quantity" />
              <Button variant="ghost" icon="trash" aria-label="Remove part" onClick={() => set("parts", f.parts.filter((_, j) => j !== i))} />
            </div>
          ))}
          <Button size="sm" icon="plus" onClick={() => set("parts", [...f.parts, { partId: "", qty: "1" }])}>
            Add part
          </Button>
        </div>
        <Field label="Description" className="full">
          <textarea value={f.description} onChange={(e) => set("description", e.target.value)} />
        </Field>
        <label className="check">
          <input type="checkbox" checked={f.active} onChange={(e) => set("active", e.target.checked)} /> Plan is active
        </label>
        {existing && (
          <div className="small muted">
            Last done {formatDate(existing.lastDoneAt)}
            {existing.lastDoneMeter !== null && ` at ${existing.lastDoneMeter} ${asset?.meterUnit ?? ""}`}
          </div>
        )}
        {error && (
          <div className="full">
            <Notice tone="critical" icon="alert">
              {error}
            </Notice>
          </div>
        )}
      </div>
    </Modal>
  );
}
