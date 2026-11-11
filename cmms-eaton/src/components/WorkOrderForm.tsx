import { useEffect, useMemo, useState } from "react";
import type { Priority, WOType } from "../types";
import { fromLocalInput, nowLocalInput, shiftForIso, todayKey } from "../lib/dates";
import { newId } from "../lib/ids";
import { createWorkOrder } from "../lib/mutations";
import { can } from "../lib/permissions";
import { PRIORITIES, PRIORITY_LABEL, priorityForBreakdown, WO_TYPES } from "../lib/workorders";
import { useCurrentUser, useStore } from "../store/StoreProvider";
import { useToast } from "./Toast";
import { Button, ChipSelect, Field, Modal, Notice } from "./ui";

export interface WorkOrderFormProps {
  open: boolean;
  onClose: () => void;
  onCreated?: (id: string) => void;
  initialType?: WOType;
  initialAssetId?: string | null;
}

export function WorkOrderForm({ open, onClose, onCreated, initialType, initialAssetId }: WorkOrderFormProps) {
  const { snapshot, mutate, linesById } = useStore();
  const user = useCurrentUser();
  const toast = useToast();
  const fullCreate = can(user, "wo.create");

  const allowedTypes = useMemo(() => {
    if (fullCreate) return WO_TYPES;
    const basic: WOType[] = user.role === "production_supervisor" ? ["breakdown", "safety", "improvement", "other"] : ["breakdown", "corrective", "safety", "improvement", "inspection", "other"];
    return WO_TYPES.filter((t) => basic.includes(t.value));
  }, [fullCreate, user.role]);

  const [type, setType] = useState<WOType>(initialType ?? "breakdown");
  const [title, setTitle] = useState("");
  const [assetId, setAssetId] = useState<string>(initialAssetId ?? "");
  const [priority, setPriority] = useState<Priority | "">("");
  const [description, setDescription] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [assigned, setAssigned] = useState<string[]>([]);
  const [estimated, setEstimated] = useState("");
  const [stoppedAt, setStoppedAt] = useState(nowLocalInput());
  const [failureCode, setFailureCode] = useState("");
  const [checklist, setChecklist] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setType(initialType ?? "breakdown");
    setTitle("");
    setAssetId(initialAssetId ?? "");
    setPriority("");
    setDescription("");
    setDueDate("");
    setAssigned([]);
    setEstimated("");
    setStoppedAt(nowLocalInput());
    setFailureCode("");
    setChecklist("");
    setError(null);
  }, [open, initialType, initialAssetId]);

  const assets = useMemo(() => {
    const visible = snapshot.assets.filter((a) => a.active && a.status !== "retired");
    if (user.role === "production_supervisor" && user.lineIds.length > 0) return visible.filter((a) => a.lineId && user.lineIds.includes(a.lineId));
    return visible.sort((a, b) => a.assetNo.localeCompare(b.assetNo));
  }, [snapshot.assets, user]);
  const asset = assets.find((a) => a.id === assetId);
  const line = asset?.lineId ? linesById.get(asset.lineId) : undefined;
  const technicians = snapshot.users.filter((u) => u.active && (u.role === "technician" || u.role === "maintenance_supervisor"));
  const isBreakdown = type === "breakdown";
  const stoppedIso = fromLocalInput(stoppedAt);
  const shift = stoppedIso ? shiftForIso(stoppedIso, snapshot.settings.shifts) : null;
  const shiftWarning = shift && line && !line.shifts.includes(shift) ? `Line ${line.code} does not normally run shift ${shift}` : null;
  const effectivePriority: Priority = priority || (isBreakdown && asset ? priorityForBreakdown(asset.criticality) : "medium");

  const submit = () => {
    setError(null);
    if (!title.trim()) return setError("Give the work order a title");
    if (isBreakdown && !assetId) return setError("Select the machine that stopped");
    if (isBreakdown && !stoppedIso) return setError("Enter when the machine stopped");
    if (isBreakdown && stoppedIso && new Date(stoppedIso).getTime() > Date.now() + 5 * 60_000) return setError("Stop time cannot be in the future");
    let createdId = "";
    mutate(
      (d) => {
        const wo = createWorkOrder(
          d,
          {
            type,
            title: title.trim(),
            description: description.trim(),
            assetId: assetId || null,
            priority: effectivePriority,
            dueDate: dueDate || (isBreakdown ? todayKey() : null),
            assignedToUserIds: fullCreate ? assigned : [],
            estimatedHours: fullCreate ? Number(estimated) || 0 : 0,
            downtimeStart: isBreakdown ? stoppedIso : null,
            failureCode: isBreakdown ? failureCode : "",
            checklist: fullCreate
              ? checklist
                  .split("\n")
                  .map((s) => s.trim())
                  .filter(Boolean)
                  .map((text) => ({ id: newId(), text, done: false, doneByUserId: null, doneAt: null }))
              : [],
          },
          user.id,
        );
        createdId = wo.id;
        d.audit.unshift({ id: newId(), at: wo.createdAt, userId: user.id, entity: "work_order", entityId: wo.id, action: "create", summary: `${wo.woNo} created: ${wo.title}` });
      },
    );
    toast.success(isBreakdown ? "Breakdown reported" : "Work order created");
    onClose();
    if (createdId) onCreated?.(createdId);
  };

  return (
    <Modal
      title={isBreakdown ? "Report a breakdown" : "New work order"}
      open={open}
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit}>
            {isBreakdown ? "Report breakdown" : "Create work order"}
          </Button>
        </>
      }
    >
      <form
        className="form-grid"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <Field label="Type" required>
          <select value={type} onChange={(e) => setType(e.target.value as WOType)}>
            {allowedTypes.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Priority" hint={!priority && asset ? `Auto from criticality ${asset.criticality}: ${PRIORITY_LABEL[effectivePriority]}` : undefined}>
          <select value={priority} onChange={(e) => setPriority(e.target.value as Priority | "")} disabled={!fullCreate && !isBreakdown ? false : false}>
            <option value="">Automatic</option>
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {PRIORITY_LABEL[p]}
              </option>
            ))}
          </select>
        </Field>
        <Field label={isBreakdown ? "Machine" : "Asset"} required={isBreakdown} className="full">
          <select value={assetId} onChange={(e) => setAssetId(e.target.value)}>
            <option value="">{isBreakdown ? "Select the machine" : "No specific asset"}</option>
            {assets.map((a) => (
              <option key={a.id} value={a.id}>
                {a.assetNo} · {a.name}
                {a.lineId ? ` (${linesById.get(a.lineId)?.code ?? ""})` : ""}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Title" required className="full">
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder={isBreakdown ? "What happened? e.g. Press will not cycle, alarm E42" : "Short description of the work"} />
        </Field>
        {isBreakdown && (
          <>
            <Field label="Machine stopped at" required hint={shift ? `Shift ${shift}${line ? ` · line ${line.code}` : ""}` : undefined}>
              <input type="datetime-local" value={stoppedAt} onChange={(e) => setStoppedAt(e.target.value)} max={nowLocalInput()} />
            </Field>
            <Field label="Failure code">
              <select value={failureCode} onChange={(e) => setFailureCode(e.target.value)}>
                <option value="">Not known yet</option>
                {snapshot.settings.failureCodes.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </Field>
            {shiftWarning && (
              <div className="full">
                <Notice tone="warning" icon="alert">
                  {shiftWarning}. The shift is recorded as {shift}; check the stop time.
                </Notice>
              </div>
            )}
          </>
        )}
        <Field label="Description" className="full">
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Symptoms, alarms, what the operator saw, safety notes" />
        </Field>
        {!isBreakdown && (
          <Field label="Due date">
            <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
          </Field>
        )}
        {fullCreate && (
          <>
            <Field label="Estimated hours">
              <input type="number" min={0} step={0.25} value={estimated} onChange={(e) => setEstimated(e.target.value)} />
            </Field>
            <Field label="Assign to" className="full">
              <ChipSelect options={technicians.map((t) => ({ value: t.id, label: t.name }))} value={assigned} onChange={setAssigned} />
            </Field>
            {!isBreakdown && (
              <Field label="Checklist" hint="One step per line" className="full">
                <textarea value={checklist} onChange={(e) => setChecklist(e.target.value)} placeholder={"LOTO applied\nInspect ...\nTest run"} />
              </Field>
            )}
          </>
        )}
        {error && (
          <div className="full">
            <Notice tone="critical" icon="alert">
              {error}
            </Notice>
          </div>
        )}
        <button type="submit" className="sr-only">
          Save
        </button>
      </form>
    </Modal>
  );
}
