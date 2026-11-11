import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { BarRows, GroupedBars } from "../components/charts";
import { Icon } from "../components/icons";
import { Badge, Button, Card, Empty, PlanStateBadge, PriorityBadge, Stat, StatusBadge } from "../components/ui";
import { formatDate, formatDateTime, formatHours, formatMinutes, todayKey } from "../lib/dates";
import { availabilityPct, downtimeByAsset, duePlans, lastNDays, lowStockParts, mtbfHours, mttrHours, openByType, pmCompliance, weeklySeries } from "../lib/kpi";
import { can, canSeeWorkOrder } from "../lib/permissions";
import { planState } from "../lib/pm";
import { isOpenStatus, isOverdue, PRIORITY_RANK } from "../lib/workorders";
import { useCurrentUser, useStore } from "../store/StoreProvider";

export function Dashboard() {
  const { snapshot, assetsById, usersById, linesById } = useStore();
  const user = useCurrentUser();
  const navigate = useNavigate();
  const [days, setDays] = useState(30);
  const today = todayKey();
  const period = lastNDays(days, today);

  const visibleWos = useMemo(() => snapshot.workOrders.filter((w) => canSeeWorkOrder(user, w)), [snapshot.workOrders, user]);
  const open = useMemo(() => visibleWos.filter((w) => isOpenStatus(w.status)), [visibleWos]);
  const counts = openByType(visibleWos);
  const overdue = open.filter((w) => isOverdue(w, today));
  const critical = open.filter((w) => w.priority === "critical");
  const mine = open.filter((w) => w.assignedToUserIds.includes(user.id)).sort((a, b) => PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority]);
  const mttr = mttrHours(visibleWos, period);
  const mtbf = mtbfHours(visibleWos, period, snapshot.settings.plannedHoursPerDay);
  const availability = availabilityPct(visibleWos, period, snapshot.settings.plannedHoursPerDay);
  const compliance = pmCompliance(visibleWos, period);
  const downtime = downtimeByAsset(visibleWos, period, snapshot.assets).slice(0, 6);
  const weekly = weeklySeries(visibleWos, 8, today);
  const low = lowStockParts(snapshot.parts).slice(0, 6);
  const due = duePlans(snapshot.pmPlans, snapshot.assets, today).slice(0, 6);
  const awaitingHandback = visibleWos.filter((w) => w.type === "breakdown" && w.status === "completed" && !w.handbackByUserId);
  const openBreakdowns = open.filter((w) => w.type === "breakdown").sort((a, b) => PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority]);

  const assetLabel = (id: string | null) => {
    const a = id ? assetsById.get(id) : undefined;
    return a ? `${a.assetNo} · ${a.name}` : "—";
  };
  const lineLabel = (id: string | null) => (id ? (linesById.get(id)?.code ?? "") : "");

  const isTech = user.role === "technician";
  const isProd = user.role === "production_supervisor";

  return (
    <div className="stack">
      <div className="flex between flex-wrap">
        <div>
          <h1>{greeting()}, {user.name.split(" ")[0]}</h1>
          <div className="text-2">
            {formatDate(today)} · {snapshot.settings.plantName}
            {isProd && user.lineIds.length > 0 && ` · Lines ${user.lineIds.map((id) => linesById.get(id)?.code).filter(Boolean).join(", ")}`}
          </div>
        </div>
        <div className="flex">
          <select value={days} onChange={(e) => setDays(Number(e.target.value))} aria-label="KPI period" style={{ width: "auto" }}>
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
          {can(user, "wo.request") && (
            <Button variant="primary" icon="zap" onClick={() => navigate("/work-orders?new=breakdown")}>
              Report breakdown
            </Button>
          )}
        </div>
      </div>

      <div className="grid grid-stats">
        <Stat label="Open breakdowns" value={counts.breakdown} tone={counts.breakdown ? "critical" : "good"} hint={critical.length ? `${critical.length} critical` : "No critical breakdowns"} onClick={() => navigate("/work-orders?tab=breakdown&status=open")} />
        <Stat label="Open PM work orders" value={counts.pm} tone={compliance.open ? "warning" : undefined} hint={`${due.length} plan${due.length === 1 ? "" : "s"} due now`} onClick={() => navigate("/work-orders?tab=pm&status=open")} />
        <Stat label="Other open work" value={counts.other} hint={`${overdue.length} overdue in total`} onClick={() => navigate("/work-orders?tab=other&status=open")} />
        <Stat label="PM compliance" value={compliance.pct === null ? "—" : `${Math.round(compliance.pct)}%`} tone={compliance.pct === null ? undefined : compliance.pct >= 90 ? "good" : compliance.pct >= 75 ? "warning" : "critical"} hint={`${compliance.onTime} of ${compliance.due} on time, last ${days} days`} />
        <Stat label="MTTR" value={formatHours(mttr)} hint={`Mean time to repair, last ${days} days`} />
        <Stat label="MTBF" value={mtbf === null ? "—" : `${Math.round(mtbf)} h`} hint={`Mean time between failures, last ${days} days`} />
        <Stat label="Availability" value={availability === null ? "—" : `${availability.toFixed(1)}%`} tone={availability !== null && availability < 95 ? "warning" : "good"} hint={`${snapshot.settings.plannedHoursPerDay} planned h/day`} />
        <Stat label="Parts below minimum" value={lowStockParts(snapshot.parts).length} tone={lowStockParts(snapshot.parts).length ? "warning" : "good"} onClick={() => navigate("/parts?filter=low")} />
      </div>

      {isTech && (
        <Card title="My work orders" actions={<Link to="/work-orders?tab=mine">All mine</Link>} tight>
          <WoList rows={mine.slice(0, 8)} empty="Nothing assigned to you right now. Open work orders are in the Work orders page." />
        </Card>
      )}

      <div className="grid grid-2">
        <Card title="Open breakdowns" actions={<Link to="/work-orders?tab=breakdown&status=open">View all</Link>} tight>
          <WoList rows={openBreakdowns.slice(0, 6)} empty="No machines are down." />
        </Card>
        {isProd ? (
          <Card title="Awaiting your handback" actions={<Link to="/work-orders?tab=breakdown">Breakdowns</Link>} tight>
            <WoList rows={awaitingHandback.slice(0, 6)} empty="No repaired machines waiting for your confirmation." />
          </Card>
        ) : (
          <Card title="PM plans due now" actions={<Link to="/pm">PM schedule</Link>} tight>
            {due.length === 0 ? (
              <Empty icon="check" title="All PM plans are on schedule" />
            ) : (
              <ul className="list">
                {due.map((p) => (
                  <li key={p.id}>
                    <Link className="row" to={`/pm?plan=${p.id}`}>
                      <div className="grow">
                        <div className="title">
                          {p.code} · {p.name}
                        </div>
                        <div className="meta">
                          {assetLabel(p.assetId)} · due {formatDate(p.nextDueAt)}
                        </div>
                      </div>
                      <PlanStateBadge state={planState(p, assetsById.get(p.assetId), today)} />
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        )}
      </div>

      {(can(user, "dashboard.full") || isProd) && (
        <div className="grid grid-2">
          <Card title={`Downtime by asset, last ${days} days`}>
            <BarRows rows={downtime.map((d) => ({ label: d.label, value: d.minutes, hint: `${d.label}: ${formatMinutes(d.minutes)} over ${d.count} breakdown${d.count === 1 ? "" : "s"}` }))} format={formatMinutes} color="var(--series-2)" />
          </Card>
          <Card title="Work orders per week">
            <GroupedBars
              categories={weekly.map((w) => w.label)}
              series={[
                { name: "Created", color: "var(--series-1)", values: weekly.map((w) => w.created) },
                { name: "Completed", color: "var(--series-3)", values: weekly.map((w) => w.completed) },
              ]}
            />
          </Card>
        </div>
      )}

      {can(user, "part.view") && !isProd && (
        <div className="grid grid-2">
          <Card title="Parts below minimum stock" actions={<Link to="/parts?filter=low">Spare parts</Link>} tight>
            {low.length === 0 ? (
              <Empty icon="check" title="Stock levels are fine" />
            ) : (
              <table className="data">
                <thead>
                  <tr>
                    <th>Part</th>
                    <th className="num">Stock</th>
                    <th className="num">Min</th>
                    <th>Supplier</th>
                  </tr>
                </thead>
                <tbody>
                  {low.map((p) => (
                    <tr key={p.id} className="clickable" onClick={() => navigate(`/parts/${p.id}`)}>
                      <td>
                        <div className="primary-cell">{p.partNo}</div>
                        <div className="sub-cell">{p.name}</div>
                      </td>
                      <td className="num">
                        <Badge tone={p.stock === 0 ? "critical" : "warning"}>
                          {p.stock} {p.unit}
                        </Badge>
                      </td>
                      <td className="num">{p.minStock}</td>
                      <td>{p.supplier}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
          <Card title="Recent activity" tight>
            <ul className="list">
              {snapshot.audit.slice(0, 8).map((a) => (
                <li key={a.id}>
                  <Icon name="history" size={16} />
                  <div className="grow">
                    <div>{a.summary}</div>
                    <div className="meta">
                      {a.userId ? (usersById.get(a.userId)?.name ?? "") : "System"} · {formatDateTime(a.at)}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      )}
    </div>
  );

  function WoList({ rows, empty }: { rows: typeof open; empty: string }) {
    if (rows.length === 0) return <Empty icon="check" title={empty} />;
    return (
      <ul className="list">
        {rows.map((w) => (
          <li key={w.id}>
            <Link className="row" to={`/work-orders/${w.id}`}>
              <div className="grow">
                <div className="title">
                  {w.woNo} · {w.title}
                </div>
                <div className="meta">
                  {assetLabel(w.assetId)} {lineLabel(w.lineId) && `· ${lineLabel(w.lineId)}`} · {w.assignedToUserIds.map((id) => usersById.get(id)?.name.split(" ")[0]).filter(Boolean).join(", ") || "Unassigned"}
                  {w.dueDate && ` · due ${formatDate(w.dueDate)}`}
                </div>
              </div>
              <PriorityBadge priority={w.priority} />
              <StatusBadge status={w.status} />
            </Link>
          </li>
        ))}
      </ul>
    );
  }
}

function greeting(): string {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}
