// Lists: Inbox, Today, Upcoming, Waiting, Overdue, Done; plus a basket's page and search.
import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { errorText, type Lane, type Task } from "../api";
import { TaskList } from "../components/TaskRow";
import { dayLabel, todayISO } from "../format";
import { Icon } from "../icons";
import { cachedGet } from "../offline";
import { useApp } from "../store";
import { BasketIcon, Card, Empty, Spinner } from "../ui";

const LANES: { key: Lane | "all"; label: string; icon: string }[] = [
  { key: "today", label: "Today", icon: "sun" },
  { key: "overdue", label: "Overdue", icon: "alert" },
  { key: "upcoming", label: "Upcoming", icon: "upcoming" },
  { key: "waiting", label: "Waiting", icon: "hourglass" },
  { key: "inbox", label: "Inbox", icon: "inbox" },
  { key: "done", label: "Done", icon: "done" },
];

const EMPTY: Record<string, [string, string, string]> = {
  today: ["sun", "Nothing due today", "Tasks with today's date and your Top 3 show here."],
  overdue: ["done", "Nothing overdue", "You're on top of things."],
  upcoming: ["upcoming", "Nothing scheduled ahead", "Tasks with a future date show here."],
  waiting: ["hourglass", "Not waiting on anyone", "Say “follow up with …” to track a reply."],
  inbox: ["inbox", "Inbox is clear", "Tasks without a date land here until you schedule them."],
  done: ["done", "Nothing closed yet", "Closed tasks stay here as your record."],
  all: ["search", "No matches", "Try a different word."],
};

function groupUpcoming(tasks: Task[]): { label: string; tasks: Task[] }[] {
  const groups = new Map<string, Task[]>();
  for (const t of tasks) {
    const key = t.due_date ?? "";
    groups.set(key, [...(groups.get(key) ?? []), t]);
  }
  return [...groups.entries()].map(([d, ts]) => ({ label: d ? dayLabel(d) : "No date", tasks: ts }));
}

export function Tasks() {
  const { refreshKey, toast, baskets } = useApp();
  const { basketId } = useParams();
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const lane = (params.get("lane") as Lane | null) ?? (basketId || q ? "all" : "today");
  const person = params.get("person");
  const noBasket = params.get("no_basket") === "1";
  const [tasks, setTasks] = useState<Task[] | null>(null);
  const [stale, setStale] = useState(false);
  const [search, setSearch] = useState(q);
  const basket = basketId ? baskets.find((b) => String(b.id) === basketId) : undefined;

  const path = useMemo(() => {
    const p = new URLSearchParams();
    if (basketId) {
      p.set("basket_id", basketId);
      if (lane !== "all") p.set("lane", lane);
    } else if (q) {
      p.set("lane", "all");
    } else p.set("lane", lane);
    if (q) p.set("q", q);
    if (person) p.set("person", person);
    if (noBasket) p.set("no_basket", "true");
    return `/api/tasks?${p}`;
  }, [basketId, lane, q, person, noBasket]);

  useEffect(() => {
    setTasks(null);
    cachedGet<{ tasks: Task[] }>(path)
      .then((r) => { setTasks(r.data.tasks); setStale(r.stale); })
      .catch((e) => { toast({ text: errorText(e), kind: "error" }); setTasks([]); });
  }, [path, refreshKey, toast]);

  const setLane = (l: string) => {
    const next = new URLSearchParams(params);
    next.set("lane", l);
    next.delete("q");
    setSearch("");
    setParams(next, { replace: true });
  };

  const active = tasks?.filter((t) => t.status === "open" || t.status === "waiting") ?? [];
  const closed = tasks?.filter((t) => t.status === "done" || t.status === "dropped") ?? [];
  const heading = basket ? basket.name : person ? `With ${person}` : noBasket ? "No basket" : q ? `Search: “${q}”` : LANES.find((l) => l.key === lane)?.label ?? "Tasks";

  return (
    <div className="page-narrow stack">
      <div className="row">
        {basket && <BasketIcon basket={basket} />}
        <h1 className="grow">{heading}</h1>
      </div>
      <form className="row" onSubmit={(e) => { e.preventDefault(); const n = new URLSearchParams(params); if (search.trim()) n.set("q", search.trim()); else n.delete("q"); setParams(n); }}>
        <div className="grow" style={{ position: "relative" }}>
          <Icon name="search" size={18} style={{ position: "absolute", left: 12, top: 13, color: "var(--ink-3)" }} />
          <input id="search" className="input" style={{ paddingLeft: 38 }} type="search" placeholder="Search tasks, notes, people" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search" />
        </div>
      </form>
      {!q && (
        <div className="chips" role="tablist" aria-label="Lists">
          {basketId && <button className={`chip ${lane === "all" ? "on" : ""}`} onClick={() => setLane("all")} role="tab" aria-selected={lane === "all"}>All open</button>}
          {LANES.map((l) => (
            <button key={l.key} className={`chip ${lane === l.key ? "on" : ""}`} onClick={() => setLane(l.key)} role="tab" aria-selected={lane === l.key}>
              <Icon name={l.icon} size={16} />{l.label}
            </button>
          ))}
        </div>
      )}
      {stale && <div className="offline"><Icon name="wifioff" size={16} />Offline: showing your last saved list.</div>}
      {tasks === null ? <Spinner /> : (
        <>
          {lane === "upcoming" && !basketId && !q ? (
            groupUpcoming(active).map((g) => (
              <Card key={g.label} title={g.label}><TaskList tasks={g.tasks} /></Card>
            ))
          ) : (
            <Card>
              <TaskList tasks={q ? tasks : lane === "done" ? closed : active}
                empty={<Empty icon={EMPTY[lane]?.[0] ?? "list"} title={EMPTY[lane]?.[1] ?? "Nothing here"}>{EMPTY[lane]?.[2]}</Empty>} />
            </Card>
          )}
          {lane === "upcoming" && !active.length && <Card><Empty icon="upcoming" title={EMPTY.upcoming[1]}>{EMPTY.upcoming[2]}</Empty></Card>}
          {lane === "done" && <div className="tiny muted" style={{ textAlign: "center" }}>Showing your most recent closed tasks. Export everything from <Link to="/settings">Settings</Link>.</div>}
          {lane === "inbox" && active.length > 0 && <div className="tiny muted" style={{ textAlign: "center" }}>Give each a date (⋯ → Pick a date) or drop what you won't do. Today is {dayLabel(todayISO())}.</div>}
        </>
      )}
    </div>
  );
}
