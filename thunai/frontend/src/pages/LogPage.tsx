import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, ApiError, OfflineError } from "../api";
import type { Log, TextField } from "../api";
import type { Lang } from "../i18n";
import { ErrorNote, Header, Icon, MicButton, OfflineBanner, Page, Sheet, Spinner, StatusChip, formatDate } from "../components";
import type { VoiceResult } from "../components";
import { newId, queueLog } from "../offline";
import { speak } from "../speak";
import { useApp } from "../state";

const FIELDS: TextField[] = ["issue", "root_cause", "corrective_action"];
const REQUIRED: TextField[] = ["issue", "corrective_action"];

interface FieldState {
  value: string;
  own: boolean; // the technician's own words (typed, spoken or confirmed)
  ai: boolean;
  unsure: boolean;
  en: string;
  ta: string;
}

interface Part {
  description: string;
  part_no: string;
  qty: number;
}

interface Extraction {
  ok: boolean;
  issue: { original: string; en: string; ta: string; unsure: boolean };
  root_cause: { original: string; en: string; ta: string; unsure: boolean };
  corrective_action: { original: string; en: string; ta: string; unsure: boolean };
  parts_replaced: Part[];
  downtime_min: number;
  alarm_code: string;
  missing_question_en: string;
  missing_question_ta: string;
}

const empty = (): FieldState => ({ value: "", own: false, ai: false, unsure: false, en: "", ta: "" });

function fromLog(log: Log, lang: Lang): Record<TextField, FieldState> {
  const out = {} as Record<TextField, FieldState>;
  for (const f of FIELDS) {
    const x = log.texts[f];
    const translated = lang === "ta" ? x.ta || x.en : x.en || x.ta;
    out[f] = { value: x.original || translated, own: !!x.original, ai: x.ai_filled, unsure: x.unsure, en: x.en, ta: x.ta };
  }
  return out;
}

