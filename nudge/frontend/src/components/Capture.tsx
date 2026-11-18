// Voice / text capture: record → transcribe → understand → review cards → save.
// Fields the assistant guessed are highlighted until you touch them or save.
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, errorText, OfflineError, type Draft, type Interpretation } from "../api";
import { dayLabel } from "../format";
import { Icon } from "../icons";
import { queue } from "../offline";
import { useRecorder } from "../recorder";
import { canSpeak, speak, stopSpeaking } from "../speak";
import { useApp } from "../store";
import { Sheet } from "../ui";
import { TaskRow } from "./TaskRow";

type Phase = "ready" | "recording" | "working" | "review";

const DAY_CODES = ["SU", "MO", "TU", "WE", "TH", "FR", "SA"];
const DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

function repeatOptions(due: string | null, current: string, currentLabel: string): { value: string; label: string }[] {
  const d = due ? new Date(`${due}T00:00:00`) : new Date();
  const opts = [
    { value: "", label: "Doesn't repeat" },
    { value: "FREQ=DAILY", label: "Every day" },
    { value: "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR", label: "Every weekday" },
    { value: `FREQ=WEEKLY;BYDAY=${DAY_CODES[d.getDay()]}`, label: `Every ${DAY_NAMES[d.getDay()]}` },
    { value: `FREQ=MONTHLY;BYMONTHDAY=${d.getDate()}`, label: `Every month on day ${d.getDate()}` },
    { value: "FREQ=YEARLY", label: "Every year" },
  ];
  if (current && !opts.some((o) => o.value === current)) opts.splice(1, 0, { value: current, label: currentLabel || current });
  return opts;
}

