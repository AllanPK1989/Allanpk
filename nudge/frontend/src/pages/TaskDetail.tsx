// One task: edit everything, confirm AI guesses, checklist, follow-up chain, history.
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, errorText, type Task } from "../api";
import { dayLabel, dueText, localDateTime, plural, timeAgo } from "../format";
import { Icon } from "../icons";
import { useApp, useTaskActions } from "../store";
import { Card, Spinner } from "../ui";

const DAY_CODES = ["SU", "MO", "TU", "WE", "TH", "FR", "SA"];
const DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

const EVENT_TEXT: Record<string, string> = {
  created: "Added", edited: "Edited", closed: "Closed", undone: "Close undone", reopened: "Reopened",
  dropped: "Dropped", snoozed: "Snoozed", nudged: "You nudged them", kept: "Kept (still relevant)",
};

export function TaskDetail() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const nav = useNavigate();
  const { baskets, refreshKey, bump, toast, setNudgeFor, setNoteFor, setMenuFor } = useApp();
  const actions = useTaskActions();
  const [t, setT] = useState<Task | null>(null);
  const [newItem, setNewItem] = useState("");

  useEffect(() => {
    api.get<Task>(`/api/tasks/${id}`).then(setT).catch((e) => { toast({ text: errorText(e), kind: "error" }); nav("/"); });
  }, [id, refreshKey, nav, toast]);

  useEffect(() => {
    if (t && params.get("nudge") === "1" && t.status === "waiting") setNudgeFor(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [t?.id]);

  if (!t) return <Spinner />;
  const closed = t.status === "done" || t.status === "dropped";
  const g = (f: string) => (t.ai_fields.includes(f) || (f === "basket_id" && t.ai_fields.includes("basket")) ? "guessed" : "");

  const patch = async (body: Record<string, unknown>) => {
    try {
      setT(await api.patch<Task>(`/api/tasks/${t.id}`, body));
      bump();
    } catch (e) {
      toast({ text: errorText(e), kind: "error" });
    }
  };
  const item = async (method: "post" | "patch" | "del", path: string, body?: unknown) => {
    try {
      const r = method === "post" ? await api.post<Task>(path, body) : method === "patch" ? await api.patch<Task>(path, body) : await api.del<Task>(path);
      setT({ ...t, ...r });
    } catch (e) {
      toast({ text: errorText(e), kind: "error" });
    }
  };
  const remove = async () => {
    if (!window.confirm("Delete this task for good? (Use Drop if you just won't do it.)")) return;
    await api.del(`/api/tasks/${t.id}`);
    bump();
    toast({ text: "Deleted" });
    nav(-1);
  };
  const due = dueText(t);
  const d = t.due_date ? new Date(`${t.due_date}T00:00:00`) : new Date();
  const repeatOpts = [
    ["", "Doesn't repeat"], ["FREQ=DAILY", "Every day"], ["FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR", "Every weekday"],
    [`FREQ=WEEKLY;BYDAY=${DAY_CODES[d.getDay()]}`, `Every ${DAY_NAMES[d.getDay()]}`],
    [`FREQ=MONTHLY;BYMONTHDAY=${d.getDate()}`, `Every month on day ${d.getDate()}`], ["FREQ=YEARLY", "Every year"],
  ];
  if (t.repeat_rule && !repeatOpts.some(([v]) => v === t.repeat_rule)) repeatOpts.splice(1, 0, [t.repeat_rule, t.repeat_label]);

  return (
    <div className="page-narrow stack">
      <div className="row">
        <button className="icon-btn" onClick={() => nav(-1)} aria-label="Back"><Icon name="back" /></button>
        <div className="grow" />
        {!closed && <button className="icon-btn" onClick={() => setMenuFor(t)} aria-label="More actions"><Icon name="more" /></button>}
      </div>

      {t.ai_fields.length > 0 && !closed && (
        <div className="warnbox row" style={{ background: "var(--guess-soft)", color: "var(--guess)" }}>
          <Icon name="sparkle" /><span className="grow">Some details were filled in automatically. Check the highlighted ones.</span>
          <button className="btn small" onClick={() => patch({ confirm_ai: true, inbox: false })}>Looks right</button>
        </div>
      )}

      <div className="card card-pad stack">
        <textarea className={`input ${g("title")}`} defaultValue={t.title} key={`title-${t.updated_at}`} rows={2} aria-label="Title"
          style={{ fontSize: 20, fontWeight: 650, border: 0, padding: 0, minHeight: 0, resize: "none", background: "transparent" }}
          onBlur={(e) => e.target.value.trim() && e.target.value !== t.title && patch({ title: e.target.value.trim() })} />
        <div className="row wrap">
          {closed ? <span className="badge good"><Icon name="done" size={12} />{t.status === "done" ? "Done" : "Dropped"} {t.closed_at && timeAgo(t.closed_at)}</span>
            : due.text && <span className={`badge ${due.tone === "over" ? "critical" : due.tone === "today" ? "warning" : "neutral"}`}><Icon name="calendar" size={12} />{due.text}</span>}
          {t.status === "waiting" && <span className="badge info"><Icon name="hourglass" size={12} />Waiting on {t.person} · {plural(t.waiting_days ?? 0, "day")}</span>}
          {t.focus && <span className="badge warning"><Icon name="star" size={12} />Top 3</span>}
          {t.repeat_label && <span className="badge neutral"><Icon name="repeat" size={12} />{t.repeat_label}</span>}
        </div>

        {!closed ? (
          <div className="row wrap">
            <button className="btn primary" onClick={() => actions.complete(t)}><Icon name="check" />Mark done</button>
            {t.status === "waiting" && <button className="btn" onClick={() => setNudgeFor(t)}><Icon name="send" />Write a nudge</button>}
            {t.status === "waiting" && <button className="btn" onClick={() => patch({ status: "open" })}>They replied, my move</button>}
            <button className="btn" onClick={() => actions.snooze(t, "tomorrow")}><Icon name="calendar" />Tomorrow</button>
          </div>
        ) : (
          <div className="row wrap">
            {t.status === "done" && <button className="btn" onClick={async () => { await api.post(`/api/tasks/${t.id}/undo-close`); bump(); }}><Icon name="undo" />Undo close</button>}
            <button className="btn" onClick={() => actions.reopen(t)}>Reopen</button>
            <button className="btn" onClick={() => setNoteFor(t)}><Icon name="edit" />{t.closing_note ? "Edit closing note" : "Add closing note"}</button>
            <button className="btn" onClick={async () => {
              try { const fu = await api.post<Task>(`/api/tasks/${t.id}/follow-up`, { in_days: 3 }); bump(); nav(`/task/${fu.id}`); }
              catch (e) { toast({ text: errorText(e), kind: "error" }); }
            }}><Icon name="plus" />Follow-up in 3 days</button>
          </div>
        )}
        {t.closing_note && <div className="answer small"><b>Closing note:</b> {t.closing_note}</div>}
      </div>

      <Card title="Details">
        <div className="card-pad fieldgrid" style={{ paddingTop: 4 }}>
          <label className="mini">Basket
            <select className={`input ${g("basket_id")}`} value={t.basket_id ?? ""} onChange={(e) => patch({ basket_id: e.target.value ? Number(e.target.value) : null })}>
              <option value="">No basket</option>
              {baskets.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
            </select>
          </label>
          <label className="mini">Priority
            <select className={`input ${g("priority")}`} value={t.priority} onChange={(e) => patch({ priority: e.target.value })}>
              <option value="high">High</option><option value="normal">Normal</option><option value="low">Low</option>
            </select>
          </label>
          <label className="mini">Date
            <input className={`input ${g("due_date")}`} type="date" value={t.due_date ?? ""} onChange={(e) => patch({ due_date: e.target.value || null })} />
          </label>
          <label className="mini">Time
            <input className={`input ${g("due_time")}`} type="time" value={t.due_time ?? ""} disabled={!t.due_date} onChange={(e) => patch({ due_time: e.target.value || null })} />
          </label>
          <label className="mini">Person
            <input className={`input ${g("person")}`} defaultValue={t.person} key={`p-${t.updated_at}`} placeholder="Who's involved?"
              onBlur={(e) => e.target.value !== t.person && patch({ person: e.target.value })} />
          </label>
          <label className="mini">Repeats
            <select className="input" value={t.repeat_rule} onChange={(e) => patch({ repeat_rule: e.target.value })} disabled={closed}>
              {repeatOpts.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          {t.person && !closed && (
            <label className="row small full" style={{ gap: 10, cursor: "pointer" }}>
              <input type="checkbox" checked={t.status === "waiting"} onChange={(e) => patch({ status: e.target.checked ? "waiting" : "open" })} style={{ width: 20, height: 20 }} />
              I'm waiting on {t.person}
            </label>
          )}
          {t.status === "waiting" && (
            <label className="mini full">Nudge me every
              <select className="input" value={t.nudge_every_days ?? 3} onChange={(e) => patch({ nudge_every_days: Number(e.target.value) })}>
                {[1, 2, 3, 5, 7, 14].map((n) => <option key={n} value={n}>{plural(n, "day")}</option>)}
              </select>
              {t.next_nudge_at && <span className="tiny muted" style={{ fontWeight: 450 }}>Next reminder: {localDateTime(t.next_nudge_at)}{t.nudge_count ? ` · nudged ${plural(t.nudge_count, "time")} so far` : ""}</span>}
            </label>
          )}
          <label className="mini full">Notes
            <textarea className="input" defaultValue={t.notes} key={`n-${t.updated_at}`} placeholder="Anything useful: amounts, part numbers, context"
              onBlur={(e) => e.target.value !== t.notes && patch({ notes: e.target.value })} />
          </label>
        </div>
      </Card>

      <Card title={`Checklist${t.checklist.length ? ` · ${t.checklist.filter((c) => c.done).length}/${t.checklist.length}` : ""}`}>
        <div style={{ padding: "0 16px 12px" }}>
          {t.checklist.map((c) => (
            <div key={c.id} className="row" style={{ minHeight: 44 }}>
              <input type="checkbox" checked={c.done} style={{ width: 20, height: 20 }} aria-label={c.text}
                onChange={(e) => item("patch", `/api/checklist/${c.id}`, { done: e.target.checked })} />
              <span className="grow" style={{ textDecoration: c.done ? "line-through" : undefined, color: c.done ? "var(--ink-3)" : undefined }}>{c.text}</span>
              <button className="icon-btn" aria-label={`Remove ${c.text}`} onClick={() => item("del", `/api/checklist/${c.id}`)}><Icon name="x" size={18} /></button>
            </div>
          ))}
          <form className="row" onSubmit={(e) => { e.preventDefault(); if (newItem.trim()) { item("post", `/api/tasks/${t.id}/checklist`, { text: newItem.trim() }); setNewItem(""); } }}>
            <input className="input" value={newItem} onChange={(e) => setNewItem(e.target.value)} placeholder="Add a step" />
            <button className="btn" type="submit" disabled={!newItem.trim()}>Add</button>
          </form>
        </div>
      </Card>

      {(t.follows || (t.followed_by && t.followed_by.length > 0)) && (
        <Card title="Follow-up chain">
          <div style={{ padding: "0 16px 12px" }} className="stack">
            {t.follows && <Link to={`/task/${t.follows.id}`} className="row"><Icon name="back" size={16} />Follows: {t.follows.title} <span className="tiny muted">({t.follows.status})</span></Link>}
            {t.followed_by?.map((f) => <Link key={f.id} to={`/task/${f.id}`} className="row"><Icon name="arrow" size={16} />Then: {f.title} <span className="tiny muted">({f.status})</span></Link>)}
          </div>
        </Card>
      )}

      {t.transcript && (
        <Card title="What you said"><div className="transcript" style={{ padding: "0 16px 14px" }}>“{t.transcript}”</div></Card>
      )}

      <Card title="History">
        <ul className="timeline" style={{ padding: "0 16px 12px" }}>
          {t.history?.map((h, i) => (
            <li key={i}><span className="grow">{EVENT_TEXT[h.kind] ?? h.kind}
              {h.kind === "snoozed" && typeof h.detail.to === "string" ? ` to ${dayLabel(h.detail.to)}` : ""}</span>
              <span className="tiny">{localDateTime(h.at)}</span></li>
          ))}
        </ul>
      </Card>

      <div className="row" style={{ justifyContent: "center" }}>
        {!closed && <button className="btn ghost danger" onClick={() => actions.drop(t)}>Drop it</button>}
        <button className="btn ghost danger" onClick={remove}><Icon name="trash" size={18} />Delete</button>
      </div>
    </div>
  );
}
