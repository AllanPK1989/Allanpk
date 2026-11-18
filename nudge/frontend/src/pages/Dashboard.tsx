import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, errorText, type Dashboard as D, type ShortTask } from "../api";
import { AgingBars, TrendChart } from "../components/Charts";
import { TaskList, TaskRow } from "../components/TaskRow";
import { initials, longDate, plural } from "../format";
import { Icon } from "../icons";
import { cachedGet } from "../offline";
import { setBadge } from "../push";
import { useApp, useTaskActions } from "../store";
import { BasketIcon, Card, colorVar, Empty, Sheet, Spinner } from "../ui";

function Kpi({ tone, icon, label, value, to, hot }: { tone: string; icon: string; label: string; value: number; to: string; hot?: boolean }) {
  const nav = useNavigate();
  return (
    <button className={`kpi ${tone} ${hot ? "hot" : ""}`} onClick={() => nav(to)} aria-label={`${label}: ${value}`}>
      <span className="kpi-top"><span className="kpi-ic"><Icon name={icon} size={17} /></span>{label}</span>
      <span className="kpi-val">{value}</span>
    </button>
  );
}

function FocusCard({ data }: { data: D }) {
  const [picking, setPicking] = useState(false);
  const actions = useTaskActions();
  const candidates = data.today_list.filter((t) => !t.focus);
  return (
    <Card title={<span className="row"><Icon name="star" size={18} style={{ color: "var(--c-amber)", fill: "currentColor" }} />Today's Top 3</span>}
      action={data.focus.length < 3 && candidates.length > 0 ? <button className="btn small ghost" onClick={() => setPicking(true)}><Icon name="plus" size={16} />Pick</button> : undefined}>
      {data.focus.length ? <TaskList tasks={data.focus} /> : (
        <div className="card-pad muted small" style={{ paddingTop: 4 }}>
          Pick up to three things that would make today a good day.{" "}
          {candidates.length > 0 && <button className="btn small" style={{ marginTop: 8 }} onClick={() => setPicking(true)}>Choose from today</button>}
        </div>
      )}
      {picking && (
        <Sheet title="Pick for your Top 3" onClose={() => setPicking(false)}>
          <div className="menu">
            {candidates.map((t) => (
              <button key={t.id} onClick={async () => { await actions.focus(t, true); setPicking(false); }}>
                <Icon name="star" />{t.title}
              </button>
            ))}
          </div>
        </Sheet>
      )}
    </Card>
  );
}

function TodayCard({ data }: { data: D }) {
  const { bump, toast } = useApp();
  const rest = data.today_list.filter((t) => !t.focus); // Top 3 is shown just above
  const overdue = rest.filter((t) => t.overdue);
  const moveAll = async () => {
    try {
      const r = await api.post<{ changed: number }>("/api/tasks-bulk", { ids: overdue.map((t) => t.id), action: "tomorrow" });
      bump();
      toast({ text: `Moved ${plural(r.changed, "task")} to tomorrow` });
    } catch (e) {
      toast({ text: errorText(e), kind: "error" });
    }
  };
  return (
    <Card title={data.focus.length ? `Rest of today · ${rest.length}` : `Today · ${rest.length}`}
      action={overdue.length > 1 ? <button className="btn small ghost" onClick={moveAll}><Icon name="calendar" size={16} />Move {overdue.length} overdue to tomorrow</button> : <Link className="btn small ghost" to="/tasks?lane=today">See all</Link>}>
      <TaskList tasks={rest.slice(0, 12)} empty={<Empty icon="sun" title={data.focus.length ? "Nothing else due today" : "Nothing due today"}>Enjoy the breathing room, or pull something forward.</Empty>} />
      {rest.length > 12 && <Link className="btn ghost block" to="/tasks?lane=today">Show {rest.length - 12} more</Link>}
    </Card>
  );
}

function Baskets({ data }: { data: D }) {
  const nav = useNavigate();
  return (
    <div className="baskets">
      {data.baskets.map((b) => (
        <button key={b.basket.id ?? "none"} className="btile" onClick={() => nav(b.basket.id ? `/basket/${b.basket.id}` : "/tasks?no_basket=1")}
          aria-label={`${b.basket.name}: ${b.open} open${b.overdue ? `, ${b.overdue} overdue` : ""}`}>
          <div className="row"><BasketIcon basket={b.basket} size={32} />
            {b.overdue > 0 && <span className="badge critical" style={{ marginLeft: "auto" }}><Icon name="alert" size={12} />{b.overdue} overdue</span>}
          </div>
          <div className="bname">{b.basket.name}</div>
          <div className="row" style={{ alignItems: "baseline", gap: 6 }}>
            <span className="bnum">{b.open}</span><span className="small muted">open</span>
            {b.waiting > 0 && <span className="small muted">· {b.waiting} waiting</span>}
          </div>
          <div className="meter" aria-hidden="true"><i style={{ width: `${b.cleared_pct}%`, background: colorVar(b.basket.color) }} /></div>
          <div className="tiny muted">
            {b.cleared_30} cleared in 30 days{b.open > 0 ? ` · oldest ${b.oldest_days}d` : ""}
          </div>
        </button>
      ))}
    </div>
  );
}

function Radar({ data }: { data: D }) {
  const { setNudgeFor } = useApp();
  const [open, setOpen] = useState<string | null>(null);
  if (!data.radar.length) return <Empty icon="hourglass" title="You're not waiting on anyone">Tasks where someone owes you a reply show up here.</Empty>;
  return (
    <div>
      {data.radar.map((g) => (
        <div key={g.person}>
          <button className="person" onClick={() => setOpen(open === g.person ? null : g.person)} aria-expanded={open === g.person}>
            <span className="avatar">{initials(g.person)}</span>
            <span className="grow">
              <span style={{ fontWeight: 600, display: "block" }}>{g.person}</span>
              <span className="small muted">{plural(g.count, "item")} pending</span>
            </span>
            <span className={`badge ${g.oldest_days >= 7 ? "critical" : g.oldest_days >= 3 ? "warning" : "neutral"}`}>
              <Icon name="hourglass" size={12} />{g.oldest_days}d
            </span>
          </button>
          {open === g.person && (
            <div style={{ background: "var(--surface-2)" }}>
              {g.items.map((t) => (
                <div key={t.id}>
                  <TaskRow task={t} />
                  <div className="row" style={{ padding: "0 14px 10px 52px", background: "var(--surface)" }}>
                    <button className="btn small" onClick={() => setNudgeFor(t)}><Icon name="send" size={16} />Write a nudge</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function Stale({ tasks, count }: { tasks: ShortTask[]; count: number }) {
  const actions = useTaskActions();
  const { setMenuFor } = useApp();
  return (
    <Card title={`Needs a decision · ${count}`} action={<span className="tiny muted">No activity for a while</span>}>
      {tasks.map((t) => (
        <div key={t.id} style={{ borderTop: "1px solid var(--line)", padding: "10px 16px" }}>
          <Link to={`/task/${t.id}`} style={{ color: "var(--ink)", fontWeight: 550 }}>{t.title}</Link>
          <div className="tiny muted" style={{ margin: "2px 0 8px" }}>Added {plural(t.age_days, "day")} ago{t.basket ? ` · ${t.basket.name}` : ""}</div>
          <div className="row wrap">
            <button className="btn small" onClick={() => actions.keep(t)}>Still relevant</button>
            <button className="btn small" onClick={() => setMenuFor(t)}><Icon name="calendar" size={16} />Reschedule</button>
            <button className="btn small danger" onClick={() => actions.drop(t)}>Drop it</button>
          </div>
        </div>
      ))}
    </Card>
  );
}

export function Dashboard() {
  const { refreshKey, toast, openCapture } = useApp();
  const nav = useNavigate();
  const [data, setData] = useState<D | null>(null);
  const [stale, setStale] = useState(false);

  useEffect(() => {
    cachedGet<D>("/api/dashboard")
      .then((r) => { setData(r.data); setStale(r.stale); setBadge(r.data.kpis.overdue + r.data.kpis.due_today); })
      .catch((e) => toast({ text: errorText(e), kind: "error" }));
  }, [refreshKey, toast]);

  if (!data) return <Spinner />;
  const k = data.kpis;
  return (
    <div className="page stack">
      <div className="row wrap" style={{ alignItems: "flex-end", gap: 12 }}>
        <div style={{ flex: "1 1 260px", minWidth: 0 }}>
          <div className="muted small">{longDate(data.today)}</div>
          <h1>{data.greeting}</h1>
        </div>
        <Link className="btn small" to="/briefing"><Icon name="sun" size={16} />Morning briefing</Link>
        <Link className="btn small" to="/wrapup"><Icon name="sunset" size={16} />Wrap-up</Link>
      </div>
      {stale && <div className="offline"><Icon name="wifioff" size={16} />Offline: showing your last saved dashboard.</div>}

      <div className="kpis">
        <Kpi tone="critical" icon="alert" label="Overdue" value={k.overdue} to="/tasks?lane=overdue" hot={k.overdue > 0} />
        <Kpi tone="warning" icon="clock" label="Due today" value={k.due_today} to="/tasks?lane=today" />
        <Kpi tone="info" icon="hourglass" label="Waiting on others" value={k.waiting} to="/tasks?lane=waiting" />
        <Kpi tone="good" icon="done" label="Closed this week" value={k.closed_week} to="/tasks?lane=done" />
      </div>

      {data.open_total === 0 && (
        <Card><Empty icon="mic" title="Nothing on your plate yet">
          <button className="btn primary" style={{ marginTop: 10 }} onClick={() => openCapture("voice", true)}><Icon name="mic" />Say what's on your mind</button>
        </Empty></Card>
      )}

      <div className="grid-dash">
        <div className="span-7 stack">
          <FocusCard data={data} />
          <TodayCard data={data} />
          {data.lanes.inbox > 0 && (
            <button className="card card-pad row" style={{ textAlign: "left", cursor: "pointer", color: "inherit" }} onClick={() => nav("/tasks?lane=inbox")}>
              <Icon name="inbox" /><span className="grow"><b>{plural(data.lanes.inbox, "task")}</b> in your Inbox without a date</span>
              <span className="small" style={{ color: "var(--accent-ink)", fontWeight: 650 }}>Sort them</span><Icon name="chevron" size={18} />
            </button>
          )}
        </div>
        <div className="span-5 stack">
          <Card title={`Follow-up radar · ${data.kpis.waiting}`} action={<Link className="btn small ghost" to="/people">People</Link>}>
            <Radar data={data} />
          </Card>
          {data.stale.length > 0 && <Stale tasks={data.stale} count={data.stale_count} />}
        </div>

        <div className="span-12 stack">
          <div className="row"><h2 className="grow">Baskets</h2><Link className="btn small ghost" to="/settings#baskets">Edit baskets</Link></div>
          <Baskets data={data} />
        </div>

        <div className="span-6">
          <Card title="Backlog aging"><div className="card-pad" style={{ paddingTop: 4 }}>
            <AgingBars data={data.aging} />
          </div></Card>
        </div>
        <div className="span-6">
          <Card title="Added vs closed, by week" action={<Link className="btn small ghost" to="/review">Weekly review</Link>}>
            <div className="card-pad" style={{ paddingTop: 4 }}><TrendChart data={data.trend} /></div>
          </Card>
        </div>
      </div>
    </div>
  );
}