function toLocalInput(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

const fromLocalInput = (v: string) => (v ? new Date(v).toISOString() : null);

export default function LogPage() {
  const { id, no } = useParams();
  const isNew = !id;
  const { t, lang, user, toast, sessionFinished, sync } = useApp();
  const navigate = useNavigate();
  const [log, setLog] = useState<Log | null>(null);
  const [fields, setFields] = useState<Record<TextField, FieldState>>({ issue: empty(), root_cause: empty(), corrective_action: empty() });
  const [startAt, setStartAt] = useState(isNew ? toLocalInput(new Date().toISOString()) : "");
  const [endAt, setEndAt] = useState("");
  const [manualDowntime, setManualDowntime] = useState("");
  const [alarm, setAlarm] = useState("");
  const [parts, setParts] = useState<Part[]>([]);
  const [mediaIds, setMediaIds] = useState<number[]>([]);
  const [pendingAudio, setPendingAudio] = useState<Blob | null>(null);
  const [source, setSource] = useState<"text" | "voice">("text");
  const [question, setQuestion] = useState("");
  const [openLog, setOpenLog] = useState<Log | null>(null);
  const [busy, setBusy] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [missing, setMissing] = useState<TextField[]>([]);
  const [rejecting, setRejecting] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [clientUuid] = useState(newId);

  const machineNo = (isNew ? no : log?.machine_no) ?? "";

  useEffect(() => {
    if (isNew) {
      api
        .get<{ log: Log | null }>(`/api/machines/${encodeURIComponent(no ?? "")}/open-log`)
        .then((r) => setOpenLog(r.log))
        .catch(() => {});
      return;
    }
    api
      .get<Log>(`/api/logs/${id}`)
      .then((l) => {
        setLog(l);
        setFields(fromLog(l, lang));
        setStartAt(toLocalInput(l.start_at));
        setEndAt(toLocalInput(l.end_at));
        setManualDowntime(l.downtime_min != null && !(l.start_at && l.end_at) ? String(l.downtime_min) : "");
        setAlarm(l.alarm_code);
        setParts(l.parts ?? []);
      })
      .catch(setError);
  }, [id, no, isNew]);

  const [forceEdit, setForceEdit] = useState(false);
  const editable = useMemo(() => {
    if (isNew || forceEdit) return true;
    if (!log || !user) return false;
    return ["draft", "open"].includes(log.status) || log.needs_confirmation;
  }, [isNew, forceEdit, log, user]);

  const downtime = useMemo(() => {
    if (startAt && endAt) {
      const m = Math.round((new Date(endAt).getTime() - new Date(startAt).getTime()) / 60000);
      return m >= 0 ? m : null;
    }
    return manualDowntime ? Number(manualDowntime) : null;
  }, [startAt, endAt, manualDowntime]);

  const setField = (f: TextField, value: string) =>
    setFields((s) => ({ ...s, [f]: { ...s[f], value, own: true, ai: false, unsure: false } }));

  const applyExtraction = (x: Extraction) => {
    setFields((s) => {
      const next = { ...s };
      for (const f of FIELDS) {
        // Never overwrite what the technician typed or confirmed.
        if (s[f].value && s[f].own && !s[f].ai) continue;
        const v = x[f];
        const value = v.original || (lang === "ta" ? v.ta || v.en : v.en || v.ta);
        if (!value) continue;
        next[f] = { value, own: !!v.original, ai: true, unsure: v.unsure, en: v.en, ta: v.ta };
      }
      return next;
    });
    if (x.parts_replaced.length && !parts.length) setParts(x.parts_replaced.map((p) => ({ ...p, qty: p.qty || 1 })));
    if (x.downtime_min >= 0 && !endAt) setManualDowntime(String(x.downtime_min));
    if (x.alarm_code && !alarm) setAlarm(x.alarm_code);
    const q = lang === "ta" ? x.missing_question_ta || x.missing_question_en : x.missing_question_en;
    setQuestion(q);
    if (q) speak(q, lang);
  };

  const onVoice = useCallback(
    async (r: VoiceResult) => {
      setSource("voice");
      if (r.mediaId) setMediaIds((ids) => [...ids, r.mediaId as number]);
      if (!r.text) {
        if (!r.mediaId) setPendingAudio(r.blob); // offline: send the recording with the queued log
        return;
      }
      setExtracting(true);
      try {
        const x = await api.post<Extraction>("/api/logs/extract", { machine_no: machineNo, transcript: r.text });
        if (x.ok) applyExtraction(x);
        else setField("issue", fields.issue.value ? `${fields.issue.value} ${r.text}` : r.text);
      } catch (e) {
        setError(e);
      } finally {
        setExtracting(false);
      }
    },
    [machineNo, fields, lang, parts, endAt, alarm],
  );

  const textBody = (f: TextField) => {
    const s = fields[f];
    if (s.own) return { original: s.value, en: s.ai ? s.en : null, ta: s.ai ? s.ta : null, ai_filled: s.ai, unsure: s.unsure };
    if (s.ai) return { original: "", en: s.en || s.value, ta: s.ta, ai_filled: true, unsure: s.unsure };
    return { original: s.value };
  };

  const save = async (mode: "submit" | "down" | "draft") => {
    const submit = mode !== "draft";
    if (submit) {
      const miss = REQUIRED.filter((f) => !fields[f].value.trim());
      setMissing(miss);
      if (miss.length && !(isNew && pendingAudio)) return;
    }
    setBusy(true);
    setError(null);
    const body = {
      issue: textBody("issue"),
      root_cause: textBody("root_cause"),
      corrective_action: textBody("corrective_action"),
      start_at: fromLocalInput(startAt),
      end_at: fromLocalInput(endAt),
      downtime_min: startAt && endAt ? null : manualDowntime ? Number(manualDowntime) : null,
      alarm_code: alarm,
      parts: parts.filter((p) => p.description.trim()),
      media_ids: mediaIds,
      submit,
      still_down: mode === "down",
    };
    try {
      if (isNew && pendingAudio) {
        // Recorded offline: send with the recording so the server transcribes it.
        throw new OfflineError("recorded offline");
      }
      if (isNew) {
        const created = await api.post<Log>("/api/logs", { ...body, machine_no: machineNo, source, client_uuid: clientUuid });
        toast(submit ? t("submitted") : t("saved"));
        if (submit) sessionFinished();
        navigate(submit ? `/m/${encodeURIComponent(machineNo)}` : `/log/${created.id}`, { replace: true });
      } else {
        const updated = await api.patch<Log>(`/api/logs/${id}`, body);
        toast(submit ? t("submitted") : t("saved"));
        if (submit) {
          sessionFinished();
          navigate(`/m/${encodeURIComponent(updated.machine_no)}`, { replace: true });
        } else setLog(updated);
      }
    } catch (e) {
      if (e instanceof OfflineError && isNew) {
        await queueLog({
          payload: { ...body, machine_no: machineNo, source, client_uuid: clientUuid },
          audio: pendingAudio ?? undefined,
          language: lang,
        });
        toast(t("saved_offline"));
        void sync();
        navigate("/", { replace: true });
      } else if (e instanceof ApiError && e.status === 422) {
        const detail = e.detail as { missing?: TextField[] } | undefined;
        setMissing(detail?.missing ?? []);
        setError(e);
      } else setError(e);
    } finally {
      setBusy(false);
    }
  };

  const verify = async () => {
    try {
      setLog(await api.post<Log>(`/api/logs/${id}/verify`));
      toast(t("status_verified"));
    } catch (e) {
      setError(e);
    }
  };

  const reject = async () => {
    try {
      setLog(await api.post<Log>(`/api/logs/${id}/reject`, { reason: rejectReason }));
      setRejecting(false);
    } catch (e) {
      setError(e);
    }
  };

  const title = isNew ? `${t("new_log")} · ${machineNo.toUpperCase()}` : log ? log.log_no : t("loading");

  if (!isNew && !log && !error) {
    return (
      <>
        <Header title={title} />
        <Page>
          <Spinner label={t("loading")} />
        </Page>
      </>
    );
  }

  // ---- read-only view ----------------------------------------------------------------------
  if (!editable && log) {
    const canReview = user && user.role !== "technician" && ["closed", "open"].includes(log.status);
    const canEdit = user && user.role !== "technician" && log.status !== "rejected";
    return (
      <>
        <Header
          title={title}
          right={
            canEdit ? (
              <button className="icon-btn" onClick={() => setForceEdit(true)} aria-label={t("edit")}>
                <Icon name="log" />
              </button>
            ) : undefined
          }
        />
        <Page
          footer={
            canReview ? (
              <div className="answer-row">
                <button className="btn btn-ok" onClick={() => void verify()}>
                  <Icon name="check" /> {t("verify")}
                </button>
                <button className="btn btn-notok" onClick={() => setRejecting(true)}>
                  <Icon name="x" /> {t("reject")}
                </button>
              </div>
            ) : undefined
          }
        >
          <ErrorNote error={error} />
          <LogSummary log={log} lang={lang} />
        </Page>
        {rejecting && (
          <Sheet title={t("reject_reason")} onClose={() => setRejecting(false)}>
            <textarea className="input textarea" rows={3} value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} />
            <button className="btn btn-notok btn-block" disabled={rejectReason.trim().length < 2} onClick={() => void reject()}>
              {t("reject")}
            </button>
          </Sheet>
        )}
      </>
    );
  }

  // ---- form --------------------------------------------------------------------------------
  return (
    <>
      <Header title={title} />
      <OfflineBanner />
      <Page
        footer={
          <div className="footer-stack">
            <button className="btn btn-primary btn-block btn-big" disabled={busy} onClick={() => void save("submit")}>
              <Icon name="check" /> {t("submit")}
            </button>
            <div className="answer-row btn-small-row">
              <button className="btn btn-neutral" disabled={busy} onClick={() => void save("down")}>
                {t("submit_down")}
              </button>
              <button className="btn btn-ghost" disabled={busy} onClick={() => void save("draft")}>
                {t("save_draft")}
              </button>
            </div>
          </div>
        }
      >
        <ErrorNote error={error} />
        {log && (
          <p className="muted">
            {log.machine_no} · {log.machine_name} · {t("shift")} {log.shift} · {formatDate(log.reported_at, true)}
          </p>
        )}
        <section className="voice-box">
          <p className="field-title">{t("speak_log")}</p>
          <MicButton onResult={(r) => void onVoice(r)} language={lang} />
          {extracting && <Spinner label={t("thinking")} />}
          {pendingAudio && <p className="note note-info">{t("saved_offline")}</p>}
        </section>
        {question && (
          <p className="note note-question">
            <strong>{t("question_from_ai")}: </strong>
            {question}
          </p>
        )}
        {FIELDS.map((f) => {
          const s = fields[f];
          const isMissing = missing.includes(f);
          return (
            <label key={f} className={`field ${s.ai ? (s.unsure ? "field-unsure" : "field-ai") : ""} ${isMissing ? "field-missing" : ""}`}>
              <span className="field-title">
                {t(f)}
                {REQUIRED.includes(f) && <em className="req"> · {t("required")}</em>}
              </span>
              <textarea className="input textarea" rows={2} value={s.value} onChange={(e) => setField(f, e.target.value)} />
              {s.ai && <small className="ai-flag">{s.unsure ? t("ai_unsure") : t("ai_check")}</small>}
            </label>
          );
        })}
        <div className="grid-2">
          <label className="field">
            <span>{t("start_time")}</span>
            <input className="input" type="datetime-local" value={startAt} onChange={(e) => setStartAt(e.target.value)} />
          </label>
          <label className="field">
            <span>{t("end_time")}</span>
            <input className="input" type="datetime-local" value={endAt} onChange={(e) => setEndAt(e.target.value)} />
          </label>
        </div>
        <label className="field">
          <span>
            {t("downtime")} ({t("minutes")})
          </span>
          {startAt && endAt ? (
            <output className="input output">{downtime ?? "–"}</output>
          ) : (
            <input className="input" inputMode="numeric" value={manualDowntime} onChange={(e) => setManualDowntime(e.target.value.replace(/\D/g, ""))} />
          )}
        </label>
        <label className="field">
          <span>{t("alarm_code")}</span>
          <input className="input" value={alarm} onChange={(e) => setAlarm(e.target.value)} />
        </label>
        <div className="field">
          <span className="field-title">{t("parts")}</span>
          {parts.map((p, i) => (
            <div key={i} className="part-row">
              <input
                className="input"
                placeholder={t("part_name")}
                value={p.description}
                onChange={(e) => setParts((ps) => ps.map((x, j) => (j === i ? { ...x, description: e.target.value } : x)))}
              />
              <input
                className="input qty"
                inputMode="decimal"
                aria-label={t("qty")}
                value={p.qty}
                onChange={(e) => setParts((ps) => ps.map((x, j) => (j === i ? { ...x, qty: Number(e.target.value) || 1 } : x)))}
              />
              <button className="icon-btn" onClick={() => setParts((ps) => ps.filter((_, j) => j !== i))} aria-label="Remove">
                <Icon name="x" />
              </button>
            </div>
          ))}
          <button className="btn btn-ghost" onClick={() => setParts((ps) => [...ps, { description: "", part_no: "", qty: 1 }])}>
            <Icon name="plus" /> {t("add_part")}
          </button>
        </div>
      </Page>
      {openLog && (
        <Sheet title={t("open_issues")} onClose={() => setOpenLog(null)}>
          <p>{t("open_log_exists", { no: openLog.log_no })}</p>
          <p className="muted">{openLog.texts.issue.original || openLog.texts.issue.en}</p>
          <button className="btn btn-primary btn-block" onClick={() => navigate(`/log/${openLog.id}`, { replace: true })}>
            {t("add_to_open")}
          </button>
          <button className="btn btn-ghost btn-block" onClick={() => setOpenLog(null)}>
            {t("create_new")}
          </button>
        </Sheet>
      )}
    </>
  );
}

