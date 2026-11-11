import { useEffect, useState } from "react";
import type { Asset, AssetStatus, Criticality } from "../types";
import { ASSET_STATUS_LABELS } from "../types";
import { newId, nowIso } from "../lib/ids";
import { useCurrentUser, useStore } from "../store/StoreProvider";
import { useToast } from "./Toast";
import { Button, Field, Modal, Notice } from "./ui";

export function AssetForm({ open, asset, parentId, onClose, onSaved }: { open: boolean; asset?: Asset; parentId?: string | null; onClose: () => void; onSaved?: (id: string) => void }) {
  const { snapshot, mutate } = useStore();
  const user = useCurrentUser();
  const toast = useToast();
  const blank = () => ({
    assetNo: `EQ-${String(snapshot.sequences.asset + 1).padStart(3, "0")}`,
    name: "",
    lineId: "",
    parentId: parentId ?? "",
    category: "",
    make: "",
    model: "",
    serialNo: "",
    criticality: "B" as Criticality,
    status: "running" as AssetStatus,
    location: "",
    installDate: "",
    meterUnit: "",
    meterReading: "0",
    specs: [] as { key: string; value: string }[],
    notes: "",
    active: true,
  });
  const [f, setF] = useState(blank);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    if (asset) {
      setF({
        assetNo: asset.assetNo,
        name: asset.name,
        lineId: asset.lineId ?? "",
        parentId: asset.parentId ?? "",
        category: asset.category,
        make: asset.make,
        model: asset.model,
        serialNo: asset.serialNo,
        criticality: asset.criticality,
        status: asset.status,
        location: asset.location,
        installDate: asset.installDate ?? "",
        meterUnit: asset.meterUnit,
        meterReading: String(asset.meterReading),
        specs: asset.specs.map((s) => ({ ...s })),
        notes: asset.notes,
        active: asset.active,
      });
    } else {
      const b = blank();
      const parent = parentId ? snapshot.assets.find((a) => a.id === parentId) : undefined;
      if (parent) {
        b.lineId = parent.lineId ?? "";
        b.location = parent.location;
        b.criticality = parent.criticality;
        b.category = "Component";
      }
      setF(b);
    }
    setError(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, asset?.id, parentId]);

  const set = <K extends keyof typeof f>(key: K, value: (typeof f)[K]) => setF((s) => ({ ...s, [key]: value }));
  const parents = snapshot.assets.filter((a) => a.active && a.parentId === null && a.id !== asset?.id && (!f.lineId || a.lineId === f.lineId));

  const submit = () => {
    setError(null);
    const no = f.assetNo.trim();
    if (!no) return setError("Asset number is required");
    if (!f.name.trim()) return setError("Name is required");
    if (snapshot.assets.some((a) => a.assetNo.toLowerCase() === no.toLowerCase() && a.id !== asset?.id)) return setError(`Asset number ${no} already exists`);
    const now = nowIso();
    let id = asset?.id ?? "";
    mutate(
      (d) => {
        const data = {
          assetNo: no,
          name: f.name.trim(),
          lineId: f.lineId || null,
          parentId: f.parentId || null,
          category: f.category.trim(),
          make: f.make.trim(),
          model: f.model.trim(),
          serialNo: f.serialNo.trim(),
          criticality: f.criticality,
          status: f.status,
          location: f.location.trim(),
          installDate: f.installDate || null,
          meterUnit: f.meterUnit.trim(),
          meterReading: Number(f.meterReading) || 0,
          specs: f.specs.filter((s) => s.key.trim()).map((s) => ({ key: s.key.trim(), value: s.value.trim() })),
          notes: f.notes.trim(),
          active: f.active,
          updatedAt: now,
        };
        if (asset) {
          const a = d.assets.find((x) => x.id === asset.id);
          if (!a) return;
          const meterChanged = a.meterReading !== data.meterReading;
          Object.assign(a, data);
          if (meterChanged) a.meterUpdatedAt = now;
        } else {
          id = newId();
          d.sequences.asset += 1;
          d.assets.push({ id, ...data, meterUpdatedAt: data.meterUnit ? now : null, createdAt: now });
        }
      },
      { entity: "asset", entityId: id || no, action: asset ? "update" : "create", summary: `Asset ${no} ${asset ? "updated" : "created"} by ${user.name}` },
    );
    toast.success(asset ? "Asset updated" : "Asset created");
    onClose();
    if (!asset && id) onSaved?.(id);
  };

  return (
    <Modal
      title={asset ? `Edit ${asset.assetNo}` : parentId ? "New component" : "New asset"}
      open={open}
      onClose={onClose}
      size="wide"
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button variant="primary" onClick={submit}>
            {asset ? "Save" : "Create asset"}
          </Button>
        </>
      }
    >
      <div className="form-grid">
        <Field label="Asset number" required>
          <input value={f.assetNo} onChange={(e) => set("assetNo", e.target.value)} />
        </Field>
        <Field label="Name" required>
          <input value={f.name} onChange={(e) => set("name", e.target.value)} />
        </Field>
        <Field label="Line">
          <select value={f.lineId} onChange={(e) => set("lineId", e.target.value)}>
            <option value="">No line</option>
            {snapshot.lines.filter((l) => l.active).map((l) => (
              <option key={l.id} value={l.id}>
                {l.code} · {l.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Part of (parent machine)" hint="Leave empty for a top-level machine">
          <select value={f.parentId} onChange={(e) => set("parentId", e.target.value)}>
            <option value="">None</option>
            {parents.map((a) => (
              <option key={a.id} value={a.id}>
                {a.assetNo} · {a.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Category">
          <input list="asset-categories" value={f.category} onChange={(e) => set("category", e.target.value)} />
          <datalist id="asset-categories">
            {snapshot.settings.assetCategories.map((c) => (
              <option key={c} value={c} />
            ))}
          </datalist>
        </Field>
        <Field label="Criticality" hint="A: production stops · B: reduced output · C: no immediate effect">
          <select value={f.criticality} onChange={(e) => set("criticality", e.target.value as Criticality)}>
            <option value="A">A · critical</option>
            <option value="B">B · important</option>
            <option value="C">C · standard</option>
          </select>
        </Field>
        <Field label="Make">
          <input value={f.make} onChange={(e) => set("make", e.target.value)} />
        </Field>
        <Field label="Model">
          <input value={f.model} onChange={(e) => set("model", e.target.value)} />
        </Field>
        <Field label="Serial number">
          <input value={f.serialNo} onChange={(e) => set("serialNo", e.target.value)} />
        </Field>
        <Field label="Location">
          <input value={f.location} onChange={(e) => set("location", e.target.value)} />
        </Field>
        <Field label="Status">
          <select value={f.status} onChange={(e) => set("status", e.target.value as AssetStatus)}>
            {(Object.keys(ASSET_STATUS_LABELS) as AssetStatus[]).map((s) => (
              <option key={s} value={s}>
                {ASSET_STATUS_LABELS[s]}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Install date">
          <input type="date" value={f.installDate} onChange={(e) => set("installDate", e.target.value)} />
        </Field>
        <Field label="Meter unit" hint="hours, cycles, km… leave empty if none">
          <input value={f.meterUnit} onChange={(e) => set("meterUnit", e.target.value)} />
        </Field>
        <Field label="Meter reading">
          <input type="number" min={0} value={f.meterReading} onChange={(e) => set("meterReading", e.target.value)} disabled={!f.meterUnit.trim()} />
        </Field>
        <div className="full">
          <div className="field">
            <span className="label">Specifications</span>
          </div>
          {f.specs.map((s, i) => (
            <div className="flex mb-8" key={i}>
              <input placeholder="Name (e.g. Rated power)" value={s.key} onChange={(e) => set("specs", f.specs.map((x, j) => (j === i ? { ...x, key: e.target.value } : x)))} />
              <input placeholder="Value" value={s.value} onChange={(e) => set("specs", f.specs.map((x, j) => (j === i ? { ...x, value: e.target.value } : x)))} />
              <Button variant="ghost" icon="trash" aria-label="Remove" onClick={() => set("specs", f.specs.filter((_, j) => j !== i))} />
            </div>
          ))}
          <Button size="sm" icon="plus" onClick={() => set("specs", [...f.specs, { key: "", value: "" }])}>
            Add specification
          </Button>
        </div>
        <Field label="Notes" className="full">
          <textarea value={f.notes} onChange={(e) => set("notes", e.target.value)} />
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
