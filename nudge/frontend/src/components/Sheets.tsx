// App-level sheets: the task action menu, the closing note, and the follow-up message writer.
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, errorText, type Task } from "../api";
import { addDays, todayISO } from "../format";
import { Icon } from "../icons";
import { useRecorder } from "../recorder";
import { useApp, useTaskActions } from "../store";
import { BasketDot, Sheet, Spinner } from "../ui";

export function TaskMenu() {
  const { menuFor: t, setMenuFor, baskets, bump, toast, setNudgeFor } = useApp();
  const actions = useTaskActions();
  const nav = useNavigate();
  const [pickDate, setPickDate] = useState(false);
  const [moving, setMoving] = useState(false);
  if (!t) return null;
  const close = () => { setMenuFor(null); setPickDate(false); setMoving(false); };
  const doThen = (fn: () => void) => () => { close(); fn(); };

  const move = async (basketId: number) => {
    close();
    try {
      await api.patch(`/api/tasks/${t.id}`, { basket_id: basketId });
      bump();
      toast({ text: "Moved" });
    } catch (e) {
      toast({ text: errorText(e), kind: "error" });
    }
  };

  return (
    <Sheet title={t.title} onClose={close}>
      {pickDate ? (
        <div className="stack">
          <input className="input" type="date" min={todayISO()} defaultValue={addDays(todayISO(), 1)} id="snooze-date" />
          <button className="btn primary block" onClick={() => {
            const v = (document.getElementById("snooze-date") as HTMLInputElement).value;
            if (v) { close(); actions.snooze(t, "date", v); }
          }}>Move to this date</button>
        </div>
      ) : moving ? (
        <div className="menu">
          {baskets.map((b) => (
            <button key={b.id} onClick={() => move(b.id)}><BasketDot basket={b} />{b.name}{b.id === t.basket?.id && <span className="muted small">(current)</span>}</button>
          ))}
        </div>
      ) : (
        <div className="menu">
          <button onClick={doThen(() => actions.complete(t))}><Icon name="check" />Mark done</button>
          <div className="sep" />
          <button onClick={doThen(() => actions.snooze(t, "1h"))}><Icon name="clock" />Remind me in an hour</button>
          <button onClick={doThen(() => actions.snooze(t, "tonight"))}><Icon name="moon" />Remind me tonight</button>
          <button onClick={doThen(() => actions.snooze(t, "tomorrow"))}><Icon name="calendar" />Move to tomorrow</button>
          <button onClick={doThen(() => actions.snooze(t, "next_week"))}><Icon name="upcoming" />Move to next week</button>
          <button onClick={() => setPickDate(true)}><Icon name="calendar" />Pick a date…</button>
          <div className="sep" />
          <button onClick={doThen(() => actions.focus(t, !t.focus))}><Icon name="star" />{t.focus ? "Remove from Top 3" : "Add to today's Top 3"}</button>
          {t.status === "waiting" && <button onClick={doThen(() => setNudgeFor(t))}><Icon name="send" />Write a follow-up message</button>}
          {t.status === "waiting" && <button onClick={doThen(() => actions.nudged(t))}><Icon name="check" />I've nudged them</button>}
          <button onClick={() => setMoving(true)}><Icon name="layers" />Move to another basket</button>
          <button onClick={doThen(() => nav(`/task/${t.id}`))}><Icon name="edit" />Open and edit</button>
          <div className="sep" />
          <button onClick={doThen(() => actions.drop(t))} style={{ color: "var(--critical-ink)" }}><Icon name="trash" />Drop it (no longer needed)</button>
        </div>
      )}
    </Sheet>
  );
}

export function NoteSheet() {
  const { noteFor: t, setNoteFor, bump, toast } = useApp();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const rec = useRecorder(async (blob) => {
    setBusy(true);
    try {
      const form = new FormData();
      form.append("audio", blob, `note.${blob.type.includes("mp4") ? "m4a" : "webm"}`);
      const r = await api.upload<{ text: string }>("/api/assistant/transcribe", form);
      setText((cur) => (cur ? `${cur} ${r.text}` : r.text));
    } catch (e) {
      toast({ text: errorText(e), kind: "error" });
    } finally {
      setBusy(false);
    }
  });
  useEffect(() => setText((t as Task | null)?.closing_note ?? ""), [t]);
  if (!t) return null;
  const save = async () => {
    try {
      await api.post(`/api/tasks/${t.id}/closing-note`, { note: text });
      bump();
      toast({ text: "Note saved" });
      setNoteFor(null);
    } catch (e) {
      toast({ text: errorText(e), kind: "error" });
    }
  };
  return (
    <Sheet title="How did it go?" onClose={() => setNoteFor(null)}>
      <div className="stack">
        <div className="muted small">{t.title}</div>
        <textarea className="input" value={text} onChange={(e) => setText(e.target.value)} placeholder="Outcome, decision, amount, who said what…" autoFocus />
        <div className="row">
          <button className={`btn ${rec.state === "recording" ? "danger" : ""}`} onClick={rec.state === "recording" ? rec.stop : rec.start} disabled={busy}>
            <Icon name={rec.state === "recording" ? "stop" : "mic"} />{rec.state === "recording" ? `Stop (${rec.seconds}s)` : busy ? "Writing it down…" : "Say it"}
          </button>
          <div className="grow" />
          <button className="btn primary" onClick={save}>Save note</button>
        </div>
      </div>
    </Sheet>
  );
}

export function NudgeSheet() {
  const { nudgeFor: t, setNudgeFor, toast } = useApp();
  const actions = useTaskActions();
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!t) return;
    setLoading(true);
    api.get<{ message: string }>(`/api/tasks/${t.id}/nudge-draft`)
      .then((r) => setMsg(r.message))
      .catch((e) => toast({ text: errorText(e), kind: "error" }))
      .finally(() => setLoading(false));
  }, [t, toast]);
  if (!t) return null;
  const close = () => setNudgeFor(null);
  const sent = () => { close(); actions.nudged(t); };
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(msg);
      toast({ text: "Copied. Paste it in WhatsApp or e-mail." });
    } catch {
      toast({ text: "Couldn't copy. Select the text and copy it.", kind: "error" });
    }
  };
  const share = async () => {
    try {
      await navigator.share({ text: msg });
      sent();
    } catch {
      /* cancelled */
    }
  };
  const canShare = typeof navigator.share === "function";
  return (
    <Sheet title={`Follow up with ${t.person || "them"}`} onClose={close}>
      {loading ? <Spinner label="Writing" /> : (
        <div className="stack">
          <textarea className="input" style={{ minHeight: 150 }} value={msg} onChange={(e) => setMsg(e.target.value)} aria-label="Message" />
          <div className="tiny muted">A ready-made message. Edit anything before sending.</div>
          <div className="row wrap">
            {canShare && <button className="btn primary" onClick={share}><Icon name="share" />Share…</button>}
            <a className="btn" href={`https://wa.me/?text=${encodeURIComponent(msg)}`} target="_blank" rel="noreferrer" onClick={sent}><Icon name="send" />WhatsApp</a>
            <a className="btn" href={`mailto:?subject=${encodeURIComponent(t.title)}&body=${encodeURIComponent(msg)}`} onClick={sent}><Icon name="mail" />E-mail</a>
            <button className="btn" onClick={copy}><Icon name="copy" />Copy</button>
          </div>
          <button className="btn ghost" onClick={sent}><Icon name="check" />I've sent it. Remind me again later</button>
        </div>
      )}
    </Sheet>
  );
}
