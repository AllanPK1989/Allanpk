import { useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Icon } from "../components/icons";
import { PartForm, StockModal } from "../components/PartForm";
import { Badge, Button, Card, Empty, KV, PageHeader, Stat, money, usePaged } from "../components/ui";
import { formatDateTime } from "../lib/dates";
import { can } from "../lib/permissions";
import { useCurrentUser, useStore } from "../store/StoreProvider";

export function PartDetail() {
  const { id } = useParams();
  const { snapshot, assetsById, usersById } = useStore();
  const user = useCurrentUser();
  const navigate = useNavigate();
  const [edit, setEdit] = useState(false);
  const [stock, setStock] = useState<"receive" | "adjust" | null>(null);
  const part = snapshot.parts.find((p) => p.id === id);
  const txs = useMemo(() => snapshot.stockTransactions.filter((t) => t.partId === id).sort((a, b) => b.at.localeCompare(a.at)), [snapshot.stockTransactions, id]);
  const paged = usePaged(txs, 30);
  if (!part) return <Empty icon="package" title="Part not found" action={<Button onClick={() => navigate("/parts")}>Back to parts</Button>} />;
  const manage = can(user, "part.manage");
  const currency = snapshot.settings.currency;
  const lowStock = part.minStock > 0 && part.stock <= part.minStock;
  const issued90 = txs.filter((t) => t.type === "issue" && Date.now() - new Date(t.at).getTime() < 90 * 86_400_000).reduce((s, t) => s + -t.qty, 0);
  const woNo = (wid: string | null) => (wid ? snapshot.workOrders.find((w) => w.id === wid) : undefined);

  return (
    <div className="stack">
      <Link to="/parts" className="flex small">
        <Icon name="arrow-left" size={14} /> Spare parts
      </Link>
      <PageHeader
        title={
          <span className="flex flex-wrap">
            {part.partNo}
            <Badge tone={part.stock === 0 ? "critical" : lowStock ? "warning" : "good"} dot>
              {part.stock} {part.unit} in stock
            </Badge>
            {!part.active && <Badge>Inactive</Badge>}
          </span>
        }
        subtitle={part.name}
        actions={
          manage && (
            <>
              <Button variant="primary" icon="download" onClick={() => setStock("receive")}>
                Receive stock
              </Button>
              <Button icon="gauge" onClick={() => setStock("adjust")}>
                Adjust count
              </Button>
              <Button icon="edit" onClick={() => setEdit(true)}>
                Edit
              </Button>
            </>
          )
        }
      />
      <div className="grid grid-stats">
        <Stat label="In stock" value={`${part.stock} ${part.unit}`} tone={part.stock === 0 ? "critical" : lowStock ? "warning" : "good"} hint={`min ${part.minStock} · max ${part.maxStock}`} />
        <Stat label="Stock value" value={money(part.stock * part.unitCost, currency)} hint={`${money(part.unitCost, currency)} per ${part.unit}`} />
        <Stat label="Issued, last 90 days" value={`${issued90} ${part.unit}`} />
        <Stat label="Lead time" value={part.leadTimeDays ? `${part.leadTimeDays} d` : "—"} hint={part.supplier || "No supplier"} />
      </div>
      {lowStock && (
        <div className="notice warning">
          <Icon name="alert" size={18} />
          <div>
            Stock is at or below the minimum of {part.minStock} {part.unit}. {part.maxStock > part.stock && `Reorder about ${part.maxStock - part.stock} ${part.unit}`}
            {part.supplier && ` from ${part.supplier}`}.
          </div>
        </div>
      )}
      <div className="grid grid-3">
        <div className="stack span-2">
          <Card title="Stock movements" tight>
            {txs.length === 0 ? (
              <Empty icon="history" title="No movements yet" />
            ) : (
              <>
                <table className="data responsive">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Type</th>
                      <th className="num">Qty</th>
                      <th>Work order</th>
                      <th>By</th>
                      <th>Note</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paged.visible.map((t) => {
                      const wo = woNo(t.workOrderId);
                      return (
                        <tr key={t.id}>
                          <td data-label="Date" className="nowrap">{formatDateTime(t.at)}</td>
                          <td data-label="Type">{t.type}</td>
                          <td data-label="Qty" className="num" style={{ color: t.qty < 0 ? "var(--critical-text)" : "var(--good-text)", fontWeight: 600 }}>
                            {t.qty > 0 ? "+" : ""}
                            {t.qty}
                          </td>
                          <td data-label="Work order">{wo ? <Link to={`/work-orders/${wo.id}`}>{wo.woNo}</Link> : "—"}</td>
                          <td data-label="By">{usersById.get(t.userId)?.name ?? "—"}</td>
                          <td data-label="Note">{t.note}</td>
                        </tr>
                      );
                    })}
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
                { k: "Category", v: part.category || "—" },
                { k: "Location", v: part.location || "—" },
                { k: "Supplier", v: part.supplier || "—" },
                { k: "Unit cost", v: money(part.unitCost, currency) },
                { k: "Lead time", v: part.leadTimeDays ? `${part.leadTimeDays} days` : "—" },
              ]}
            />
            {part.description && <p className="mt-8 small">{part.description}</p>}
          </Card>
          <Card title="Used on" tight>
            {part.assetIds.length === 0 ? (
              <Empty icon="box" title="Not linked to any asset" />
            ) : (
              <ul className="list">
                {part.assetIds.map((aid) => {
                  const a = assetsById.get(aid);
                  return a ? (
                    <li key={aid}>
                      <Link className="row" to={`/assets/${a.id}`}>
                        <div className="grow">
                          <div className="title">{a.assetNo}</div>
                          <div className="meta">{a.name}</div>
                        </div>
                      </Link>
                    </li>
                  ) : null;
                })}
              </ul>
            )}
          </Card>
        </div>
      </div>
      <PartForm open={edit} part={part} onClose={() => setEdit(false)} />
      {stock && <StockModal open partId={part.id} mode={stock} onClose={() => setStock(null)} />}
    </div>
  );
}
