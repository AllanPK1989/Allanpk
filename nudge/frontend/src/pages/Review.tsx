// Weekly review: what got done, what slipped, what's gone quiet, and what's coming.
import { useEffect, useState } from "react";
import { api, errorText, type Review as R } from "../api";
import { DayColumns } from "../components/Charts";
import { TaskList } from "../components/TaskRow";
import { plural, shortDate } from "../format";
import { Icon } from "../icons";
import { useApp } from "../store";
import { Card, Empty, Spinner } from "../ui";

export function Review() {
  const { refreshKey, toast, bump } = useApp();
  const [offset, setOffset] = useState(0);
  const [r, setR] = useState<R | null>(null);
  useEffect(() => {
    api.get<R>(`/api/review?offset=${offset}`).then(setR).catch((e) => toast({ text: errorText(e), kind: "error" }));
  }, [offset, refreshKey, toast]);
  if (!r) return <Spinner />;

  const moveSlipped = async () => {
    try {
      await api.post("/api/tasks-bulk", { ids: r.slipped.map((t) => t.id), action: "tomorrow" });
      bump();
      toast({ text: "Moved to tomorrow" });
    } catch (e) {
      toast({ text: errorText(e), kind: "error" });
    }
  };

  return (
    <div className="page-narrow stack">
      <div className="row">
        <div className="grow">
          <div className="muted small">{shortDate(r.week_start)} – {shortDate(r.week_end)}</div>
          <h1>{offset === 0 ? "This week" : offset === 1 ? "Last week" : `${offset} weeks ago`}</h1>
        </div>
        <div className="seg" role="group" aria-label="Week">
          <button className={offset === 1 ? "on" : ""} onClick={() => setOffset(1)}>Last week</button>
          <button className={offset === 0 ? "on" : ""} onClick={() => setOffset(0)}>This week</button>
        </div>
      </div>

      <div className="card card-pad">
        <div className="row wrap" style={{ gap: 24, alignItems: "flex-end" }}>
          <div><div className="hero">{r.closed_count}</div><div className="muted">closed</div></div>
          <div><div style={{ fontSize: 26, fontWeight: 700 }}>{r.created_count}</div><div className="muted small">added</div></div>
          <div><div style={{ fontSize: 26, fontWeight: 700 }}>{r.dropped_count}</div><div className="muted small">dropped</div></div>
          <div><div style={{ fontSize: 26, fontWeight: 700 }}>{r.open_total}</div><div className="muted small">open now</div></div>
        </div>
        <div className="small muted" style={{ marginTop: 10 }}>
          {r.closed_count >= r.created_count ? "You closed at least as much as you took on. The pile is shrinking." : `You took on ${r.created_count - r.closed_count} more than you closed. Worth dropping or delegating something?`}
        </div>
        <div style={{ marginTop: 14 }}><DayColumns data={r.by_day} /></div>
      </div>

      {r.by_basket.length > 0 && (
        <Card title="Closed by basket">
          <table className="data" style={{ margin: "0 0 8px" }}><tbody>
            {r.by_basket.map((b) => <tr key={b.name}><td style={{ paddingLeft: 16 }}>{b.name}</td><td className="n" style={{ paddingRight: 16 }}>{b.count}</td></tr>)}
          </tbody></table>
        </Card>
      )}

      <Card title={`Slipped · ${r.slipped.length}`} action={r.slipped.length > 1 ? <button className="btn small ghost" onClick={moveSlipped}>Move all to tomorrow</button> : undefined}>
        <TaskList tasks={r.slipped} empty={<Empty icon="done" title="Nothing slipped">Everything due this week was closed or moved.</Empty>} />
      </Card>
      {r.stale.length > 0 && <Card title={`Gone quiet · ${r.stale.length}`}><TaskList tasks={r.stale} /></Card>}
      <Card title="Waiting longest"><TaskList tasks={r.waiting_longest} empty={<Empty icon="hourglass" title="Not waiting on anyone" />} /></Card>
      <Card title="Oldest open"><TaskList tasks={r.oldest} empty={<Empty icon="done" title="Nothing open" />} /></Card>
      {offset === 0 && (
        <div className="card card-pad row"><Icon name="upcoming" />
          <span className="grow">{plural(r.next_week_count, "task")} already scheduled for next week.</span></div>
      )}
      {r.closed.length > 0 && <Card title={`Closed · ${r.closed.length}`}><TaskList tasks={r.closed} /></Card>}
    </div>
  );
}
