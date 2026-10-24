import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { Log, Session } from "../api";
import { ErrorNote, Header, Icon, Page, Sheet, Spinner, StatusChip, formatDate } from "../components";
import { useApp } from "../state";

interface Queue {
  to_verify: Log[];
  open: Log[];
  not_helpful: Session[];
  escalated_sessions: Session[];
}

export default function Review() {
  const { t, lang, toast } = useApp();
  const [queue, setQueue] = useState<Queue | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [rejecting, setRejecting] = useState<Log | null>(null);
  const [reason, setReason] = useState("");

  const load = useCallback(() => {
    api.get<Queue>("/api/review/queue").then(setQueue).catch(setError);
  }, []);
  useEffect(load, [load]);

  const verify = async (l: Log) => {
    try {
      await api.post(`/api/logs/${l.id}/verify`);
      toast(`${l.log_no}: ${t("status_verified")}`);
      load();
    } catch (e) {
      setError(e);
    }
  };

  const reject = async () => {
    if (!rejecting) return;
    try {
      await api.post(`/api/logs/${rejecting.id}/reject`, { reason });
      setRejecting(null);
      setReason("");
      load();
    } catch (e) {
      setError(e);
    }
  };

  const text = (l: Log, f: "issue" | "root_cause" | "corrective_action") =>
    (lang === "ta" ? l.texts[f].ta || l.texts[f].en : l.texts[f].en || l.texts[f].ta) || l.texts[f].original;

  return (
    <>
      <Header title={t("review")} />
      <Page>
        <ErrorNote error={error} />
        {!queue && !error && <Spinner label={t("loading")} />}
        {queue && (
          <>
            <h2 className="section-title">
              {t("to_verify")} ({queue.to_verify.length})
            </h2>
            {queue.to_verify.length === 0 && <p className="muted">{t("nothing_here")}</p>}
            {queue.to_verify.map((l) => (
              <div key={l.id} className="card">
                <Link to={`/log/${l.id}`} className="card-link">
                  <div className="row-between">
                    <strong className="mono">
                      {l.machine_no} · {l.log_no}
                    </strong>
                    <StatusChip status={l.status} />
                  </div>
                  <p>
                    <strong>{t("issue")}:</strong> {text(l, "issue")}
                  </p>
                  <p>
                    <strong>{t("root_cause")}:</strong> {text(l, "root_cause") || "–"}
                  </p>
                  <p>
                    <strong>{t("corrective_action")}:</strong> {text(l, "corrective_action")}
                  </p>
                  <p className="muted small">
                    {l.technician_name} · {formatDate(l.reported_at, true)} · {l.downtime_min ?? "–"} {t("minutes")}
                  </p>
                </Link>
                <div className="answer-row">
                  <button className="btn btn-ok" onClick={() => void verify(l)}>
                    <Icon name="check" /> {t("verify")}
                  </button>
                  <button className="btn btn-notok" onClick={() => setRejecting(l)}>
                    <Icon name="x" /> {t("reject")}
                  </button>
                </div>
              </div>
            ))}

            <h2 className="section-title">
              {t("open_logs")} ({queue.open.length})
            </h2>
            {queue.open.map((l) => (
              <Link key={l.id} to={`/log/${l.id}`} className="list-item list-item-alert">
                <div>
                  <strong className="mono">{l.machine_no}</strong> · {formatDate(l.reported_at, true)}
                  <div className="clamp">{text(l, "issue")}</div>
                </div>
                <StatusChip status={l.status} />
              </Link>
            ))}

            <h2 className="section-title">
              {t("not_helpful_answers")} ({queue.not_helpful.length})
            </h2>
            {queue.not_helpful.map((s) => (
              <SessionRow key={s.id} s={s} />
            ))}

            <h2 className="section-title">
              {t("escalated_sessions")} ({queue.escalated_sessions.length})
            </h2>
            {queue.escalated_sessions.map((s) => (
              <SessionRow key={s.id} s={s} />
            ))}
          </>
        )}
      </Page>
      {rejecting && (
        <Sheet title={t("reject_reason")} onClose={() => setRejecting(null)}>
          <textarea className="input textarea" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />
          <button className="btn btn-notok btn-block" disabled={reason.trim().length < 2} onClick={() => void reject()}>
            {t("reject")}
          </button>
        </Sheet>
      )}
    </>
  );
}

function SessionRow({ s }: { s: Session & { technician_name?: string; created_at?: string } }) {
  return (
    <div className="list-item">
      <div>
        <strong className="mono">{s.machine_no}</strong> · #{s.id} · {s.outcome}
        <div className="clamp">{s.problem_text}</div>
        <div className="muted small">
          {s.technician_name} · {formatDate(s.created_at, true)}
        </div>
      </div>
      {s.resulting_log_id && <Link to={`/log/${s.resulting_log_id}`}>Log</Link>}
    </div>
  );
}
