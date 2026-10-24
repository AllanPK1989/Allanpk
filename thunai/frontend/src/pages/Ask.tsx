import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import type { Alarm, Session, Step, Supervisor } from "../api";
import type { Lang } from "../i18n";
import { ErrorNote, Header, Icon, MicButton, Page, Sheet, Spinner, SupervisorSheet, formatDate } from "../components";
import type { VoiceResult } from "../components";
import { hasVoice, speak, stopSpeaking } from "../speak";
import { useApp } from "../state";

type Phase = "describe" | "questions" | "steps" | "finish" | "done";

function pick(step: Step, field: "action" | "check" | "expected_result" | "safety_note", lang: Lang): string {
  const ta = step[`${field}_ta` as keyof Step] as string;
  const en = step[`${field}_en` as keyof Step] as string;
  return lang === "ta" ? ta || en : en || ta;
}

function evidenceText(item: Step["evidence"]["items"][number], lang: Lang): string {
  const d = item.data ?? {};
  const pickText = (en: unknown, ta: unknown) => String((lang === "ta" && ta) || en || ta || "");
  if (item.kind === "fault_card") {
    const causes = Array.isArray(d.causes)
      ? d.causes.map((c) => `${(lang === "ta" && c.cause_ta) || c.cause} (${c.count})`).join(", ")
      : "";
    return `${pickText(d.symptom, d.symptom_ta)}${causes ? ` · ${causes}` : ""}`;
  }
  if (item.kind === "tip") return pickText(d.text_en, d.text_ta);
  if (item.kind === "doc") return `${d.title}, page ${d.page}`;
  if (item.kind === "alarm") return `${d.code}: ${d.message}${d.remedy ? ` → ${d.remedy}` : ""}`;
  const issue = pickText(d.issue_en, d.issue_ta);
  const fix = pickText(d.corrective_action_en, d.corrective_action_ta);
  return fix ? `${issue} → ${fix}` : issue || item.text_en;
}

