import { useEffect, useState } from "react";
import type { Part } from "../types";
import { newId, nowIso } from "../lib/ids";
import { useCurrentUser, useStore } from "../store/StoreProvider";
import { useToast } from "./Toast";
import { Button, ChipSelect, Field, Modal, Notice } from "./ui";

export function PartForm({ open, part, onClose, onSaved }: { open: boolean; part?: Part; onClose: () => void; onSaved?: (id: string) => void }) {
  const { snapshot, mutate } = useStore();
  const user = useCurrentUser();
  const toast = useToast();
  const blank = () => ({
    partNo: `SP-${String(1000 + snapshot.sequences.part + 1)}`,
    name: "",
    description: "",
    category: "",
    unit: "pc",
    stock: "0",
    minStock: "0",
    maxStock: "0",
    location: "",
    unitCost: "0",
    supplier: "",
    leadTimeDays: "7",
    assetIds: [] as string[],
    active: true,
  });
  const [f, setF] = useState(blank);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    if (part) {
      setF({
        partNo: part.partNo,
        name: part.name,
        description: part.description,
        category: part.category,
        unit: part.unit,
        stock: String(part.stock),
        minStock: String(part.minStock),
        maxStock: String(part.maxStock),
        location: part.location,
        unitCost: String(part.unitCost),
        supplier: part.supplier,
        leadTimeDays: String(part.leadTimeDays),
        assetIds: part.assetIds,
        active: part.active,
      });
    } else setF(blank());
    setError(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, part?.id]);

  const set = <K extends keyof typeof f>(key: K, value: (typeof f)[K]) => setF((s) => ({ ...s, [key]: value }));
  const assets = snapshot.assets.filter((a) => a.active).sort((a, b) => a.assetNo.localeCompare(b.assetNo));

  const submit = () => {
    setError(null);
    const no = f.partNo.trim();
    if (!no) return setError("Part number is required");
    if (!f.name.trim()) return setError("Name is required");
    if (snapshot.parts.some((p) => p.partNo.toLowerCase() === no.toLowerCase() && p.id !== part?.id)) return setError(`Part number ${no} already exists`);
    const now = nowIso();
    let id = part?.id ?? "";
    mutate(
      (d) => {
        const data = {
          partNo: no,
          name: f.name.trim(),
          description: f.description.trim(),
          category: f.category.trim(),
          unit: f.unit.trim() || "pc",
          minStock: Math.max(0, Number(f.minStock) || 0),
          maxStock: Math.max(0, Number(f.maxStock) || 0),
          location: f.location.trim(),
          unitCost: Math.max(0, Number(f.unitCost) || 0),
          supplier: f.supplier.trim(),
          leadTimeDays: Math.max(0, Number(f.leadTimeDays) || 0),
          assetIds: f.assetIds,
          active: f.active,
          updatedAt: now,
        };
        if (part) {
          const p = d.parts.find((x) => x.id === part.id);
          if (p) Object.assign(p, data);
        } else {
          id = newId();
          d.sequences.part += 1;
          const stock = Math.max(0, Number(f.stock) || 0);
          d.parts.push({ id, ...data, stock, createdAt: now });
          if (stock > 0) d.stockTransactions.push({ id: newId(), partId: id, type: "receive", qty: stock, unitCost: data.unitCost, workOrderId: null, userId: user.id, at: now, note: "Opening stock" });
        }
      },
      { entity: "part", entityId: id || no, action: part ? "update" : "create", summary: `Part ${no} ${part ? "updated" : "created"} by ${user.name}` },
    );
    toast.success(part ? "Part updated" : "Part created");
    onClose();
    if (!part && id) onSaved?.(id);
  };

  return (
    <Modal
      title={part ? `Edit ${part.partNo}` : "New spare part"}
      open={open}
      onClose={onClose}
      size="wide"
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit}>
            {part ? "Save" : "Create part"}
          </Button>
        </>
      }
    >
      <div className="form-grid">
        <Field label="Part number" required>
          <input value={f.partNo} onChange={(e) => set("partNo", e.target.value)} />
        </Field>
        <Field label="Name" required>
          <input value={f.name} onChange={(e) => set("name", e.target.value)} />
        </Field>
        <Field label="Category">
          <input list="part-categories" value={f.category} onChange={(e) => set("category", e.target.value)} />
          <datalist id="part-categories">
            {snapshot.settings.partCategories.map((c) => (
              <option key={c} value={c} />
            ))}
          </datalist>
        </Field>
        <Field label="Unit">
          <input value={f.unit} onChange={(e) => set("unit", e.target.value)} placeholder="pc, litre, kg, m" />
        </Field>
        {!part && (
          <Field label="Opening stock">
            <input type="number" min={0} step="any" value={f.stock} onChange={(e) => set("stock", e.target.value)} />
          </Field>
        )}
        <Field label="Minimum stock" hint="Alert when stock is at or below this">
          <input type="number" min={0} step="any" value={f.minStock} onChange={(e) => set("minStock", e.target.value)} />
        </Field>
        <Field label="Maximum stock">
          <input type="number" min={0} step="any" value={f.maxStock} onChange={(e) => set("maxStock", e.target.value)} />
        </Field>
        <Field label={`Unit cost (${snapshot.settings.currency})`}>
          <input type="number" min={0} step="any" value={f.unitCost} onChange={(e) => set("unitCost", e.target.value)} />
        </Field>
        <Field label="Storage location">
          <input value={f.location} onChange={(e) => set("location", e.target.value)} placeholder="Rack A1, Drawer 3" />
        </Field>
        <Field label="Supplier">
          <input value={f.supplier} onChange={(e) => set("supplier", e.target.value)} />
        </Field>
        <Field label="Lead time (days)">
          <input type="number" min={0} value={f.leadTimeDays} onChange={(e) => set("leadTimeDays", e.target.value)} />
        </Field>
        <Field label="Used on assets" className="full">
          <ChipSelect options={assets.map((a) => ({ value: a.id, label: a.assetNo }))} value={f.assetIds} onChange={(v) => set("assetIds", v)} />
        </Field>
        <Field label="Description" className="full">
          <textarea value={f.description} onChange={(e) => set("description", e.target.value)} />
        </Field>
        <label className="check">
          <input type="checkbox" checked={f.active} onChange={(e) => set("active", e.target.checked)} /> Active
        </label>
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

