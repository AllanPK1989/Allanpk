import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Icon } from "../components/icons";
import { useToast } from "../components/Toast";
import { Badge, Button, Card, ChipSelect, Empty, Field, KV, Modal, Notice, PageHeader, PriorityBadge, StatusBadge, money } from "../components/ui";
import { formatDate, formatDateTime, formatMinutes, fromLocalInput, nowLocalInput, todayKey, toLocalInput } from "../lib/dates";
import { addComment, addLabor, assignWorkOrder, changeStatus, completeWorkOrder, movePart, removeLabor, setHandback, toggleChecklist } from "../lib/mutations";
import { can, canExecuteWorkOrder, canSeeWorkOrder } from "../lib/permissions";
import { isOpenStatus, laborHours, partsCost, PRIORITIES, PRIORITY_LABEL, WO_STATUS_LABEL, WO_TYPE_LABEL } from "../lib/workorders";
import { useCurrentUser, useStore } from "../store/StoreProvider";
import type { Priority, WOStatus, WorkOrder } from "../types";

type ModalKind = null | "complete" | "edit" | "hold" | "cancel" | "labor" | "part" | "reopen";

export function WorkOrderDetail() {
  const { id } = useParams();
  const { snapshot, mutate, assetsById, usersById, linesById, partsById } = useStore();
  const user = useCurrentUser();
  const toast = useToast();
  const navigate = useNavigate();
  const [modal, setModal] = useState<ModalKind>(null);
  const [comment, setComment] = useState("");
  const [note, setNote] = useState("");

  const wo = snapshot.workOrders.find((w) => w.id === id);
  if (!wo || !canSeeWorkOrder(user, wo)) {
    return <Empty icon="wrench" title="Work order not found" action={<Button onClick={() => navigate("/work-orders")}>Back to work orders</Button>} />;
  }

  const asset = wo.assetId ? assetsById.get(wo.assetId) : undefined;
  const line = wo.lineId ? linesById.get(wo.lineId) : undefined;
  const plan = wo.pmPlanId ? snapshot.pmPlans.find((p) => p.id === wo.pmPlanId) : undefined;
  const exec = canExecuteWorkOrder(user, wo);
  const manage = can(user, "wo.assign");
  const closer = can(user, "wo.close");
  const currency = snapshot.settings.currency;
  const name = (uid: string | null) => (uid ? (usersById.get(uid)?.name ?? "Unknown") : "—");
  const audit = (action: string, summary: string) => ({ entity: "work_order", entityId: wo.id, action, summary });

  const setStatus = (to: WOStatus, msg = "") => {
    mutate((d) => changeStatus(d, wo.id, to, user.id, msg), audit("status", `${wo.woNo} → ${WO_STATUS_LABEL[to]}${msg ? `: ${msg}` : ""}`));
    toast.success(`${wo.woNo} is now ${WO_STATUS_LABEL[to].toLowerCase()}`);
  };

  const canHandback = can(user, "wo.handback") && wo.type === "breakdown" && (wo.status === "completed" || wo.status === "closed") && !wo.handbackByUserId;
  const downMinutes = wo.downtimeStart ? (wo.downtimeMinutes ?? Math.round((Date.now() - new Date(wo.downtimeStart).getTime()) / 60_000)) : null;
  const openChecklist = wo.checklist.filter((c) => !c.done).length;

  const actions = (
    <>
      {exec && (wo.status === "open" || wo.status === "assigned") && (
        <Button variant="primary" icon="play" onClick={() => setStatus("in_progress")}>
          Start work
        </Button>
      )}
      {exec && wo.status === "in_progress" && (
        <>
          <Button variant="primary" icon="check" onClick={() => setModal("complete")}>
            Complete
          </Button>
          <Button icon="pause" onClick={() => { setNote(""); setModal("hold"); }}>
            Put on hold
          </Button>
        </>
      )}
      {exec && wo.status === "on_hold" && (
        <Button variant="primary" icon="play" onClick={() => setStatus("in_progress", "Resumed")}>
          Resume
        </Button>
      )}
      {closer && wo.status === "completed" && (
        <>
          <Button variant="primary" icon="check" onClick={() => setStatus("closed")}>
            Close
          </Button>
          <Button icon="refresh" onClick={() => { setNote(""); setModal("reopen"); }}>
            Reopen
          </Button>
        </>
      )}
      {canHandback && (
        <Button variant="primary" icon="check" onClick={() => { mutate((d) => setHandback(d, wo.id, user.id), audit("handback", `${wo.woNo}: machine handed back to production by ${user.name}`)); toast.success("Handback recorded"); }}>
          Confirm handback
        </Button>
      )}
      {manage && isOpenStatus(wo.status) && (
        <Button icon="edit" onClick={() => setModal("edit")}>
          Edit / assign
        </Button>
      )}
      {closer && isOpenStatus(wo.status) && (
        <Button variant="ghost" icon="x" onClick={() => { setNote(""); setModal("cancel"); }}>
          Cancel
        </Button>
      )}
      {closer && wo.status === "cancelled" && (
        <Button icon="refresh" onClick={() => setStatus("open", "Reopened")}>
          Reopen
        </Button>
      )}
    </>
  );

  return (
    <div className="stack">
      <Link to="/work-orders" className="flex small">
        <Icon name="arrow-left" size={14} /> Work orders
      </Link>
      <PageHeader
        title={
          <span className="flex flex-wrap">
            {wo.woNo}
            <Badge tone="accent">{WO_TYPE_LABEL[wo.type]}</Badge>
            <PriorityBadge priority={wo.priority} />
            <StatusBadge status={wo.status} />
          </span>
        }
        subtitle={wo.title}
        actions={actions}
      />

      {wo.type === "breakdown" && isOpenStatus(wo.status) && downMinutes !== null && (
        <Notice tone="critical" icon="zap">
          Machine down for {formatMinutes(downMinutes)} since {formatDateTime(wo.downtimeStart)} (shift {wo.shift ?? "?"}).
        </Notice>
      )}
      {wo.status === "completed" && wo.type === "breakdown" && !wo.handbackByUserId && (
        <Notice tone="warning" icon="flag">
          Repair completed. Waiting for the production supervisor to confirm handback.
        </Notice>
      )}

      <div className="grid grid-3">
        <div className="stack span-2">
          <Card title="Details">
            {wo.description && <p style={{ whiteSpace: "pre-wrap" }}>{wo.description}</p>}
            <KV
              items={[
                { k: "Asset", v: asset ? <Link to={`/assets/${asset.id}`}>{asset.assetNo} · {asset.name}</Link> : "—" },
                { k: "Line", v: line ? `${line.code} · ${line.name}` : "—" },
                { k: "Requested by", v: name(wo.requestedByUserId) },
                { k: "Created", v: formatDateTime(wo.createdAt) },
                { k: "Due", v: formatDate(wo.dueDate) },
                ...(wo.scheduledDate ? [{ k: "Scheduled", v: formatDate(wo.scheduledDate) }] : []),
                { k: "Estimated", v: wo.estimatedHours ? `${wo.estimatedHours} h` : "—" },
                ...(plan ? [{ k: "PM plan", v: <Link to={`/pm?plan=${plan.id}`}>{plan.code} · {plan.name}</Link> }] : []),
                ...(wo.failureCode ? [{ k: "Failure code", v: wo.failureCode }] : []),
                ...(wo.meterAtCompletion !== null ? [{ k: "Meter at completion", v: `${wo.meterAtCompletion} ${asset?.meterUnit ?? ""}` }] : []),
              ]}
            />
          </Card>

          {(wo.type === "breakdown" || wo.rootCause || wo.actionTaken) && (
            <Card title={wo.type === "breakdown" ? "Breakdown and repair" : "Work done"}>
              <KV
                items={[
                  ...(wo.type === "breakdown"
                    ? [
                        { k: "Stopped", v: `${formatDateTime(wo.downtimeStart)}${wo.shift ? ` · shift ${wo.shift}` : ""}` },
                        { k: "Back in service", v: formatDateTime(wo.downtimeEnd) },
                        { k: "Downtime", v: formatMinutes(wo.downtimeMinutes ?? downMinutes) },
                        { k: "Handback", v: wo.handbackByUserId ? `${name(wo.handbackByUserId)} · ${formatDateTime(wo.handbackAt)}` : "Not yet confirmed" },
                      ]
                    : []),
                  { k: "Root cause", v: wo.rootCause || "—" },
                  { k: "Action taken", v: wo.actionTaken || "—" },
                ]}
              />
            </Card>
          )}

          {wo.checklist.length > 0 && (
            <Card title={`Checklist · ${wo.checklist.length - openChecklist} of ${wo.checklist.length} done`}>
              <ul className="list checklist" style={{ padding: 0 }}>
                {wo.checklist.map((c) => (
                  <li key={c.id} className={c.done ? "done" : ""} style={{ padding: "8px 0" }}>
                    <input type="checkbox" checked={c.done} disabled={!exec || !isOpenStatus(wo.status)} onChange={() => mutate((d) => toggleChecklist(d, wo.id, c.id, user.id))} aria-label={c.text} />
                    <span className="text grow">{c.text}</span>
                    {c.done && <span className="small muted">{name(c.doneByUserId)}</span>}
                  </li>
                ))}
              </ul>
            </Card>
          )}

          <Card
            title={`Labour · ${laborHours(wo).toFixed(2)} h`}
            actions={exec && isOpenStatus(wo.status) ? <Button size="sm" icon="plus" onClick={() => setModal("labor")}>Add hours</Button> : undefined}
            tight
          >
            {wo.labor.length === 0 ? (
              <Empty icon="clock" title="No labour logged yet" />
            ) : (
              <table className="data">
                <thead>
                  <tr>
                    <th>Technician</th>
                    <th>Date</th>
                    <th className="num">Hours</th>
                    <th>Note</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {wo.labor.map((l) => (
                    <tr key={l.id}>
                      <td>{name(l.userId)}</td>
                      <td>{formatDate(l.date)}</td>
                      <td className="num">{l.hours}</td>
                      <td>{l.note}</td>
                      <td className="right">
                        {(manage || l.userId === user.id) && isOpenStatus(wo.status) && (
                          <Button size="sm" variant="ghost" icon="trash" aria-label="Remove" onClick={() => mutate((d) => removeLabor(d, wo.id, l.id))} />
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>

          <Card
            title={`Parts used · ${money(partsCost(wo), currency)}`}
            actions={can(user, "part.issue") && exec && isOpenStatus(wo.status) ? <Button size="sm" icon="package" onClick={() => setModal("part")}>Issue / return part</Button> : undefined}
            tight
          >
            {wo.partsUsed.length === 0 ? (
              <Empty icon="package" title="No parts used" />
            ) : (
              <table className="data">
                <thead>
                  <tr>
                    <th>Part</th>
                    <th className="num">Qty</th>
                    <th className="num">Unit cost</th>
                    <th className="num">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {wo.partsUsed.map((p) => {
                    const part = partsById.get(p.partId);
                    return (
                      <tr key={p.id}>
                        <td>{part ? <Link to={`/parts/${part.id}`}>{part.partNo} · {part.name}</Link> : "Unknown part"}</td>
                        <td className="num">
                          {p.qty} {part?.unit}
                        </td>
                        <td className="num">{money(p.unitCost, currency)}</td>
                        <td className="num">{money(p.qty * p.unitCost, currency)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </Card>

          <Card title="Comments">
            {wo.comments.map((c) => (
              <div className="comment" key={c.id}>
                <div className="who">
                  {name(c.userId)} <span className="muted" style={{ fontWeight: 400 }}>· {formatDateTime(c.at)}</span>
                </div>
                <div style={{ whiteSpace: "pre-wrap" }}>{c.text}</div>
              </div>
            ))}
            {can(user, "wo.comment") && (
              <form
                className="flex"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!comment.trim()) return;
                  mutate((d) => addComment(d, wo.id, user.id, comment.trim()), audit("comment", `${wo.woNo}: comment added`));
                  setComment("");
                }}
              >
                <input value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Add a comment" aria-label="Comment" />
                <Button type="submit" disabled={!comment.trim()}>
                  Post
                </Button>
              </form>
            )}
          </Card>
        </div>

        <div className="stack">
          <Card title="Assignment">
            <KV
              items={[
                { k: "Assigned to", v: wo.assignedToUserIds.length ? wo.assignedToUserIds.map(name).join(", ") : <span className="muted">Unassigned</span> },
                { k: "Started", v: formatDateTime(wo.startedAt) },
                { k: "Completed", v: formatDateTime(wo.completedAt) },
                { k: "Closed", v: wo.closedAt ? `${formatDateTime(wo.closedAt)} · ${name(wo.closedByUserId)}` : "—" },
              ]}
            />
          </Card>
          {asset && (
            <Card title="Asset">
              <KV
                items={[
                  { k: "Asset", v: <Link to={`/assets/${asset.id}`}>{asset.assetNo}</Link> },
                  { k: "Name", v: asset.name },
                  { k: "Criticality", v: asset.criticality },
                  { k: "Status", v: <Badge tone={asset.status === "down" ? "critical" : asset.status === "maintenance" ? "warning" : "good"}>{asset.status}</Badge> },
                  ...(asset.meterUnit ? [{ k: "Meter", v: `${asset.meterReading} ${asset.meterUnit}` }] : []),
                  { k: "Location", v: asset.location || "—" },
                ]}
              />
              <div className="mt-8 small">
                <Link to={`/work-orders?q=${encodeURIComponent(asset.assetNo)}&status=all`}>History for this asset</Link>
              </div>
            </Card>
          )}
          <Card title="History" tight>
            <ul className="timeline" style={{ padding: 16 }}>
              {[...wo.history].reverse().map((h, i) => (
                <li key={i}>
                  <div>
                    <strong>{WO_STATUS_LABEL[h.to]}</strong>
                    {h.note && <span className="muted"> · {h.note}</span>}
                  </div>
                  <div className="small muted">
                    {name(h.userId)} · {formatDateTime(h.at)}
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>

      <CompleteModal wo={wo} open={modal === "complete"} onClose={() => setModal(null)} />
      <EditModal wo={wo} open={modal === "edit"} onClose={() => setModal(null)} />
      <LaborModal wo={wo} open={modal === "labor"} onClose={() => setModal(null)} />
      <PartModal wo={wo} open={modal === "part"} onClose={() => setModal(null)} />
      <NoteModal
        open={modal === "hold" || modal === "cancel" || modal === "reopen"}
        title={modal === "hold" ? "Put on hold" : modal === "cancel" ? "Cancel work order" : "Reopen work order"}
        label={modal === "hold" ? "Why is the work on hold? (waiting for parts, access, approval…)" : modal === "cancel" ? "Reason for cancelling" : "Why is it being reopened?"}
        note={note}
        setNote={setNote}
        danger={modal === "cancel"}
        onClose={() => setModal(null)}
        onConfirm={() => {
          const to: WOStatus = modal === "hold" ? "on_hold" : modal === "cancel" ? "cancelled" : "in_progress";
          setStatus(to, note.trim());
          setModal(null);
        }}
      />
    </div>
  );
}

function NoteModal({ open, title, label, note, setNote, danger, onClose, onConfirm }: { open: boolean; title: string; label: string; note: string; setNote: (v: string) => void; danger?: boolean; onClose: () => void; onConfirm: () => void }) {
  return (
    <Modal
      title={title}
      open={open}
      onClose={onClose}
      size="narrow"
      footer={
        <>
          <Button onClick={onClose}>Back</Button>
          <Button variant={danger ? "danger" : "primary"} onClick={onConfirm} disabled={!note.trim()}>
            {title}
          </Button>
        </>
      }
    >
      <Field label={label} required>
        <textarea value={note} onChange={(e) => setNote(e.target.value)} autoFocus />
      </Field>
    </Modal>
  );
}

function CompleteModal({ wo, open, onClose }: { wo: WorkOrder; open: boolean; onClose: () => void }) {
  const { snapshot, mutate, assetsById } = useStore();
  const user = useCurrentUser();
  const toast = useToast();
  const asset = wo.assetId ? assetsById.get(wo.assetId) : undefined;
  const [rootCause, setRootCause] = useState(wo.rootCause);
  const [action, setAction] = useState(wo.actionTaken);
  const [code, setCode] = useState(wo.failureCode);
  const [end, setEnd] = useState(nowLocalInput());
  const [meter, setMeter] = useState(asset?.meterUnit ? String(asset.meterReading) : "");
  const [hours, setHours] = useState(wo.labor.length === 0 ? String(wo.estimatedHours || "") : "");
  const [error, setError] = useState<string | null>(null);
  const isBreakdown = wo.type === "breakdown";
  const openChecklist = wo.checklist.filter((c) => !c.done).length;

  const submit = () => {
    setError(null);
    if (!action.trim()) return setError("Describe what was done");
    if (isBreakdown && !rootCause.trim()) return setError("Enter the root cause");
    const endIso = isBreakdown ? fromLocalInput(end) : null;
    if (isBreakdown && !endIso) return setError("Enter when the machine was back in service");
    if (isBreakdown && endIso && wo.downtimeStart && new Date(endIso).getTime() < new Date(wo.downtimeStart).getTime()) return setError("Back-in-service time is before the stop time");
    const meterValue = meter.trim() === "" ? null : Number(meter);
    if (meterValue !== null && (!Number.isFinite(meterValue) || meterValue < 0)) return setError("Meter reading must be a number");
    const laborValue = Number(hours) || 0;
    mutate(
      (d) => completeWorkOrder(d, wo.id, { rootCause: rootCause.trim(), actionTaken: action.trim(), failureCode: code, downtimeEnd: endIso, meterReading: meterValue, laborHours: laborValue }, user.id),
      { entity: "work_order", entityId: wo.id, action: "complete", summary: `${wo.woNo} completed by ${user.name}` },
    );
    toast.success(`${wo.woNo} completed`);
    onClose();
  };

  return (
    <Modal
      title={`Complete ${wo.woNo}`}
      open={open}
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>Back</Button>
          <Button variant="primary" onClick={submit}>
            Mark completed
          </Button>
        </>
      }
    >
      <div className="form-grid">
        {openChecklist > 0 && (
          <div className="full">
            <Notice tone="warning" icon="alert">
              {openChecklist} checklist step{openChecklist === 1 ? " is" : "s are"} not ticked. You can still complete, but it will show in the record.
            </Notice>
          </div>
        )}
        {isBreakdown && (
          <>
            <Field label="Root cause" required className="full">
              <input value={rootCause} onChange={(e) => setRootCause(e.target.value)} placeholder="What actually failed and why" />
            </Field>
            <Field label="Failure code">
              <select value={code} onChange={(e) => setCode(e.target.value)}>
                <option value="">Not classified</option>
                {snapshot.settings.failureCodes.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Machine back in service at" required hint={wo.downtimeStart ? `Stopped ${formatDateTime(wo.downtimeStart)}` : undefined}>
              <input type="datetime-local" value={end} onChange={(e) => setEnd(e.target.value)} min={toLocalInput(wo.downtimeStart)} />
            </Field>
          </>
        )}
        <Field label="Action taken" required className="full">
          <textarea value={action} onChange={(e) => setAction(e.target.value)} placeholder="What was repaired, replaced, adjusted or checked" />
        </Field>
        {asset?.meterUnit && (
          <Field label={`Meter reading (${asset.meterUnit})`} hint="Updates the asset meter; used for meter-based PM">
            <input type="number" min={0} value={meter} onChange={(e) => setMeter(e.target.value)} />
          </Field>
        )}
        <Field label="Your hours on this job" hint={wo.labor.length ? "Already logged hours stay" : undefined}>
          <input type="number" min={0} step={0.25} value={hours} onChange={(e) => setHours(e.target.value)} />
        </Field>
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

function EditModal({ wo, open, onClose }: { wo: WorkOrder; open: boolean; onClose: () => void }) {
  const { snapshot, mutate, linesById } = useStore();
  const user = useCurrentUser();
  const toast = useToast();
  const [title, setTitle] = useState(wo.title);
  const [description, setDescription] = useState(wo.description);
  const [priority, setPriority] = useState<Priority>(wo.priority);
  const [dueDate, setDueDate] = useState(wo.dueDate ?? "");
  const [estimated, setEstimated] = useState(String(wo.estimatedHours || ""));
  const [assetId, setAssetId] = useState(wo.assetId ?? "");
  const [assigned, setAssigned] = useState<string[]>(wo.assignedToUserIds);
  const technicians = snapshot.users.filter((u) => u.active && (u.role === "technician" || u.role === "maintenance_supervisor"));
  const assets = useMemo(() => snapshot.assets.filter((a) => a.active).sort((a, b) => a.assetNo.localeCompare(b.assetNo)), [snapshot.assets]);

  const submit = () => {
    if (!title.trim()) return;
    mutate(
      (d) => {
        const w = d.workOrders.find((x) => x.id === wo.id);
        if (!w) return;
        w.title = title.trim();
        w.description = description.trim();
        w.priority = priority;
        w.dueDate = dueDate || null;
        w.estimatedHours = Number(estimated) || 0;
        w.assetId = assetId || null;
        const a = assetId ? d.assets.find((x) => x.id === assetId) : undefined;
        w.lineId = a?.lineId ?? w.lineId;
        w.updatedAt = new Date().toISOString();
        assignWorkOrder(d, wo.id, assigned, user.id);
      },
      { entity: "work_order", entityId: wo.id, action: "update", summary: `${wo.woNo} updated by ${user.name}` },
    );
    toast.success("Work order updated");
    onClose();
  };

  return (
    <Modal
      title={`Edit ${wo.woNo}`}
      open={open}
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={!title.trim()}>
            Save
          </Button>
        </>
      }
    >
      <div className="form-grid">
        <Field label="Title" required className="full">
          <input value={title} onChange={(e) => setTitle(e.target.value)} />
        </Field>
        <Field label="Asset" className="full">
          <select value={assetId} onChange={(e) => setAssetId(e.target.value)}>
            <option value="">No specific asset</option>
            {assets.map((a) => (
              <option key={a.id} value={a.id}>
                {a.assetNo} · {a.name}
                {a.lineId ? ` (${linesById.get(a.lineId)?.code ?? ""})` : ""}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Priority">
          <select value={priority} onChange={(e) => setPriority(e.target.value as Priority)}>
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {PRIORITY_LABEL[p]}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Due date">
          <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
        </Field>
        <Field label="Estimated hours">
          <input type="number" min={0} step={0.25} value={estimated} onChange={(e) => setEstimated(e.target.value)} />
        </Field>
        <Field label="Assign to" className="full">
          <ChipSelect options={technicians.map((t) => ({ value: t.id, label: t.name }))} value={assigned} onChange={setAssigned} />
        </Field>
        <Field label="Description" className="full">
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} />
        </Field>
      </div>
    </Modal>
  );
}

function LaborModal({ wo, open, onClose }: { wo: WorkOrder; open: boolean; onClose: () => void }) {
  const { snapshot, mutate } = useStore();
  const user = useCurrentUser();
  const manage = can(user, "wo.assign");
  const [who, setWho] = useState(user.id);
  const [date, setDate] = useState(todayKey());
  const [hours, setHours] = useState("1");
  const [note, setNote] = useState("");
  const people = snapshot.users.filter((u) => u.active && (u.role === "technician" || u.role === "maintenance_supervisor"));
  const submit = () => {
    const h = Number(hours);
    if (!(h > 0) || !date) return;
    mutate((d) => addLabor(d, wo.id, { userId: manage ? who : user.id, date, hours: h, note: note.trim() }), { entity: "work_order", entityId: wo.id, action: "labor", summary: `${wo.woNo}: ${h} h logged` });
    onClose();
  };
  return (
    <Modal title="Add labour" open={open} onClose={onClose} size="narrow" footer={<><Button onClick={onClose}>Cancel</Button><Button variant="primary" onClick={submit}>Add</Button></>}>
      <div className="stack">
        {manage && (
          <Field label="Technician">
            <select value={who} onChange={(e) => setWho(e.target.value)}>
              {people.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </Field>
        )}
        <Field label="Date" required>
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} max={todayKey()} />
        </Field>
        <Field label="Hours" required>
          <input type="number" min={0.25} step={0.25} value={hours} onChange={(e) => setHours(e.target.value)} />
        </Field>
        <Field label="Note">
          <input value={note} onChange={(e) => setNote(e.target.value)} />
        </Field>
      </div>
    </Modal>
  );
}

function PartModal({ wo, open, onClose }: { wo: WorkOrder; open: boolean; onClose: () => void }) {
  const { snapshot, mutate, partsById } = useStore();
  const user = useCurrentUser();
  const toast = useToast();
  const [direction, setDirection] = useState<"issue" | "return">("issue");
  const [partId, setPartId] = useState("");
  const [qty, setQty] = useState("1");
  const [error, setError] = useState<string | null>(null);
  const parts = useMemo(() => {
    const list = direction === "return" ? wo.partsUsed.map((p) => partsById.get(p.partId)).filter((p): p is NonNullable<typeof p> => Boolean(p)) : snapshot.parts.filter((p) => p.active);
    const linked = (id: string) => (wo.assetId && partsById.get(id)?.assetIds.includes(wo.assetId) ? 0 : 1);
    return [...list].sort((a, b) => linked(a.id) - linked(b.id) || a.partNo.localeCompare(b.partNo));
  }, [direction, wo, snapshot.parts, partsById]);
  const part = partsById.get(partId);

  const submit = () => {
    setError(null);
    if (!partId) return setError("Select a part");
    let err: string | null = null;
    mutate(
      (d) => {
        err = movePart(d, wo.id, partId, Number(qty), user.id, direction);
      },
      { entity: "work_order", entityId: wo.id, action: direction, summary: `${wo.woNo}: ${qty} x ${part?.partNo ?? ""} ${direction === "issue" ? "issued" : "returned"}` },
    );
    if (err) return setError(err);
    toast.success(direction === "issue" ? "Part issued" : "Part returned");
    onClose();
  };

  return (
    <Modal title="Issue or return a part" open={open} onClose={onClose} size="narrow" footer={<><Button onClick={onClose}>Cancel</Button><Button variant="primary" onClick={submit}>{direction === "issue" ? "Issue" : "Return"}</Button></>}>
      <div className="stack">
        <div className="chips">
          <button type="button" className={`chip ${direction === "issue" ? "on" : ""}`} onClick={() => setDirection("issue")}>Issue from stock</button>
          <button type="button" className={`chip ${direction === "return" ? "on" : ""}`} onClick={() => setDirection("return")}>Return to stock</button>
        </div>
        <Field label="Part" required hint={part ? `${part.stock} ${part.unit} in stock · ${part.location}` : "Parts linked to this asset are listed first"}>
          <select value={partId} onChange={(e) => setPartId(e.target.value)}>
            <option value="">Select a part</option>
            {parts.map((p) => (
              <option key={p.id} value={p.id}>
                {p.partNo} · {p.name} ({p.stock} {p.unit})
              </option>
            ))}
          </select>
        </Field>
        <Field label="Quantity" required error={error}>
          <input type="number" min={0.01} step="any" value={qty} onChange={(e) => setQty(e.target.value)} />
        </Field>
      </div>
    </Modal>
  );
}
