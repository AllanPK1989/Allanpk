// Supervisor review of a fault card: check the AI draft against its source logs, edit, approve,
// reject, retire or re-draft. Every action is audited on the server; approved edits create a new version.
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import type { FaultCard, Log } from "../api";
import { ErrorNote, Header, Icon, Page, Sheet, Spinner, formatDate } from "../components";
import { useApp } from "../state";

const lines = (text: string) => text.split("\n").map((l) => l.trim()).filter(Boolean);
const list = (text: string) => text.split(",").map((l) => l.trim()).filter(Boolean);

export default function CardPage() {
  const { id } = useParams();
  const { t, toast } = useApp();
  const navigate = useNavigate();
  const [card, setCard] = useState<FaultCard | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ symptom: "", symptom_ta: "", causes: "", causes_ta: "", steps_en: "", steps_ta: "", parts: "", tools: "" });
  const [reasonFor, setReasonFor] = useState<"" | "reject" | "retire">("");
  const [reason, setReason] = useState("");

  const load = (c: FaultCard) => {
    setCard(c);
    setForm({
      symptom: c.symptom,
      symptom_ta: c.symptom_ta,
      causes: c.causes.map((x) => x.cause).join("\n"),
      causes_ta: c.causes.map((x) => x.cause_ta ?? "").join("\n"),
      steps_en: c.steps_en.join("\n"),
      steps_ta: c.steps_ta.join("\n"),
      parts: c.parts.join(", "),
      tools: c.tools.join(", "),
    });
  };

  useEffect(() => {
    api.get<FaultCard>(`/api/fault-cards/${id}`).then(load).catch(setError);
  }, [id]);

  const run = async (fn: () => Promise<FaultCard>, message: string) => {
    setBusy(true);
    setError(null);
    try {
      const c = await fn();
      toast(message);
      if (String(c.id) !== id) navigate(`/cards/${c.id}`, { replace: true });
      else load(c);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  const save = () => {
    const causesTa = lines(form.causes_ta);
    return run(
      () =>
        api.patch<FaultCard>(`/api/fault-cards/${id}`, {
          symptom: form.symptom,
          symptom_ta: form.symptom_ta,
          causes: lines(form.causes).map((cause, i) => ({ cause, cause_ta: causesTa[i] ?? "" })),
          steps_en: lines(form.steps_en),
          steps_ta: lines(form.steps_ta),
          parts: list(form.parts),
          tools: list(form.tools),
        }),
      t("saved"),
    );
  };

  if (!card) {
    return (
      <>
        <Header title={`FC-${id}`} />
        <Page>{error ? <ErrorNote error={error} /> : <Spinner label={t("loading")} />}</Page>
      </>
    );
  }

  const editable = !["rejected", "retired"].includes(card.status);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setForm({ ...form, [k]: e.target.value });

  return (
    <>
      <Header title={`${card.ref} · v${card.version}`} />
      <Page
        footer={
          editable ? (
            <div className="footer-stack">
              <div className="answer-row">
                {["draft", "needs_review"].includes(card.status) && (
                  <button className="btn btn-ok" disabled={busy} onClick={() => void run(() => api.post(`/api/fault-cards/${id}/approve`), "Approved")}>
                    <Icon name="check" /> Approve
                  </button>
                )}
                {card.status === "draft" && (
                  <button className="btn btn-notok" disabled={busy} onClick={() => setReasonFor("reject")}>
                    <Icon name="x" /> Reject
                  </button>
                )}
                {["approved", "needs_review"].includes(card.status) && (
                  <button className="btn btn-neutral" disabled={busy} onClick={() => setReasonFor("retire")}>
                    Retire
                  </button>
                )}
              </div>
              <div className="answer-row btn-small-row">
                <button className="btn btn-primary" disabled={busy} onClick={() => void save()}>
                  Save edits
                </button>
                <button className="btn btn-ghost" disabled={busy} onClick={() => void run(() => api.post(`/api/fault-cards/${id}/redraft`), "New draft written")}>
                  Re-draft from logs
                </button>
              </div>
            </div>
          ) : undefined
        }
      >
        <ErrorNote error={error} />
        <div className="row-between">
          <div>
            <strong>{card.scope === "type" ? `All machines of type ${card.scope_name}` : `${card.machine_no} · ${card.scope_name}`}</strong>
            <div className="muted small">
              {card.source_log_ids.length} source logs
              {card.avg_fix_min != null && ` · average fix ${card.avg_fix_min} min`}
              {card.replaces_id && ` · re-draft of FC-${card.replaces_id}`}
            </div>
          </div>
          <span className={`chip ${card.status === "approved" ? "chip-verified" : card.status === "needs_review" ? "chip-open" : "chip-draft"}`}>
            {t(`card_status_${card.status}` as "card_status_draft")}
          </span>
        </div>
        {card.status === "draft" && (
          <p className="note note-info">Written by the AI from the logs below. Check every cause and step before approving.</p>
        )}
        {card.review_note && <p className="note note-warn">{card.review_note}</p>}

        <label className="field">
          <span className="field-title">Symptom</span>
          <input className="input" value={form.symptom} onChange={set("symptom")} disabled={!editable} />
          <input className="input" value={form.symptom_ta} onChange={set("symptom_ta")} disabled={!editable} placeholder="Tamil" />
        </label>

        <div className="field">
          <span className="field-title">Causes, most frequent first</span>
          <ul className="causes">
            {card.causes.map((c, i) => (
              <li key={i}>
                {c.cause} <span className="count">{t("times", { n: c.count })}</span>
              </li>
            ))}
          </ul>
          <textarea className="input textarea" rows={3} value={form.causes} onChange={set("causes")} disabled={!editable} aria-label="Causes, one per line" />
          <textarea className="input textarea" rows={3} value={form.causes_ta} onChange={set("causes_ta")} disabled={!editable} aria-label="Causes in Tamil" placeholder="Tamil, one per line" />
          <small className="muted">One per line. Counts come from the logs and are kept when you edit the text.</small>
        </div>

        <div className="grid-2">
          <label className="field">
            <span className="field-title">Steps (English), one per line</span>
            <textarea className="input textarea" rows={8} value={form.steps_en} onChange={set("steps_en")} disabled={!editable} />
          </label>
          <label className="field">
            <span className="field-title">Steps (Tamil), one per line</span>
            <textarea className="input textarea" rows={8} value={form.steps_ta} onChange={set("steps_ta")} disabled={!editable} />
          </label>
        </div>
        <p className="muted small">LOTO and other safety steps are added automatically in front of every procedure.</p>
        <label className="field">
          <span>Parts (comma separated)</span>
          <input className="input" value={form.parts} onChange={set("parts")} disabled={!editable} />
        </label>
        <label className="field">
          <span>Tools (comma separated)</span>
          <input className="input" value={form.tools} onChange={set("tools")} disabled={!editable} />
        </label>

        {!!card.flagged_logs?.length && (
          <>
            <h2 className="section-title">Logs that do not match this card</h2>
            {card.flagged_logs.map((l) => (
              <LogRow key={l.id} log={l} alert />
            ))}
          </>
        )}
        <h2 className="section-title">Source logs</h2>
        {card.source_logs?.map((l) => (
          <LogRow key={l.id} log={l} />
        ))}
        {card.history.length > 0 && (
          <>
            <h2 className="section-title">Earlier versions</h2>
            {card.history
              .slice()
              .reverse()
              .map((h) => (
                <details key={h.version} className="card">
                  <summary>
                    v{h.version} · {h.symptom} · archived {formatDate(h.archived_at)}
                  </summary>
                  <ol className="card-steps">
                    {h.steps_en.map((s, i) => (
                      <li key={i}>{s}</li>
                    ))}
                  </ol>
                </details>
              ))}
          </>
        )}
      </Page>
      {reasonFor && (
        <Sheet title={reasonFor === "reject" ? "Reject draft" : "Retire card"} onClose={() => setReasonFor("")}>
          <textarea className="input textarea" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason" />
          <button
            className="btn btn-notok btn-block"
            disabled={reason.trim().length < 2}
            onClick={() => {
              const action = reasonFor;
              setReasonFor("");
              void run(() => api.post(`/api/fault-cards/${id}/${action}`, { reason }), action === "reject" ? "Rejected" : "Retired");
            }}
          >
            {reasonFor === "reject" ? "Reject" : "Retire"}
          </button>
        </Sheet>
      )}
    </>
  );
}

function LogRow({ log, alert = false }: { log: Log; alert?: boolean }) {
  const pick = (f: "issue" | "root_cause" | "corrective_action") => log.texts[f].en || log.texts[f].original;
  return (
    <Link to={`/log/${log.id}`} className={`list-item ${alert ? "list-item-alert" : ""}`}>
      <div>
        <strong className="mono">{log.log_no}</strong> · {log.machine_no} · {formatDate(log.shift_date ?? log.reported_at)}
        <div className="small">
          {pick("issue")} → <strong>{pick("root_cause") || "no cause"}</strong>
        </div>
        <div className="muted small">{pick("corrective_action")}</div>
      </div>
      <span className={`chip chip-${log.status}`}>{log.status}</span>
    </Link>
  );
}