export function StockModal({ open, partId, mode, onClose }: { open: boolean; partId: string; mode: "receive" | "adjust"; onClose: () => void }) {
  const { partsById, mutate } = useStore();
  const user = useCurrentUser();
  const toast = useToast();
  const part = partsById.get(partId);
  const [qty, setQty] = useState("1");
  const [cost, setCost] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (open) {
      setQty(mode === "receive" ? "1" : "0");
      setCost(part ? String(part.unitCost) : "");
      setNote("");
      setError(null);
    }
  }, [open, mode, part]);
  if (!part) return null;

  const submit = () => {
    setError(null);
    const n = Number(qty);
    if (!Number.isFinite(n)) return setError("Enter a number");
    if (mode === "adjust" && !note.trim()) return setError("Give a reason for the adjustment");
    let err: string | null = null;
    mutate(
      (d) => {
        err = mode === "receive" ? adjust(d, "receive", n) : adjust(d, "adjust", n - part.stock);
      },
      { entity: "part", entityId: part.id, action: mode, summary: mode === "receive" ? `${n} ${part.unit} of ${part.partNo} received` : `${part.partNo} stock adjusted to ${n} ${part.unit}: ${note.trim()}` },
    );
    if (err) return setError(err);
    toast.success(mode === "receive" ? "Stock received" : "Stock adjusted");
    onClose();

    function adjust(d: Parameters<Parameters<typeof mutate>[0]>[0], type: "receive" | "adjust", delta: number): string | null {
      const p = d.parts.find((x) => x.id === part!.id);
      if (!p) return "Part not found";
      if (type === "receive" && !(delta > 0)) return "Quantity must be more than zero";
      if (p.stock + delta < 0) return "Stock cannot go below zero";
      const now = nowIso();
      const unitCost = type === "receive" && cost.trim() !== "" ? Math.max(0, Number(cost) || 0) : p.unitCost;
      p.stock += delta;
      if (type === "receive") p.unitCost = unitCost;
      p.updatedAt = now;
      d.stockTransactions.push({ id: newId(), partId: p.id, type, qty: delta, unitCost, workOrderId: null, userId: user.id, at: now, note: note.trim() });
      return null;
    }
  };

  return (
    <Modal title={`${mode === "receive" ? "Receive stock" : "Adjust stock"} · ${part.partNo}`} open={open} onClose={onClose} size="narrow" footer={<><Button onClick={onClose}>Cancel</Button><Button variant="primary" onClick={submit}>{mode === "receive" ? "Receive" : "Adjust"}</Button></>}>
      <div className="stack">
        <div className="small muted">
          Current stock {part.stock} {part.unit} · {part.location}
        </div>
        <Field label={mode === "receive" ? `Quantity received (${part.unit})` : `Counted stock (${part.unit})`} required>
          <input type="number" min={0} step="any" value={qty} onChange={(e) => setQty(e.target.value)} autoFocus />
        </Field>
        {mode === "receive" && (
          <Field label="Unit cost" hint="Updates the part's unit cost">
            <input type="number" min={0} step="any" value={cost} onChange={(e) => setCost(e.target.value)} />
          </Field>
        )}
        <Field label={mode === "receive" ? "Note (PO number, supplier…)" : "Reason"} required={mode === "adjust"} error={error}>
          <input value={note} onChange={(e) => setNote(e.target.value)} />
        </Field>
      </div>
    </Modal>
  );
}
