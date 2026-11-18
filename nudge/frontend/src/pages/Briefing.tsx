// Morning briefing and evening wrap-up, both readable aloud.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, errorText, type Briefing as B, type Wrapup as W } from "../api";
import { TaskList, TaskRow } from "../components/TaskRow";
import { longDate, plural } from "../format";
import { Icon } from "../icons";
import { canSpeak, speak, stopSpeaking } from "../speak";
import { useApp } from "../store";
import { Card, Spinner } from "../ui";

function ReadAloud({ text }: { text: string }) {
  const [on, setOn] = useState(false);
  useEffect(() => () => stopSpeaking(), []);
  if (!canSpeak()) return null;
  return (
    <button className="btn" onClick={() => { if (on) { stopSpeaking(); setOn(false); } else { setOn(true); speak(text, () => setOn(false)); } }}>
      <Icon name={on ? "stop" : "volume"} />{on ? "Stop" : "Read aloud"}
    </button>
  );
}

export function Briefing() {
  const { refreshKey, toast, setNudgeFor } = useApp();
  const [b, setB] = useState<B | null>(null);
  useEffect(() => {
    api.get<B>("/api/briefing").then(setB).catch((e) => toast({ text: errorText(e), kind: "error" }));
  }, [refreshKey, toast]);
  if (!b) return <Spinner />;
  return (
    <div className="page-narrow stack">
      <div>
        <div className="muted small">{longDate(b.date)} · Morning briefing</div>
        <h1>{b.greeting}</h1>
      </div>
      <div className="card card-pad stack">
        <div className="briefing-text">{b.text}</div>
        <div className="row"><ReadAloud text={b.text} /></div>
      </div>
      {b.focus.length > 0 && <Card title="Your Top 3"><TaskList tasks={b.focus} /></Card>}
      {b.overdue.length > 0 && <Card title={`Overdue · ${b.overdue.length}`}><TaskList tasks={b.overdue} /></Card>}
      <Card title={`Due today · ${b.due_today.length}`}><TaskList tasks={b.due_today} empty={<div className="card-pad muted small">Nothing else due today.</div>} /></Card>
      {b.nudges.length > 0 && (
        <Card title={`Follow up today · ${b.nudges.length}`}>
          {b.nudges.map((t) => (
            <div key={t.id}>
              <TaskRow task={t} />
              <div className="row" style={{ padding: "0 14px 10px 52px" }}>
                <button className="btn small" onClick={() => setNudgeFor(t)}><Icon name="send" size={16} />Write a nudge</button>
              </div>
            </div>
          ))}
        </Card>
      )}
      {b.stale.length > 0 && <Card title="Gone quiet: keep, reschedule or drop?"><TaskList tasks={b.stale} /></Card>}
      {b.inbox_count > 0 && <Link className="card card-pad row" to="/tasks?lane=inbox" style={{ color: "inherit" }}><Icon name="inbox" /><span className="grow">{plural(b.inbox_count, "task")} in your Inbox need a date</span><Icon name="chevron" /></Link>}
    </div>
  );
}

export function Wrapup() {
  const { refreshKey, toast, bump } = useApp();
  const [w, setW] = useState<W | null>(null);
  useEffect(() => {
    api.get<W>("/api/wrapup").then(setW).catch((e) => toast({ text: errorText(e), kind: "error" }));
  }, [refreshKey, toast]);
  if (!w) return <Spinner />;
  const moveAll = async () => {
    try {
      await api.post("/api/tasks-bulk", { ids: w.carried.map((t) => t.id), action: "tomorrow" });
      bump();
      toast({ text: `Moved ${plural(w.carried.length, "task")} to tomorrow` });
    } catch (e) {
      toast({ text: errorText(e), kind: "error" });
    }
  };
  return (
    <div className="page-narrow stack">
      <div>
        <div className="muted small">{longDate(w.date)} · Evening wrap-up</div>
        <h1>Your day, wrapped up</h1>
      </div>
      <div className="card card-pad stack">
        <div className="row" style={{ gap: 20, alignItems: "flex-end" }}>
          <div><div className="hero">{w.closed_today.length}</div><div className="muted">closed today</div></div>
          <div><div style={{ fontSize: 26, fontWeight: 700 }}>{w.carried.length}</div><div className="muted small">still open</div></div>
          <div><div style={{ fontSize: 26, fontWeight: 700 }}>{w.due_tomorrow.length}</div><div className="muted small">due tomorrow</div></div>
        </div>
        <div className="briefing-text" style={{ fontSize: 17 }}>{w.text}</div>
        <div className="row wrap"><ReadAloud text={w.text} />
          {w.carried.length > 0 && <button className="btn primary" onClick={moveAll}><Icon name="calendar" />Move {w.carried.length} to tomorrow</button>}
          {w.weekly_review_ready && <Link className="btn" to="/review"><Icon name="chart" />Weekly review</Link>}
        </div>
      </div>
      {w.closed_today.length > 0 && <Card title="Closed today"><TaskList tasks={w.closed_today} /></Card>}
      {w.carried.length > 0 && <Card title="Still open"><TaskList tasks={w.carried} /></Card>}
      {w.due_tomorrow.length > 0 && <Card title="Tomorrow"><TaskList tasks={w.due_tomorrow} /></Card>}
    </div>
  );
}