function DraftCard({ draft, onChange, onRemove, people }: { draft: Draft; onChange: (d: Draft) => void; onRemove: () => void; people: string[] }) {
  const { baskets } = useApp();
  const g = (f: string) => (draft.guessed.includes(f) ? "guessed" : "");
  const set = (patch: Partial<Draft>, field?: string) =>
    onChange({ ...draft, ...patch, guessed: field ? draft.guessed.filter((x) => x !== field) : draft.guessed });
  const [showMore, setShowMore] = useState(draft.checklist.length > 0 || !!draft.notes);
  const basket = baskets.find((b) => b.id === draft.basket_id);
  return (
    <div className="draft">
      <div className="row" style={{ alignItems: "flex-start" }}>
        <textarea className="title-in" value={draft.title} onChange={(e) => set({ title: e.target.value.replace(/\n/g, " ") })} aria-label="Task title"
          rows={Math.min(3, Math.max(1, Math.ceil(draft.title.length / 30)))} style={{ resize: "none", fontFamily: "inherit" }} />
        <button className="icon-btn" onClick={onRemove} aria-label="Remove this task"><Icon name="x" /></button>
      </div>
      <div className="fieldgrid">
        <label className="mini">Basket
          <select className={`input ${g("basket")}`} value={draft.basket_id ?? ""} style={{ borderLeft: `6px solid var(--c-${basket?.color ?? "slate"})` }}
            onChange={(e) => set({ basket_id: e.target.value ? Number(e.target.value) : null }, "basket")}>
            <option value="">No basket</option>
            {baskets.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
        </label>
        <label className="mini">Priority
          <select className={`input ${g("priority")}`} value={draft.priority} onChange={(e) => set({ priority: e.target.value as Draft["priority"] }, "priority")}>
            <option value="high">High</option><option value="normal">Normal</option><option value="low">Low</option>
          </select>
        </label>
        <label className="mini">Date
          <input className={`input ${g("due_date")}`} type="date" value={draft.due_date ?? ""}
            onChange={(e) => set({ due_date: e.target.value || null }, "due_date")} />
        </label>
        <label className="mini">Time
          <input className={`input ${g("due_time")}`} type="time" value={draft.due_time ?? ""} disabled={!draft.due_date}
            onChange={(e) => set({ due_time: e.target.value || null }, "due_time")} />
        </label>
        <label className="mini">Person
          <input className={`input ${g("person")}`} value={draft.person} list="people-list" placeholder="Who's involved?"
            onChange={(e) => set({ person: e.target.value, waiting: e.target.value ? draft.waiting : false }, "person")} />
        </label>
        <label className="mini">Repeats
          <select className="input" value={draft.repeat_rule} onChange={(e) => set({ repeat_rule: e.target.value })}>
            {repeatOptions(draft.due_date, draft.repeat_rule, draft.repeat_label).map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </label>
      </div>
      {draft.person && (
        <label className="row small" style={{ gap: 10, cursor: "pointer" }}>
          <input type="checkbox" checked={draft.waiting} onChange={(e) => set({ waiting: e.target.checked })} style={{ width: 20, height: 20 }} />
          I'm waiting on {draft.person}. Nudge me to follow up.
        </label>
      )}
      {showMore ? (
        <>
          <label className="mini">Notes
            <textarea className="input" value={draft.notes} onChange={(e) => set({ notes: e.target.value })} style={{ minHeight: 60 }} />
          </label>
          <div className="mini">Checklist
            {draft.checklist.map((c, i) => (
              <div className="row" key={i}>
                <input className="input" value={c} onChange={(e) => set({ checklist: draft.checklist.map((x, j) => (j === i ? e.target.value : x)) })} />
                <button className="icon-btn" onClick={() => set({ checklist: draft.checklist.filter((_, j) => j !== i) })} aria-label="Remove step"><Icon name="x" /></button>
              </div>
            ))}
            <button className="btn small ghost" style={{ alignSelf: "flex-start" }} onClick={() => set({ checklist: [...draft.checklist, ""] })}><Icon name="plus" size={16} />Add a step</button>
          </div>
        </>
      ) : (
        <button className="btn small ghost" style={{ alignSelf: "flex-start" }} onClick={() => setShowMore(true)}><Icon name="plus" size={16} />Notes or checklist</button>
      )}
      {draft.guessed.length > 0 && <div className="tiny" style={{ color: "var(--guess)" }}><Icon name="sparkle" size={12} /> Highlighted fields are my best guess. Change them if they're wrong.</div>}
      {people.length > 0 && <datalist id="people-list">{people.map((p) => <option key={p} value={p} />)}</datalist>}
    </div>
  );
}

export function Capture() {
  const { capture, closeCapture, toast, bump, online } = useApp();
  const nav = useNavigate();
  const [phase, setPhase] = useState<Phase>("ready");
  const [text, setText] = useState("");
  const [result, setResult] = useState<Interpretation | null>(null);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [chosen, setChosen] = useState<number[]>([]);
  const [saving, setSaving] = useState(false);
  const [people, setPeople] = useState<string[]>([]);
  const [speaking, setSpeaking] = useState(false);
  const [source, setSource] = useState<"voice" | "text">("voice");
  const [typing, setTyping] = useState(capture.mode === "text");
  const textRef = useRef<HTMLTextAreaElement>(null);

  const show = useCallback((r: Interpretation) => {
    setResult(r);
    setDrafts(r.drafts);
    setChosen(r.targets.map((t) => t.task_id));
    setPhase("review");
    if (r.intent === "query" && canSpeak() && source === "voice") {
      setSpeaking(true);
      speak(r.answer, () => setSpeaking(false));
    }
  }, [source]);

  const fail = useCallback((e: unknown) => {
    toast({ text: errorText(e), kind: "error" });
    setPhase("ready");
  }, [toast]);

  const onAudio = useCallback(async (blob: Blob) => {
    setSource("voice");
    if (!navigator.onLine) {
      await queue({ kind: "voice", audio: blob });
      toast({ text: "You're offline. I saved the recording and will add it to your Inbox when you're back online." });
      closeCapture();
      return;
    }
    setPhase("working");
    try {
      const form = new FormData();
      form.append("audio", blob, `voice.${blob.type.includes("mp4") ? "m4a" : "webm"}`);
      show(await api.upload<Interpretation>("/api/assistant/voice", form));
    } catch (e) {
      if (e instanceof OfflineError) {
        await queue({ kind: "voice", audio: blob });
        toast({ text: "Connection dropped. Saved the recording to add later." });
        closeCapture();
      } else fail(e);
    }
  }, [closeCapture, fail, show, toast]);

  const rec = useRecorder(onAudio);

  useEffect(() => {
    if (!capture.open) return;
    setPhase("ready");
    setResult(null);
    setText("");
    setTyping(capture.mode === "text");
    api.get<{ names: string[] }>("/api/people/names").then((r) => setPeople(r.names)).catch(() => {});
    if (capture.autostart && capture.mode === "voice") rec.start();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [capture.open]);

  useEffect(() => {
    if (rec.state === "recording") setPhase("recording");
    else if (rec.state === "denied") {
      setTyping(true);
      setPhase("ready");
    } else if (phase === "recording" && rec.state === "idle") setPhase((p) => (p === "recording" ? "working" : p));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rec.state]);

  useEffect(() => {
    const stop = () => rec.stop();
    window.addEventListener("nudge-stop-recording", stop);
    return () => window.removeEventListener("nudge-stop-recording", stop);
  }, [rec]);

  useEffect(() => {
    if (typing && phase === "ready") textRef.current?.focus();
  }, [typing, phase]);

  if (!capture.open) return null;

  const close = () => {
    rec.cancel();
    stopSpeaking();
    closeCapture();
  };

  const interpretText = async (value = text) => {
    const v = value.trim();
    if (!v) return;
    setSource("text");
    if (!navigator.onLine) {
      await queue({ kind: "create", body: { title: v.slice(0, 300), inbox: true, source: "text" } });
      toast({ text: "Added to your Inbox offline. It will sync later." });
      close();
      return;
    }
    setPhase("working");
    try {
      show(await api.post<Interpretation>("/api/assistant/interpret", { text: v }));
    } catch (e) {
      fail(e);
    }
  };

  const saveDrafts = async () => {
    const valid = drafts.filter((d) => d.title.trim());
    if (!valid.length) return;
    setSaving(true);
    try {
      const r = await api.post<{ created: { id: number }[] }>("/api/assistant/apply", {
        intent: "create", transcript: result?.transcript ?? "", source, drafts: valid,
      });
      bump();
      toast({
        text: r.created.length === 1 ? "Saved 1 task" : `Saved ${r.created.length} tasks`,
        actions: r.created.length === 1 ? [{ label: "Open", onClick: () => nav(`/task/${r.created[0].id}`) }] : undefined,
      });
      close();
    } catch (e) {
      toast({ text: errorText(e), kind: "error" });
    } finally {
      setSaving(false);
    }
  };

  const saveAsNote = async () => {
    if (!result) return;
    try {
      await api.post("/api/tasks", { title: result.transcript.slice(0, 300), inbox: true, source });
      bump();
      toast({ text: "Saved to your Inbox as one note" });
      close();
    } catch (e) {
      toast({ text: errorText(e), kind: "error" });
    }
  };

  const applyCommand = async () => {
    if (!result) return;
    setSaving(true);
    try {
      await api.post("/api/assistant/apply", {
        intent: result.intent, targets: result.targets.filter((t) => chosen.includes(t.task_id)),
      });
      bump();
      toast({ text: result.intent === "complete" ? "Marked done" : "Moved" });
      close();
    } catch (e) {
      toast({ text: errorText(e), kind: "error" });
    } finally {
      setSaving(false);
    }
  };

  const title = phase === "review" && result
    ? result.intent === "create" ? `Check ${drafts.length === 1 ? "this task" : `these ${drafts.length} tasks`}`
      : result.intent === "query" ? "Here's what I found" : result.intent === "unclear" ? "Not sure what you meant" : "Confirm"
    : "Add tasks";

  return (
    <Sheet title={title} onClose={close} wide={phase === "review"}>
      {phase === "ready" && !typing && (
        <div className="rec">
          <button className="bigmic" onClick={rec.start} aria-label="Start recording"><Icon name="mic" size={38} /></button>
          <div className="muted" style={{ textAlign: "center", maxWidth: 420 }}>
            Tap and say everything on your mind. For example: <i>“Call the vendor tomorrow at 11, send the PM report by Friday, and follow up with Ravi next Tuesday.”</i>
          </div>
          {rec.state === "unsupported" && <div className="warnbox">This browser can't record audio. Type instead.</div>}
          <button className="btn ghost" onClick={() => setTyping(true)}><Icon name="keyboard" />Type instead</button>
        </div>
      )}

      {phase === "ready" && typing && (
        <div className="stack">
          {rec.state === "denied" && <div className="warnbox">Microphone access is blocked. Allow it in your browser settings to talk, or type below.</div>}
          <textarea ref={textRef} className="input" value={text} onChange={(e) => setText(e.target.value)}
            placeholder="e.g. Pay the electricity bill tomorrow, follow up with Kumar on the calibration certificates"
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); interpretText(); } }} />
          <div className="row">
            {rec.state !== "unsupported" && <button className="btn" onClick={() => { setTyping(false); rec.start(); }}><Icon name="mic" />Talk instead</button>}
            <div className="grow" />
            <button className="btn primary" onClick={() => interpretText()} disabled={!text.trim()}><Icon name="arrow" />{online ? "Continue" : "Add to Inbox"}</button>
          </div>
        </div>
      )}

      {phase === "recording" && (
        <div className="rec">
          <div className="bars" aria-hidden="true">{rec.levels.map((l, i) => <i key={i} style={{ height: `${Math.round(8 + l * 48)}px` }} />)}</div>
          <div className="timer">Listening… {rec.seconds}s <span className="tiny">(up to {rec.maxSeconds}s)</span></div>
          <button className="bigmic on" onClick={rec.stop} aria-label="Stop recording"><Icon name="stop" size={34} /></button>
          <div className="row">
            <button className="btn ghost" onClick={() => { rec.cancel(); setPhase("ready"); }}>Cancel</button>
          </div>
        </div>
      )}

      {phase === "working" && (
        <div className="rec">
          <div className="spin" style={{ width: 36, height: 36 }} />
          <div className="muted">{source === "voice" ? "Listening back and sorting it out…" : "Sorting it out…"}</div>
        </div>
      )}

      {phase === "review" && result && (
        <div className="stack">
          {result.warning && <div className="warnbox">{result.warning}</div>}
          <div className="row" style={{ alignItems: "flex-start" }}>
            <div className="transcript grow">“{result.transcript}”</div>
            <button className="btn small ghost" onClick={() => { setText(result.transcript); setTyping(true); setPhase("ready"); }}><Icon name="edit" size={16} />Edit</button>
          </div>

          {result.intent === "create" && (
            <>
              {drafts.map((d, i) => (
                <DraftCard key={i} draft={d} people={people}
                  onChange={(nd) => setDrafts(drafts.map((x, j) => (j === i ? nd : x)))}
                  onRemove={() => setDrafts(drafts.filter((_, j) => j !== i))} />
              ))}
              <div className="row wrap">
                <button className="btn ghost small" onClick={() => setDrafts([...drafts, {
                  title: "", notes: "", basket_id: null, basket: null, due_date: null, due_time: null, priority: "normal",
                  person: "", waiting: false, repeat_rule: "", repeat_label: "", checklist: [], guessed: [],
                }])}><Icon name="plus" size={16} />Add another</button>
                <button className="btn ghost small" onClick={saveAsNote}>Save as one note instead</button>
              </div>
              <button className="btn primary block" onClick={saveDrafts} disabled={saving || !drafts.some((d) => d.title.trim())}>
                <Icon name="check" />{saving ? "Saving…" : drafts.length === 1 ? "Save task" : `Save ${drafts.length} tasks`}
              </button>
              <div className="tiny muted" style={{ textAlign: "center" }}>
                {result.understood_by === "claude" ? "Understood by Claude" : "Understood by built-in rules"}
              </div>
            </>
          )}

          {(result.intent === "complete" || result.intent === "reschedule") && (
            <>
              <div className="answer">{result.answer}</div>
              {result.targets.map((t) => (
                <label key={t.task_id} className="row card card-pad" style={{ cursor: "pointer" }}>
                  <input type="checkbox" checked={chosen.includes(t.task_id)} style={{ width: 20, height: 20 }}
                    onChange={(e) => setChosen(e.target.checked ? [...chosen, t.task_id] : chosen.filter((x) => x !== t.task_id))} />
                  <div className="grow">
                    <div style={{ fontWeight: 600 }}>{t.title}</div>
                    {result.intent === "reschedule" && t.due_date && <div className="small muted">New date: {dayLabel(t.due_date)}{t.due_time ? ` ${t.due_time}` : ""}</div>}
                  </div>
                </label>
              ))}
              {result.targets.length > 0 ? (
                <button className="btn primary block" onClick={applyCommand} disabled={saving || !chosen.length}>
                  <Icon name="check" />{result.intent === "complete" ? "Mark done" : "Move it"}
                </button>
              ) : <button className="btn block" onClick={() => setPhase("ready")}>Try again</button>}
            </>
          )}

          {result.intent === "query" && (
            <>
              <div className="answer row" style={{ alignItems: "flex-start" }}>
                <div className="grow">{result.answer}</div>
                {canSpeak() && (
                  <button className="icon-btn" aria-label={speaking ? "Stop reading" : "Read aloud"}
                    onClick={() => { if (speaking) { stopSpeaking(); setSpeaking(false); } else { setSpeaking(true); speak(result.answer, () => setSpeaking(false)); } }}>
                    <Icon name={speaking ? "stop" : "volume"} />
                  </button>
                )}
              </div>
              {result.matches.length > 0 && <div className="card">{result.matches.map((t) => <TaskRow key={t.id} task={t} />)}</div>}
              <button className="btn block" onClick={close}>Done</button>
            </>
          )}

          {result.intent === "unclear" && (
            <>
              <div className="answer">{result.answer || "I couldn't work that out."}</div>
              <div className="row">
                <button className="btn" onClick={() => { setTyping(false); setPhase("ready"); }}><Icon name="mic" />Try again</button>
                <button className="btn" onClick={saveAsNote}>Save it as a note</button>
              </div>
            </>
          )}
        </div>
      )}
    </Sheet>
  );
}