function LogSummary({ log, lang }: { log: Log; lang: Lang }) {
  const { t } = useApp();
  return (
    <div className="log-view">
      <div className="row-between">
        <div>
          <strong>{log.machine_no}</strong> · {log.machine_name}
          <div className="muted">
            {formatDate(log.reported_at, true)} · {t("shift")} {log.shift} · {log.technician_name}
          </div>
        </div>
        <StatusChip status={log.status} />
      </div>
      {FIELDS.map((f) => {
        const x = log.texts[f];
        const shown = lang === "ta" ? x.ta || x.en || x.original : x.en || x.ta || x.original;
        return (
          <div key={f} className="kv">
            <span className="kv-k">{t(f)}</span>
            <span className="kv-v">{shown || "–"}</span>
            {x.original && x.original !== shown && (
              <span className="muted small">
                {t("original_words")}: “{x.original}”
              </span>
            )}
          </div>
        );
      })}
      <div className="kv">
        <span className="kv-k">{t("downtime")}</span>
        <span className="kv-v">{log.downtime_min != null ? `${log.downtime_min} ${t("minutes")}` : "–"}</span>
      </div>
      {log.alarm_code && (
        <div className="kv">
          <span className="kv-k">{t("alarm_code")}</span>
          <span className="kv-v">{log.alarm_code}</span>
        </div>
      )}
      {!!log.parts?.length && (
        <div className="kv">
          <span className="kv-k">{t("parts")}</span>
          <span className="kv-v">{log.parts.map((p) => `${p.description} × ${p.qty}`).join(", ")}</span>
        </div>
      )}
      {log.classification && (
        <p className="muted small">
          {log.classification.symptom_category} · {log.classification.component_name} · {log.classification.failure_mode}
        </p>
      )}
      {log.verified_by && (
        <p className="muted small">
          {t(`status_${log.status}` as "status_verified")}: {log.verified_by}
          {log.reject_reason ? ` · ${log.reject_reason}` : ""}
        </p>
      )}
    </div>
  );
}