export default function Ask() {
  const { no = "" } = useParams();
  const { t, lang, toast, sessionFinished } = useApp();
  const navigate = useNavigate();
  const [phase, setPhase] = useState<Phase>("describe");
  const [problem, setProblem] = useState("");
  const [alarm, setAlarm] = useState("");
  const [mediaIds, setMediaIds] = useState<number[]>([]);
  const [session, setSession] = useState<Session | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [current, setCurrent] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [sheet, setSheet] = useState<"" | "why" | "explain" | "cant" | "stop">("");
  const [explanation, setExplanation] = useState<{ text_en: string; text_ta: string } | null>(null);
  const [supervisor, setSupervisor] = useState<{ summary: string; supervisors: Supervisor[] } | null>(null);
  const [resultMsg, setResultMsg] = useState("");
  const [feedbackSent, setFeedbackSent] = useState(false);
  const [alarmInfo, setAlarmInfo] = useState<Alarm | null>(null);

  // Alarm lists (Phase 2): show what the code means as soon as it is typed.
  useEffect(() => {
    const code = alarm.trim();
    if (code.length < 2) {
      setAlarmInfo(null);
      return;
    }
    const timer = window.setTimeout(() => {
      api
        .get<{ alarm: Alarm | null }>(`/api/alarms/lookup?machine_no=${encodeURIComponent(no)}&code=${encodeURIComponent(code)}`)
        .then((r) => setAlarmInfo(r.alarm))
        .catch(() => setAlarmInfo(null));
    }, 400);
    return () => window.clearTimeout(timer);
  }, [alarm, no]);

  useEffect(() => () => stopSpeaking(), []);

  const route = useCallback((s: Session) => {
    setSession(s);
    if (s.outcome === "refused" || s.outcome === "failed") setPhase("done");
    else if (s.steps.length) {
      setCurrent(s.steps[0].step_no);
      setPhase("steps");
    } else if (s.questions.length) setPhase("questions");
  }, []);

  const start = async () => {
    setBusy(true);
    setError(null);
    try {
      const s = await api.post<Session>("/api/ai/sessions", {
        machine_no: no,
        problem_text: problem,
        language: lang,
        alarm_code: alarm,
        media_ids: mediaIds,
      });
      route(s);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  const sendAnswers = async () => {
    if (!session) return;
    setBusy(true);
    setError(null);
    try {
      route(await api.post<Session>(`/api/ai/sessions/${session.id}/answers`, { answers }));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  const step = session?.steps.find((s) => s.step_no === current);
  const total = session?.steps.length ?? 0;
  const position = session ? session.steps.findIndex((s) => s.step_no === current) + 1 : 0;

  const goTo = (next: number | null) => {
    stopSpeaking();
    setExplanation(null);
    if (next === 0) setPhase("finish");
    else if (next === -1) {
      setSheet("stop");
    } else if (next !== null) setCurrent(next);
  };

  const respond = async (response: "ok" | "not_ok" | "cant_do") => {
    if (!session || !step) return;
    try {
      const r = await api.post<{ next: number | null }>(`/api/ai/sessions/${session.id}/steps`, { step_no: step.step_no, response });
      if (response === "cant_do" && r.next === null) setSheet("cant");
      else goTo(r.next);
    } catch (e) {
      setError(e);
    }
  };

  const callSupervisor = async () => {
    if (!session) return;
    try {
      setSupervisor(await api.post(`/api/ai/sessions/${session.id}/call-supervisor`));
    } catch (e) {
      setError(e);
    }
  };

  const explain = async () => {
    if (!session || !step) return;
    setSheet("explain");
    setExplanation(null);
    try {
      setExplanation(await api.post(`/api/ai/sessions/${session.id}/explain`, { step_no: step.step_no }));
    } catch (e) {
      setSheet("");
      setError(e);
    }
  };

  const close = async (running: boolean) => {
    if (!session) return;
    setBusy(true);
    try {
      const r = await api.post<{ log_id: number; outcome: string; summary: string; supervisors: Supervisor[] }>(
        `/api/ai/sessions/${session.id}/close`,
        { running },
      );
      if (running) {
        toast(t("saved"));
        navigate(`/log/${r.log_id}`, { replace: true });
      } else {
        setResultMsg(t("escalated"));
        setSupervisor({ summary: r.summary, supervisors: r.supervisors });
        setPhase("done");
      }
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  const feedback = async (value: "helpful" | "not_helpful") => {
    if (!session) return;
    await api.post(`/api/ai/sessions/${session.id}/feedback`, { feedback: value }).catch(() => {});
    setFeedbackSent(true);
    toast(t("thanks"));
    sessionFinished();
  };

  const onVoice = useCallback((r: VoiceResult) => {
    if (r.text) setProblem((p) => (p ? `${p} ${r.text}` : r.text));
    if (r.mediaId) setMediaIds((ids) => [...ids, r.mediaId as number]);
  }, []);

  const addPhoto = async (file: File | undefined) => {
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    try {
      const r = await api.upload<{ media_id: number }>("/api/media/photo", form);
      setMediaIds((ids) => [...ids, r.media_id]);
      toast(t("photo_added"));
    } catch (e) {
      setError(e);
    }
  };

  const readStep = () => {
    if (!step) return;
    if (lang === "ta" && !hasVoice("ta")) toast(t("no_tamil_voice"));
    speak(
      [pick(step, "action", lang), pick(step, "check", lang), pick(step, "expected_result", lang) && `${t("expected")}: ${pick(step, "expected_result", lang)}`, pick(step, "safety_note", lang)]
        .filter(Boolean)
        .join(". "),
      lang,
    );
  };

  // The answer buttons and "Call supervisor" stay on screen however long the step text is.
  const footer =
    phase === "steps" && step ? (
      <div className="footer-stack">
        <div className="answer-row">
          <button className="btn btn-ok" onClick={() => void respond("ok")}>
            <Icon name="check" size={30} /> {t("ok")}
          </button>
          <button className="btn btn-notok" onClick={() => void respond("not_ok")}>
            <Icon name="x" size={30} /> {t("not_ok")}
          </button>
        </div>
        <div className="answer-row btn-small-row">
          <button className="btn btn-neutral" onClick={() => void respond("cant_do")}>
            {t("cant_do")}
          </button>
          <button className="btn btn-danger" onClick={() => void callSupervisor()}>
            <Icon name="phone" /> {t("call_supervisor")}
          </button>
        </div>
      </div>
    ) : phase !== "describe" && session ? (
      <button className="btn btn-danger btn-block btn-big" onClick={() => void callSupervisor()}>
        <Icon name="phone" /> {t("call_supervisor")}
      </button>
    ) : undefined;

  return (
    <>
      <Header title={no.toUpperCase()} />
      <Page footer={footer}>
        <ErrorNote error={error} />

        {phase === "describe" && (
          <>
            <label className="field">
              <span className="field-title">{t("describe_problem")}</span>
              <textarea className="input textarea" rows={4} value={problem} onChange={(e) => setProblem(e.target.value)} placeholder={t("describe_hint")} />
            </label>
            <MicButton onResult={onVoice} language={lang} />
            <label className="field">
              <span>{t("alarm_code")}</span>
              <input className="input" value={alarm} onChange={(e) => setAlarm(e.target.value)} />
            </label>
            {alarmInfo && (
              <div className="alarm-card" role="status">
                <strong>
                  {t("alarm_meaning", { code: alarmInfo.code })}: {alarmInfo.message}
                </strong>
                {alarmInfo.cause && (
                  <p>
                    <span className="muted">{t("cause")}: </span>
                    {alarmInfo.cause}
                  </p>
                )}
                {alarmInfo.remedy && (
                  <p>
                    <span className="muted">{t("remedy")}: </span>
                    {alarmInfo.remedy}
                  </p>
                )}
              </div>
            )}
            <label className="btn btn-ghost btn-block file-btn">
              <Icon name="camera" /> {t("add_photo")}
              <input type="file" accept="image/*" capture="environment" hidden onChange={(e) => void addPhoto(e.target.files?.[0])} />
            </label>
            <button className="btn btn-primary btn-block btn-big" disabled={busy || problem.trim().length < 2} onClick={() => void start()}>
              {busy ? t("thinking") : t("get_help")}
            </button>
            {busy && <Spinner label={t("thinking")} />}
          </>
        )}

        {phase === "questions" && session && (
          <>
            <h2 className="section-title">{t("quick_questions")}</h2>
            {session.questions.map((q) => (
              <div key={q.id} className="question">
                <p className="question-text">{lang === "ta" ? q.text_ta || q.text_en : q.text_en}</p>
                <div className="options">
                  {q.options.map((o) => (
                    <button
                      key={o.value}
                      className={`btn option ${answers[q.id] === o.value ? "option-on" : ""}`}
                      onClick={() => setAnswers((a) => ({ ...a, [q.id]: o.value }))}
                      aria-pressed={answers[q.id] === o.value}
                    >
                      {lang === "ta" ? o.label_ta || o.label_en : o.label_en}
                    </button>
                  ))}
                </div>
              </div>
            ))}
            <button className="btn btn-primary btn-block btn-big" disabled={busy} onClick={() => void sendAnswers()}>
              {busy ? t("thinking") : t("continue")}
            </button>
            {busy && <Spinner label={t("thinking")} />}
          </>
        )}

        {phase === "steps" && session && step && (
          <>
            {position === 1 && (session.procedure.summary_en || session.procedure.low_confidence) && (
              <div className={`note ${session.procedure.low_confidence ? "note-warn" : "note-info"}`}>
                {session.procedure.low_confidence && <p>{t("low_confidence")}</p>}
                <p>{lang === "ta" ? session.procedure.summary_ta || session.procedure.summary_en : session.procedure.summary_en}</p>
                {!!session.procedure.likely_causes?.length && (
                  <p>
                    <strong>{t("likely_causes")}: </strong>
                    {session.procedure.likely_causes.map((c) => (lang === "ta" ? c.cause_ta || c.cause_en : c.cause_en)).join(" · ")}
                  </p>
                )}
              </div>
            )}
            <div className="progress" aria-label={t("step_of", { n: position, total })}>
              <div className="progress-bar" style={{ width: `${(position / total) * 100}%` }} />
            </div>
            <article className={`step step-${step.kind}`}>
              <div className="step-head">
                <span className="step-no">{t("step_of", { n: position, total })}</span>
                <span className={`chip chip-kind-${step.kind}`}>{t(`kind_${step.kind}` as "kind_check")}</span>
              </div>
              {step.authorised_only && (
                <p className="badge-danger">
                  <Icon name="shield" /> {t("authorised_only")}
                </p>
              )}
              <p className="step-action">{pick(step, "action", lang)}</p>
              {pick(step, "check", lang) && (
                <p>
                  <strong>{t("check")}: </strong>
                  {pick(step, "check", lang)}
                </p>
              )}
              {pick(step, "expected_result", lang) && (
                <p className="expected">
                  <strong>{t("expected")}: </strong>
                  {pick(step, "expected_result", lang)}
                </p>
              )}
              {step.tools.length > 0 && (
                <p className="muted">
                  <strong>{t("tools")}: </strong>
                  {step.tools.join(", ")}
                </p>
              )}
              {pick(step, "safety_note", lang) && (
                <p className="note note-warn">
                  <Icon name="alert" size={20} /> {pick(step, "safety_note", lang)}
                </p>
              )}
              {step.general && <p className="general">{t("general_suggestion")}</p>}
              <div className="step-tools">
                <button className="btn btn-ghost" onClick={readStep}>
                  <Icon name="volume" /> {t("read_aloud")}
                </button>
                {!step.injected && (
                  <button className="btn btn-ghost" onClick={() => setSheet("why")}>
                    <Icon name="help" /> {t("why_step")}
                  </button>
                )}
                {!step.injected && (
                  <button className="btn btn-ghost" onClick={() => void explain()}>
                    <Icon name="book" /> {t("explain")}
                  </button>
                )}
              </div>
            </article>
          </>
        )}

        {phase === "finish" && session && (
          <>
            <p className="note note-info">{t("procedure_done")}</p>
            <h2 className="big-question">{t("is_running")}</h2>
            <div className="answer-row">
              <button className="btn btn-ok" disabled={busy} onClick={() => void close(true)}>
                {t("yes_running")}
              </button>
              <button className="btn btn-notok" disabled={busy} onClick={() => void close(false)}>
                {t("no_still_down")}
              </button>
            </div>
          </>
        )}

        {phase === "done" && session && (
          <>
            {session.outcome === "refused" && (
              <div className="note note-danger">
                <h2>{t("refused_title")}</h2>
                <p>{lang === "ta" ? session.procedure.refuse_reason_ta : session.procedure.refuse_reason_en}</p>
              </div>
            )}
            {session.outcome === "failed" && (
              <div className="note note-danger">
                <h2>{t("failed_title")}</h2>
                <p>{t("failed_body")}</p>
              </div>
            )}
            {resultMsg && <p className="note note-warn">{resultMsg}</p>}
            {!feedbackSent && session.outcome !== "refused" && (
              <div className="feedback">
                <p>{t("helpful_q")}</p>
                <div className="answer-row">
                  <button className="btn btn-ghost" onClick={() => void feedback("helpful")}>
                    {t("helpful")}
                  </button>
                  <button className="btn btn-ghost" onClick={() => void feedback("not_helpful")}>
                    {t("not_helpful")}
                  </button>
                </div>
              </div>
            )}
            <button className="btn btn-primary btn-block" onClick={() => navigate("/", { replace: true })}>
              <Icon name="home" /> {t("home")}
            </button>
          </>
        )}
      </Page>

      {sheet === "why" && step && (
        <Sheet title={t("why_step")} onClose={() => setSheet("")}>
          {step.evidence.general ? (
            <p className="general">{t("general_suggestion")}</p>
          ) : (
            <>
              {step.evidence.fault_cards.map((ref) => (
                <p key={ref}>{t("evidence_card", { ref })}</p>
              ))}
              {step.evidence.logs_this_machine > 0 && (
                <p>
                  <strong>
                    {t("evidence_logs", { n: step.evidence.logs_this_machine, date: formatDate(step.evidence.last_date) })}
                  </strong>
                </p>
              )}
              <ul className="evidence">
                {step.evidence.items.map((i) => (
                  <li key={i.ref}>
                    <span className="mono">{i.ref}</span> · {i.machine_no} · {formatDate(i.when)}
                    {i.tier === 3 && <em> · {t("evidence_type")}</em>}
                    {i.kind === "tip" && <em> · {t("evidence_tip")}</em>}
                    {(i.kind === "doc" || i.kind === "alarm") && <em> · {t("evidence_doc")}</em>}
                    {i.tier === 5 && <em> · {t("evidence_unverified")}</em>}
                    <div className="muted">{evidenceText(i, lang)}</div>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Sheet>
      )}
      {sheet === "explain" && (
        <Sheet title={t("explain")} onClose={() => setSheet("")}>
          {explanation ? (
            <>
              <p className="explain-text">{lang === "ta" ? explanation.text_ta : explanation.text_en}</p>
              <button className="btn btn-ghost" onClick={() => speak(lang === "ta" ? explanation.text_ta : explanation.text_en, lang)}>
                <Icon name="volume" /> {t("read_aloud")}
              </button>
            </>
          ) : (
            <Spinner label={t("thinking")} />
          )}
        </Sheet>
      )}
      {sheet === "cant" && step && (
        <Sheet title={t("cant_do_title")} onClose={() => setSheet("")}>
          <p>{t("cant_do_body")}</p>
          <button className="btn btn-danger btn-block" onClick={() => { setSheet(""); void callSupervisor(); }}>
            <Icon name="phone" /> {t("call_supervisor")}
          </button>
          <button
            className="btn btn-ghost btn-block"
            onClick={() => {
              setSheet("");
              const idx = session!.steps.findIndex((s) => s.step_no === step.step_no);
              goTo(session!.steps[idx + 1]?.step_no ?? 0);
            }}
          >
            {t("skip_step")}
          </button>
        </Sheet>
      )}
      {sheet === "stop" && (
        <Sheet title={t("stop_title")} onClose={() => setSheet("")}>
          <p>{t("stop_body")}</p>
          <button className="btn btn-danger btn-block" onClick={() => { setSheet(""); void callSupervisor(); }}>
            <Icon name="phone" /> {t("call_supervisor")}
          </button>
          <button className="btn btn-ghost btn-block" onClick={() => { setSheet(""); setPhase("finish"); }}>
            {t("is_running")}
          </button>
        </Sheet>
      )}
      {supervisor && <SupervisorSheet summary={supervisor.summary} supervisors={supervisor.supervisors} onClose={() => setSupervisor(null)} />}
    </>
  );
}
