import { useMemo, useState } from "react";
import { BarRows, GroupedBars } from "../components/charts";
import { Button, Card, Empty, PageHeader, Stat, money } from "../components/ui";
import { addDays, formatHours, formatMinutes, todayKey } from "../lib/dates";
import { downloadWorkbook, type Sheet } from "../lib/excel";
import { availabilityPct, breakdownsIn, downtimeByAsset, monthlyPmCompliance, mtbfHours, mttrHours, partsConsumption, pmCompliance, summaryByType, technicianHours, totalDowntimeMinutes, type Period } from "../lib/kpi";
import { can, canSeeWorkOrder } from "../lib/permissions";
import { WO_TYPE_LABEL } from "../lib/workorders";
import { useCurrentUser, useStore } from "../store/StoreProvider";
import { SHIFTS } from "../types";

export function Reports() {
  const { snapshot, linesById } = useStore();
  const user = useCurrentUser();
  const today = todayKey();
  const [preset, setPreset] = useState("90");
  const [from, setFrom] = useState(addDays(today, -89));
  const [to, setTo] = useState(today);
  const period: Period = preset === "custom" ? { from: from || today, to: to || today } : { from: addDays(today, -(Number(preset) - 1)), to: today };
  const wos = useMemo(() => snapshot.workOrders.filter((w) => canSeeWorkOrder(user, w)), [snapshot.workOrders, user]);
  const currency = snapshot.settings.currency;

  const failures = breakdownsIn(wos, period);
  const downtime = totalDowntimeMinutes(failures);
  const mttr = mttrHours(wos, period);
  const mtbf = mtbfHours(wos, period, snapshot.settings.plannedHoursPerDay);
  const availability = availabilityPct(wos, period, snapshot.settings.plannedHoursPerDay);
  const compliance = pmCompliance(wos, period);
  const byAsset = downtimeByAsset(wos, period, snapshot.assets);
  const byCode = useMemo(() => {
    const m = new Map<string, { code: string; count: number; minutes: number }>();
    for (const w of failures) {
      const code = w.failureCode || "Not classified";
      const row = m.get(code) ?? { code, count: 0, minutes: 0 };
      row.count += 1;
      row.minutes += w.downtimeMinutes ?? 0;
      m.set(code, row);
    }
    return [...m.values()].sort((a, b) => b.minutes - a.minutes);
  }, [failures]);
  const byLineShift = useMemo(() => {
    const lines = snapshot.lines.filter((l) => l.active);
    return lines.map((l) => {
      const own = failures.filter((w) => w.lineId === l.id);
      return { line: l, total: own.length, minutes: totalDowntimeMinutes(own), shifts: SHIFTS.map((s) => own.filter((w) => w.shift === s).length) };
    });
  }, [failures, snapshot.lines]);
  const byType = summaryByType(wos, period);
  const months = monthlyPmCompliance(wos, 6, today);
  const techHours = technicianHours(wos, period, snapshot.users);
  const consumption = partsConsumption(snapshot.stockTransactions, period, snapshot.parts);

  const exportAll = () => {
    const sheets: Sheet[] = [
      { name: "KPIs", rows: [{ From: period.from, To: period.to, Breakdowns: failures.length, "Downtime (min)": downtime, "MTTR (h)": mttr ?? "", "MTBF (h)": mtbf ?? "", "Availability %": availability ?? "", "PM due": compliance.due, "PM on time": compliance.onTime, "PM compliance %": compliance.pct ?? "" }] },
      { name: "Downtime by asset", rows: byAsset.map((r) => ({ Asset: r.label, Breakdowns: r.count, "Downtime (min)": r.minutes })) },
      { name: "By failure code", rows: byCode.map((r) => ({ "Failure code": r.code, Breakdowns: r.count, "Downtime (min)": r.minutes })) },
      { name: "By line and shift", rows: byLineShift.map((r) => ({ Line: r.line.code, "Shift A": r.shifts[0], "Shift B": r.shifts[1], "Shift C": r.shifts[2], Total: r.total, "Downtime (min)": r.minutes })) },
      { name: "By type", rows: byType.map((r) => ({ Type: WO_TYPE_LABEL[r.type as keyof typeof WO_TYPE_LABEL] ?? r.type, Created: r.created, Completed: r.completed, "Open now": r.open })) },
      { name: "PM by month", rows: months.map((m) => ({ Month: m.label, Due: m.compliance.due, "On time": m.compliance.onTime, Late: m.compliance.late, Open: m.compliance.open, "Compliance %": m.compliance.pct === null ? "" : Math.round(m.compliance.pct) })) },
      { name: "Technician hours", rows: techHours.map((t) => ({ Technician: t.name, Hours: t.hours, "Work orders": t.workOrders })) },
      { name: "Parts consumption", rows: consumption.map((p) => ({ Part: p.label, Qty: p.qty, Cost: p.cost })) },
    ];
    downloadWorkbook(`CMMS_Eaton-report-${period.from}-to-${period.to}.xlsx`, sheets);
  };

  return (
    <div className="stack">
      <PageHeader
        title="Reports"
        subtitle={`${period.from} to ${period.to}`}
        actions={
          <>
            <select value={preset} onChange={(e) => setPreset(e.target.value)} aria-label="Period">
              <option value="30">Last 30 days</option>
              <option value="90">Last 90 days</option>
              <option value="180">Last 180 days</option>
              <option value="365">Last 365 days</option>
              <option value="custom">Custom range</option>
            </select>
            {preset === "custom" && (
              <>
                <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} aria-label="From" />
                <input type="date" value={to} onChange={(e) => setTo(e.target.value)} aria-label="To" />
              </>
            )}
            {can(user, "data.export") && (
              <Button icon="download" onClick={exportAll}>
                Export to Excel
              </Button>
            )}
          </>
        }
      />
      <div className="grid grid-stats">
        <Stat label="Breakdowns" value={failures.length} />
        <Stat label="Downtime" value={formatMinutes(downtime)} />
        <Stat label="MTTR" value={formatHours(mttr)} />
        <Stat label="MTBF" value={mtbf === null ? "—" : `${Math.round(mtbf)} h`} />
        <Stat label="Availability" value={availability === null ? "—" : `${availability.toFixed(1)}%`} />
        <Stat label="PM compliance" value={compliance.pct === null ? "—" : `${Math.round(compliance.pct)}%`} hint={`${compliance.onTime} of ${compliance.due} on time`} />
      </div>
      <div className="grid grid-2">
        <Card title="Downtime by asset">
          <BarRows rows={byAsset.slice(0, 10).map((r) => ({ label: r.label, value: r.minutes, hint: `${r.count} breakdowns` }))} format={formatMinutes} color="var(--series-2)" />
        </Card>
        <Card title="Breakdowns by failure code" tight>
          {byCode.length === 0 ? (
            <Empty icon="check" title="No breakdowns in this period" />
          ) : (
            <table className="data">
              <thead>
                <tr>
                  <th>Failure code</th>
                  <th className="num">Breakdowns</th>
                  <th className="num">Downtime</th>
                  <th className="num">Avg repair</th>
                </tr>
              </thead>
              <tbody>
                {byCode.map((r) => (
                  <tr key={r.code}>
                    <td>{r.code}</td>
                    <td className="num">{r.count}</td>
                    <td className="num">{formatMinutes(r.minutes)}</td>
                    <td className="num">{formatMinutes(Math.round(r.minutes / r.count))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>
      <div className="grid grid-2">
        <Card title="Breakdowns by line and shift" tight>
          <table className="data">
            <thead>
              <tr>
                <th>Line</th>
                <th className="num">Shift A</th>
                <th className="num">Shift B</th>
                <th className="num">Shift C</th>
                <th className="num">Total</th>
                <th className="num">Downtime</th>
              </tr>
            </thead>
            <tbody>
              {byLineShift.map((r) => (
                <tr key={r.line.id}>
                  <td>
                    {r.line.code} <span className="sub-cell">· runs {r.line.shifts.join(", ")}</span>
                  </td>
                  {r.shifts.map((n, i) => (
                    <td key={i} className="num" style={!r.line.shifts.includes(SHIFTS[i]) ? { color: "var(--muted)" } : undefined}>
                      {n}
                    </td>
                  ))}
                  <td className="num">{r.total}</td>
                  <td className="num">{formatMinutes(r.minutes)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
        <Card title="Work orders by type" tight>
          <table className="data">
            <thead>
              <tr>
                <th>Type</th>
                <th className="num">Created</th>
                <th className="num">Completed</th>
                <th className="num">Open now</th>
              </tr>
            </thead>
            <tbody>
              {byType.map((r) => (
                <tr key={r.type}>
                  <td>{WO_TYPE_LABEL[r.type as keyof typeof WO_TYPE_LABEL] ?? r.type}</td>
                  <td className="num">{r.created}</td>
                  <td className="num">{r.completed}</td>
                  <td className="num">{r.open}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
      <Card title="PM compliance by month">
        <GroupedBars
          categories={months.map((m) => m.label)}
          series={[
            { name: "On time", color: "var(--series-3)", values: months.map((m) => m.compliance.onTime) },
            { name: "Late or still open", color: "var(--series-2)", values: months.map((m) => m.compliance.late + m.compliance.open) },
          ]}
          height={180}
        />
        <div className="small muted mt-8">{months.map((m) => `${m.label}: ${m.compliance.pct === null ? "no PM due" : `${Math.round(m.compliance.pct)}%`}`).join(" · ")}</div>
      </Card>
      <div className="grid grid-2">
        <Card title="Technician hours" tight>
          {techHours.length === 0 ? (
            <Empty icon="clock" title="No labour logged in this period" />
          ) : (
            <table className="data">
              <thead>
                <tr>
                  <th>Technician</th>
                  <th className="num">Hours</th>
                  <th className="num">Work orders</th>
                </tr>
              </thead>
              <tbody>
                {techHours.map((t) => (
                  <tr key={t.userId}>
                    <td>{t.name}</td>
                    <td className="num">{t.hours.toFixed(1)}</td>
                    <td className="num">{t.workOrders}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
        <Card title="Parts consumption" tight>
          {consumption.length === 0 ? (
            <Empty icon="package" title="No parts issued in this period" />
          ) : (
            <table className="data">
              <thead>
                <tr>
                  <th>Part</th>
                  <th className="num">Qty</th>
                  <th className="num">Cost</th>
                </tr>
              </thead>
              <tbody>
                {consumption.slice(0, 15).map((p) => (
                  <tr key={p.partId}>
                    <td>{p.label}</td>
                    <td className="num">{p.qty}</td>
                    <td className="num">{money(p.cost, currency)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>
      <p className="small muted">
        MTBF uses {snapshot.settings.plannedHoursPerDay} planned hours per day plant-wide; per-asset MTBF on each asset page uses that line's shifts
        {snapshot.lines.filter((l) => l.shifts.includes("C")).length > 0 && ` (${snapshot.lines.filter((l) => l.shifts.includes("C")).map((l) => linesById.get(l.id)?.code).join(", ")} run shift C)`}.
      </p>
    </div>
  );
}
