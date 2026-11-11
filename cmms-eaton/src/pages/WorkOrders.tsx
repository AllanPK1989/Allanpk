import { useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Button, Card, Empty, PageHeader, PriorityBadge, Search, StatusBadge, Tabs, usePaged } from "../components/ui";
import { WorkOrderForm } from "../components/WorkOrderForm";
import { formatDate, formatDateTime, formatMinutes, todayKey } from "../lib/dates";
import { can, canSeeWorkOrder } from "../lib/permissions";
import { isOpenStatus, isOtherType, isOverdue, PRIORITIES, PRIORITY_LABEL, PRIORITY_RANK, WO_STATUS_LABEL, WO_STATUSES, WO_TYPE_LABEL } from "../lib/workorders";
import { useCurrentUser, useStore } from "../store/StoreProvider";
import type { WOType } from "../types";

type Tab = "all" | "breakdown" | "pm" | "other" | "mine";

export function WorkOrders() {
  const { snapshot, assetsById, usersById, linesById } = useStore();
  const user = useCurrentUser();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const tab = (params.get("tab") as Tab) || "all";
  const status = params.get("status") || "open";
  const priority = params.get("priority") || "";
  const lineId = params.get("line") || "";
  const assignee = params.get("assignee") || "";
  const q = params.get("q") || "";
  const newType = params.get("new") as WOType | null;
  const [formOpen, setFormOpen] = useState(Boolean(newType));
  const today = todayKey();

  const setParam = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    next.delete("new");
    setParams(next, { replace: true });
  };

  const visible = useMemo(() => snapshot.workOrders.filter((w) => canSeeWorkOrder(user, w)), [snapshot.workOrders, user]);
  const counts = useMemo(
    () => ({
      all: visible.filter((w) => isOpenStatus(w.status)).length,
      breakdown: visible.filter((w) => w.type === "breakdown" && isOpenStatus(w.status)).length,
      pm: visible.filter((w) => w.type === "pm" && isOpenStatus(w.status)).length,
      other: visible.filter((w) => isOtherType(w.type) && isOpenStatus(w.status)).length,
      mine: visible.filter((w) => w.assignedToUserIds.includes(user.id) && isOpenStatus(w.status)).length,
    }),
    [visible, user.id],
  );

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return visible
      .filter((w) => {
        if (tab === "breakdown" && w.type !== "breakdown") return false;
        if (tab === "pm" && w.type !== "pm") return false;
        if (tab === "other" && !isOtherType(w.type)) return false;
        if (tab === "mine" && !w.assignedToUserIds.includes(user.id)) return false;
        if (status === "open" && !isOpenStatus(w.status)) return false;
        if (status === "overdue" && !isOverdue(w, today)) return false;
        if (status !== "open" && status !== "all" && status !== "overdue" && w.status !== status) return false;
        if (priority && w.priority !== priority) return false;
        if (lineId && w.lineId !== lineId) return false;
        if (assignee === "none" && w.assignedToUserIds.length > 0) return false;
        if (assignee && assignee !== "none" && !w.assignedToUserIds.includes(assignee)) return false;
        if (needle) {
          const asset = w.assetId ? assetsById.get(w.assetId) : undefined;
          const hay = `${w.woNo} ${w.title} ${w.description} ${asset?.assetNo ?? ""} ${asset?.name ?? ""} ${w.rootCause} ${w.actionTaken}`.toLowerCase();
          if (!hay.includes(needle)) return false;
        }
        return true;
      })
      .sort((a, b) => {
        const ao = isOpenStatus(a.status) ? 0 : 1;
        const bo = isOpenStatus(b.status) ? 0 : 1;
        if (ao !== bo) return ao - bo;
        if (ao === 0 && PRIORITY_RANK[a.priority] !== PRIORITY_RANK[b.priority]) return PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority];
        return b.createdAt.localeCompare(a.createdAt);
      });
  }, [visible, tab, status, priority, lineId, assignee, q, user.id, assetsById, today]);

  const paged = usePaged(rows, 50);
  const technicians = snapshot.users.filter((u) => u.active && (u.role === "technician" || u.role === "maintenance_supervisor"));

  const closeForm = () => {
    setFormOpen(false);
    if (newType) setParam("new", "");
  };

  return (
    <div>
      <PageHeader
        title="Work orders"
        subtitle={`${counts.all} open · ${visible.length} in total`}
        actions={
          <>
            {can(user, "wo.request") && (
              <Button variant="primary" icon="zap" onClick={() => { setParam("new", "breakdown"); setFormOpen(true); }}>
                Report breakdown
              </Button>
            )}
            {can(user, "wo.request") && (
              <Button icon="plus" onClick={() => { setParam("new", "other"); setFormOpen(true); }}>
                New work order
              </Button>
            )}
          </>
        }
      />
      <Tabs<Tab>
        tabs={[
          { id: "all", label: "All", count: counts.all },
          { id: "breakdown", label: "Breakdowns", count: counts.breakdown },
          { id: "pm", label: "Preventive", count: counts.pm },
          { id: "other", label: "Other work", count: counts.other },
          ...(can(user, "wo.execute") ? [{ id: "mine" as Tab, label: "Mine", count: counts.mine }] : []),
        ]}
        active={tab}
        onChange={(t) => setParam("tab", t === "all" ? "" : t)}
      />
      <div className="filters">
        <Search value={q} onChange={(v) => setParam("q", v)} placeholder="Search WO no, title, asset, cause" />
        <select value={status} onChange={(e) => setParam("status", e.target.value)} aria-label="Status">
          <option value="open">Open (any status)</option>
          <option value="overdue">Overdue</option>
          <option value="all">All statuses</option>
          {WO_STATUSES.map((s) => (
            <option key={s} value={s}>
              {WO_STATUS_LABEL[s]}
            </option>
          ))}
        </select>
        <select value={priority} onChange={(e) => setParam("priority", e.target.value)} aria-label="Priority">
          <option value="">Any priority</option>
          {PRIORITIES.map((p) => (
            <option key={p} value={p}>
              {PRIORITY_LABEL[p]}
            </option>
          ))}
        </select>
        <select value={lineId} onChange={(e) => setParam("line", e.target.value)} aria-label="Line">
          <option value="">Any line</option>
          {snapshot.lines.filter((l) => l.active).map((l) => (
            <option key={l.id} value={l.id}>
              {l.code} · {l.name}
            </option>
          ))}
        </select>
        <select value={assignee} onChange={(e) => setParam("assignee", e.target.value)} aria-label="Assigned to">
          <option value="">Anyone</option>
          <option value="none">Unassigned</option>
          {technicians.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
      </div>
      <Card tight>
        {rows.length === 0 ? (
          <Empty icon="wrench" title="No work orders match" text="Change the filters, or create a new work order." />
        ) : (
          <>
            <div className="table-wrap">
              <table className="data responsive">
                <thead>
                  <tr>
                    <th>Work order</th>
                    <th>Asset</th>
                    <th>Type</th>
                    <th>Priority</th>
                    <th>Status</th>
                    <th>Assigned</th>
                    <th>Due / downtime</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {paged.visible.map((w) => {
                    const asset = w.assetId ? assetsById.get(w.assetId) : undefined;
                    const overdue = isOverdue(w, today);
                    return (
                      <tr key={w.id} className="clickable" onClick={() => navigate(`/work-orders/${w.id}`)}>
                        <td data-label="Work order">
                          <div className="primary-cell">{w.woNo}</div>
                          <div className="sub-cell">{w.title}</div>
                        </td>
                        <td data-label="Asset">
                          {asset ? (
                            <>
                              <div>{asset.assetNo}</div>
                              <div className="sub-cell">
                                {asset.name}
                                {w.lineId && ` · ${linesById.get(w.lineId)?.code ?? ""}`}
                              </div>
                            </>
                          ) : (
                            <span className="muted">—</span>
                          )}
                        </td>
                        <td data-label="Type">{WO_TYPE_LABEL[w.type]}</td>
                        <td data-label="Priority">
                          <PriorityBadge priority={w.priority} />
                        </td>
                        <td data-label="Status">
                          <StatusBadge status={w.status} />
                        </td>
                        <td data-label="Assigned">{w.assignedToUserIds.map((id) => usersById.get(id)?.name).filter(Boolean).join(", ") || <span className="muted">Unassigned</span>}</td>
                        <td data-label="Due / downtime">
                          {w.type === "breakdown" ? (
                            w.downtimeMinutes !== null ? (
                              formatMinutes(w.downtimeMinutes)
                            ) : w.downtimeStart ? (
                              <span className="badge critical">down {formatMinutes(Math.round((Date.now() - new Date(w.downtimeStart).getTime()) / 60_000))}</span>
                            ) : (
                              "—"
                            )
                          ) : (
                            <span style={overdue ? { color: "var(--critical-text)", fontWeight: 600 } : undefined}>{formatDate(w.dueDate)}</span>
                          )}
                        </td>
                        <td data-label="Created" className="nowrap">
                          {formatDateTime(w.createdAt)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="table-foot">
              <span>
                Showing {paged.visible.length} of {paged.total}
              </span>
              {paged.more && (
                <Button size="sm" onClick={paged.showMore}>
                  Show more
                </Button>
              )}
            </div>
          </>
        )}
      </Card>
      <WorkOrderForm open={formOpen} onClose={closeForm} initialType={newType === "other" ? "corrective" : (newType ?? "breakdown")} onCreated={(id) => navigate(`/work-orders/${id}`)} />
    </div>
  );
}
