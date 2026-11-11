import { useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { PartForm, StockModal } from "../components/PartForm";
import { useToast } from "../components/Toast";
import { Badge, Button, Card, Empty, PageHeader, Search, money, usePaged } from "../components/ui";
import { parseCsv } from "../lib/csv";
import { downloadWorkbook, snapshotSheets } from "../lib/excel";
import { newId, nowIso } from "../lib/ids";
import { can } from "../lib/permissions";
import { useCurrentUser, useStore } from "../store/StoreProvider";

export function Parts() {
  const { snapshot, mutate } = useStore();
  const user = useCurrentUser();
  const navigate = useNavigate();
  const toast = useToast();
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const low = params.get("filter") === "low";
  const [formOpen, setFormOpen] = useState(false);
  const [stock, setStock] = useState<{ id: string; mode: "receive" | "adjust" } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const manage = can(user, "part.manage");
  const currency = snapshot.settings.currency;

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return snapshot.parts
      .filter((p) => {
        if (low && !(p.minStock > 0 && p.stock <= p.minStock)) return false;
        if (category && p.category !== category) return false;
        if (needle && !`${p.partNo} ${p.name} ${p.description} ${p.supplier} ${p.location}`.toLowerCase().includes(needle)) return false;
        return true;
      })
      .sort((a, b) => (a.active === b.active ? a.partNo.localeCompare(b.partNo) : a.active ? -1 : 1));
  }, [snapshot.parts, q, category, low]);
  const paged = usePaged(rows, 50);
  const categories = [...new Set(snapshot.parts.map((p) => p.category).filter(Boolean))].sort();
  const lowCount = snapshot.parts.filter((p) => p.active && p.minStock > 0 && p.stock <= p.minStock).length;
  const stockValue = snapshot.parts.filter((p) => p.active).reduce((s, p) => s + p.stock * p.unitCost, 0);

  const importCsv = async (file: File) => {
    try {
      const rowsIn = parseCsv(await file.text());
      if (rowsIn.length === 0) return toast.error("The file has no rows");
      let created = 0;
      let updated = 0;
      const now = nowIso();
      mutate(
        (d) => {
          for (const r of rowsIn) {
            const no = (r.part_no ?? r.partno ?? "").trim();
            if (!no) continue;
            const assetIds = (r.assets ?? "")
              .split(/[;|]/)
              .map((s) => s.trim().toLowerCase())
              .filter(Boolean)
              .map((code) => d.assets.find((a) => a.assetNo.toLowerCase() === code)?.id)
              .filter((id): id is string => Boolean(id));
            const data = {
              name: r.name || no,
              description: r.description ?? "",
              category: r.category ?? "",
              unit: r.unit || "pc",
              minStock: Number(r.min_stock) || 0,
              maxStock: Number(r.max_stock) || 0,
              location: r.location ?? "",
              unitCost: Number(r.unit_cost) || 0,
              supplier: r.supplier ?? "",
              leadTimeDays: Number(r.lead_time_days) || 0,
              updatedAt: now,
            };
            const existing = d.parts.find((p) => p.partNo.toLowerCase() === no.toLowerCase());
            if (existing) {
              Object.assign(existing, data);
              if (assetIds.length) existing.assetIds = assetIds;
              updated += 1;
            } else {
              const stockQty = Number(r.stock) || 0;
              const id = newId();
              d.sequences.part += 1;
              d.parts.push({ id, partNo: no, ...data, stock: stockQty, assetIds, active: true, createdAt: now });
              if (stockQty > 0) d.stockTransactions.push({ id: newId(), partId: id, type: "receive", qty: stockQty, unitCost: data.unitCost, workOrderId: null, userId: user.id, at: now, note: `Imported from ${file.name}` });
              created += 1;
            }
          }
        },
        { entity: "part", entityId: "import", action: "import", summary: `Parts imported from ${file.name}` },
      );
      toast.success(`Import done: ${created} created, ${updated} updated`);
    } catch (err) {
      toast.error(`Import failed: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  return (
    <div>
      <PageHeader
        title="Spare parts"
        subtitle={`${snapshot.parts.filter((p) => p.active).length} parts · ${lowCount} below minimum · stock value ${money(stockValue, currency)}`}
        actions={
          <>
            {can(user, "data.export") && (
              <Button icon="download" onClick={() => downloadWorkbook("CMMS_Eaton-parts.xlsx", snapshotSheets(snapshot).filter((s) => s.name === "Spare parts" || s.name === "Stock transactions"))}>
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
                New part
              </Button>
            )}
          </>
        }
      />
      <div className="filters">
        <Search value={q} onChange={setQ} placeholder="Search part no, name, supplier, location" />
        <select value={category} onChange={(e) => setCategory(e.target.value)} aria-label="Category">
          <option value="">All categories</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <label className="check small">
          <input type="checkbox" checked={low} onChange={(e) => { const next = new URLSearchParams(params); if (e.target.checked) next.set("filter", "low"); else next.delete("filter"); setParams(next, { replace: true }); }} /> Below minimum only
        </label>
      </div>
      <Card tight>
        {rows.length === 0 ? (
          <Empty icon="package" title="No parts match" text={manage ? "Add parts or import a CSV with columns part_no, name, description, category, unit, stock, min_stock, max_stock, location, unit_cost, supplier, lead_time_days, assets (asset numbers separated by ;)." : undefined} />
        ) : (
          <>
            <div className="table-wrap">
              <table className="data responsive">
                <thead>
                  <tr>
                    <th>Part</th>
                    <th>Category</th>
                    <th className="num">Stock</th>
                    <th className="num">Min / max</th>
                    <th>Location</th>
                    <th className="num">Unit cost</th>
                    <th>Supplier</th>
                    {manage && <th />}
                  </tr>
                </thead>
                <tbody>
                  {paged.visible.map((p) => {
                    const lowStock = p.minStock > 0 && p.stock <= p.minStock;
                    return (
                      <tr key={p.id} className="clickable" onClick={() => navigate(`/parts/${p.id}`)}>
                        <td data-label="Part">
                          <div className="primary-cell">{p.partNo}{!p.active && <span className="badge" style={{ marginLeft: 6 }}>inactive</span>}</div>
                          <div className="sub-cell">{p.name}</div>
                        </td>
                        <td data-label="Category">{p.category || "—"}</td>
                        <td data-label="Stock" className="num">
                          <Badge tone={p.stock === 0 ? "critical" : lowStock ? "warning" : "good"}>
                            {p.stock} {p.unit}
                          </Badge>
                        </td>
                        <td data-label="Min / max" className="num">
                          {p.minStock} / {p.maxStock}
                        </td>
                        <td data-label="Location">{p.location || "—"}</td>
                        <td data-label="Unit cost" className="num">{money(p.unitCost, currency)}</td>
                        <td data-label="Supplier">
                          {p.supplier || "—"}
                          {p.leadTimeDays > 0 && <div className="sub-cell">{p.leadTimeDays} days lead</div>}
                        </td>
                        {manage && (
                          <td data-label="" className="right nowrap" onClick={(e) => e.stopPropagation()}>
                            <Button size="sm" onClick={() => setStock({ id: p.id, mode: "receive" })}>
                              Receive
                            </Button>
                          </td>
                        )}
                      </tr>
                    );
                  })}
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
      <PartForm open={formOpen} onClose={() => setFormOpen(false)} onSaved={(id) => navigate(`/parts/${id}`)} />
      {stock && <StockModal open partId={stock.id} mode={stock.mode} onClose={() => setStock(null)} />}
    </div>
  );
}
