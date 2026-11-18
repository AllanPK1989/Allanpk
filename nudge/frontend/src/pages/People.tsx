// Everyone you have open business with: what you're waiting on, what you owe them.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, errorText, type Person } from "../api";
import { TaskRow } from "../components/TaskRow";
import { initials, plural } from "../format";
import { Icon } from "../icons";
import { useApp } from "../store";
import { Card, Empty, Spinner } from "../ui";

export function People() {
  const { refreshKey, toast, setNudgeFor } = useApp();
  const [people, setPeople] = useState<Person[] | null>(null);
  useEffect(() => {
    api.get<{ people: Person[] }>("/api/people").then((r) => setPeople(r.people)).catch((e) => toast({ text: errorText(e), kind: "error" }));
  }, [refreshKey, toast]);
  if (!people) return <Spinner />;
  return (
    <div className="page-narrow stack">
      <h1>People</h1>
      <div className="muted">Who you're waiting on, and what's still open with each person. Oldest waits first.</div>
      {!people.length && <Card><Empty icon="users" title="No one yet">Mention a name when you add a task (“follow up with Ravi…”) and they'll appear here.</Empty></Card>}
      {people.map((p) => (
        <Card key={p.person} title={
          <span className="row"><span className="avatar">{initials(p.person)}</span>
            <span className="grow">{p.person}<span className="small muted" style={{ display: "block", fontWeight: 450 }}>
              {p.waiting.length ? `Waiting on ${plural(p.waiting.length, "item")} · longest ${p.oldest_waiting_days}d` : "Nothing pending from them"}
              {p.open.length ? ` · ${p.open.length} for you to do` : ""}</span></span></span>}
          action={<Link className="btn small ghost" to={`/tasks?person=${encodeURIComponent(p.person)}&lane=all`}>All</Link>}>
          {p.waiting.map((t) => (
            <div key={t.id}>
              <TaskRow task={t} showBasket={false} />
              <div className="row" style={{ padding: "0 14px 10px 52px" }}>
                <button className="btn small" onClick={() => setNudgeFor(t)}><Icon name="send" size={16} />Write a nudge</button>
              </div>
            </div>
          ))}
          {p.open.map((t) => <TaskRow key={t.id} task={t} showBasket={false} />)}
          {p.recent_done.length > 0 && <div className="tiny muted" style={{ padding: "8px 16px 12px", borderTop: "1px solid var(--line)" }}>
            Recently closed: {p.recent_done.map((t) => t.title).join(" · ")}</div>}
        </Card>
      ))}
    </div>
  );
}
