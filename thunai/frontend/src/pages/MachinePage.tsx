import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, openFile } from "../api";
import type { Log, MachinePage as Data } from "../api";
import { ErrorNote, Header, Icon, MicButton, OfflineBanner, Page, Sheet, Spinner, StatusChip, formatDate } from "../components";
import type { VoiceResult } from "../components";
import { useApp } from "../state";

export default function MachinePage() {
  const { no = "" } = useParams();
  const { t, lang, toast } = useApp();
  const navigate = useNavigate();
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [openCard, setOpenCard] = useState<number | null>(null);
  const [tipOpen, setTipOpen] = useState(false);
  const [tipText, setTipText] = useState("");
  const [tipMedia, setTipMedia] = useState<number | null>(null);

  const onTipVoice = useCallback((r: VoiceResult) => {
    if (r.text) setTipText((v) => (v ? `${v} ${r.text}` : r.text));
    if (r.mediaId) setTipMedia(r.mediaId);
  }, []);

  const sendTip = async () => {
    try {
      await api.post("/api/tips", { machine_no: no, text: tipText, media_id: tipMedia });
      toast(t("tip_sent"));
      setTipOpen(false);
      setTipText("");
      setTipMedia(null);
    } catch (e) {
      setError(e);
    }
  };

  useEffect(() => {
    api.get<Data>(`/api/machines/${encodeURIComponent(no)}`).then(setData).catch(setError);
  }, [no]);

  const text = (l: Log) =>
    l.texts.issue.original || (lang === "ta" ? l.texts.issue.ta || l.texts.issue.en : l.texts.issue.en || l.texts.issue.ta);

  return (
    <>
      <Header title={no.toUpperCase()} />
      <OfflineBanner />
      <Page>
        <ErrorNote error={error} />
        {!data && !error && <Spinner label={t("loading")} />}
        {data && (
          <>
            <section className="machine-head">
              <h2>{data.machine.name}</h2>
              <p className="muted">
                {data.machine.machine_type} · {data.machine.zone}
                {data.machine.line ? ` · ${data.machine.line}` : ""}
              </p>
              <div className="chips-row">
                <span className={`chip chip-m-${data.machine.status}`}>{data.machine.status}</span>
                <span className="chip">Criticality {data.machine.criticality}</span>
                {data.machine.plc_model && <span className="chip">{data.machine.plc_model}</span>}
              </div>
            </section>
            <div className="tile-row two">
              <button className="tile tile-primary tile-compact" onClick={() => navigate(`/ask/${encodeURIComponent(no)}`)}>
                <Icon name="help" size={30} />
                <strong>{t("ask")}</strong>
              </button>
              <button className="tile tile-accent tile-compact" onClick={() => navigate(`/log/new/${encodeURIComponent(no)}`)}>
                <Icon name="mic" size={30} />
                <strong>{t("new_log")}</strong>
              </button>
            </div>

            <section className="kpis" aria-label="KPIs">
              <div className="kpi">
                <span className="kpi-value">{data.kpi.breakdowns}</span>
                <span className="kpi-label">{t("breakdowns")}</span>
              </div>
              <div className="kpi">
                <span className="kpi-value">{data.kpi.mttr_min ?? "–"}</span>
                <span className="kpi-label">
                  {t("mttr")} ({t("minutes")})
                </span>
              </div>
              <div className="kpi">
                <span className="kpi-value">{data.kpi.mtbf_h ?? "–"}</span>
                <span className="kpi-label">{t("mtbf")} (h)</span>
              </div>
              <p className="kpi-foot muted">{t("last_days", { n: data.kpi.period_days })}</p>
            </section>

            {data.open_logs.length > 0 && (
              <section>
                <h2 className="section-title">{t("open_issues")}</h2>
                {data.open_logs.map((l) => (
                  <Link key={l.id} to={`/log/${l.id}`} className="list-item list-item-alert">
                    <div>
                      <strong>{l.log_no}</strong> · {formatDate(l.reported_at, true)}
                      <div className="clamp">{text(l)}</div>
                    </div>
                    <StatusChip status={l.status} />
                  </Link>
                ))}
              </section>
            )}

            <section>
              <h2 className="section-title">{t("top_faults")}</h2>
              {data.top_faults.length === 0 && <p className="muted">{t("no_history")}</p>}
              {data.top_faults.map((f) => (
                <div key={f.symptom} className="fault-row">
                  <div>
                    <strong>{lang === "ta" && f.symptom_ta ? f.symptom_ta : f.symptom}</strong>
                    <div className="muted">
                      {formatDate(f.last)}
                      {f.avg_downtime_min != null && ` · ${t("avg_min", { n: f.avg_downtime_min })}`}
                    </div>
                  </div>
                  <span className="count">{t("times", { n: f.count })}</span>
                </div>
              ))}
            </section>

            {data.fault_cards.length > 0 && (
              <section>
                <h2 className="section-title">{t("fault_cards")}</h2>
                {data.fault_cards.map((c) => (
                  <div key={c.id} className="card">
                    <button className="card-toggle" onClick={() => setOpenCard(openCard === c.id ? null : c.id)} aria-expanded={openCard === c.id}>
                      <span>
                        <span className="chip chip-verified">{c.ref}</span>{" "}
                        {c.status === "needs_review" && <span className="chip chip-draft">{t("needs_review")}</span>}{" "}
                        {lang === "ta" && c.symptom_ta ? c.symptom_ta : c.symptom}
                      </span>
                      <Icon name="book" />
                    </button>
                    {openCard === c.id && (
                      <div className="card-body">
                        <ul className="causes">
                          {c.causes.map((x) => (
                            <li key={x.cause}>
                              {lang === "ta" && x.cause_ta ? x.cause_ta : x.cause} <span className="count">{t("times", { n: x.count })}</span>
                            </li>
                          ))}
                        </ul>
                        <ol className="card-steps">
                          {(lang === "ta" && c.steps_ta.length ? c.steps_ta : c.steps_en).map((s, i) => (
                            <li key={i}>{s}</li>
                          ))}
                        </ol>
                        {c.avg_fix_min && <p className="muted">{t("avg_min", { n: c.avg_fix_min })}</p>}
                      </div>
                    )}
                  </div>
                ))}
              </section>
            )}

            <section>
              <div className="row-between">
                <h2 className="section-title">{t("expert_tips")}</h2>
                <button className="btn btn-ghost btn-small" onClick={() => setTipOpen(true)}>
                  <Icon name="plus" size={18} /> {t("add_tip")}
                </button>
              </div>
              {data.tips.length === 0 && <p className="muted">{t("nothing_here")}</p>}
              {data.tips.map((tip) => (
                <div key={tip.id} className="tip">
                  <p>{lang === "ta" ? tip.ta || tip.original : tip.en || tip.original}</p>
                  <span className="muted small">
                    {tip.author} · {formatDate(tip.created_at)}
                  </span>
                </div>
              ))}
            </section>

            {data.documents.length > 0 && (
              <section>
                <h2 className="section-title">{t("documents")}</h2>
                {data.documents.map((d) => (
                  <button key={d.id} className="list-item" onClick={() => void openFile(`/api/documents/${d.id}/file`).catch(setError)}>
                    <div>
                      <strong>{d.title}</strong>
                      <div className="muted small">
                        {d.kind.replace("_", " ")}
                        {d.pages ? ` · ${d.pages} ${d.pages === 1 ? "page" : "pages"}` : ""}
                        {d.scope === "type" ? ` · ${d.type_name}` : ""}
                      </div>
                    </div>
                    <Icon name="book" />
                  </button>
                ))}
              </section>
            )}

            <section>
              <h2 className="section-title">{t("history")}</h2>
              {data.timeline.length === 0 && <p className="muted">{t("no_history")}</p>}
              <ol className="timeline">
                {data.timeline.map((l) => (
                  <li key={l.id}>
                    <Link to={`/log/${l.id}`}>
                      <div className="row-between">
                        <strong>{formatDate(l.shift_date ?? l.reported_at)}</strong>
                        <StatusChip status={l.status} />
                      </div>
                      <div>{text(l)}</div>
                      <div className="muted">
                        {(lang === "ta" ? l.texts.corrective_action.ta : l.texts.corrective_action.en) || l.texts.corrective_action.original}
                        {l.downtime_min != null && ` · ${l.downtime_min} ${t("minutes")}`}
                      </div>
                    </Link>
                  </li>
                ))}
              </ol>
            </section>
          </>
        )}
      </Page>
      {tipOpen && (
        <Sheet title={t("add_tip")} onClose={() => setTipOpen(false)}>
          <p className="muted">{t("tip_hint")}</p>
          <MicButton onResult={onTipVoice} language={lang} compact />
          <textarea className="input textarea" rows={4} value={tipText} onChange={(e) => setTipText(e.target.value)} />
          <button className="btn btn-primary btn-block" disabled={tipText.trim().length < 2} onClick={() => void sendTip()}>
            {t("submit")}
          </button>
        </Sheet>
      )}
    </>
  );
}
