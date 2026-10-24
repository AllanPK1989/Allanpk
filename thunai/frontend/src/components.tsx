import { useCallback, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { api, OfflineError } from "./api";
import type { Log, PartInfo, Supervisor } from "./api";
import { useRecorder } from "./recorder";
import { useApp } from "./state";

// ---- icons (inline SVG, no icon font to download) -------------------------------------------
const PATHS: Record<string, string> = {
  mic: "M12 2a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3zM19 10v1a7 7 0 0 1-14 0v-1M12 18v4M8 22h8",
  qr: "M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h3v3h-3zM18 18h3v3h-3zM14 20h2M20 14v2",
  search: "M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.3-4.3",
  help: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3M12 17h.01",
  log: "M9 2h6v4H9zM16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2M8 12h8M8 16h5",
  list: "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01",
  check: "M20 6 9 17l-5-5",
  x: "M18 6 6 18M6 6l12 12",
  alert: "M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0zM12 9v4M12 17h.01",
  phone: "M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z",
  volume: "M11 5 6 9H2v6h4l5 4V5zM15.5 8.5a5 5 0 0 1 0 7M19 5a10 10 0 0 1 0 14",
  back: "M19 12H5M12 19l-7-7 7-7",
  camera: "M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2zM12 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
  home: "M3 10.5 12 3l9 7.5V21H3zM9 21v-6h6v6",
  shield: "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z",
  settings: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z",
  download: "M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3",
  logout: "M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9",
  wrench: "M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.8-3.8a6 6 0 0 1-7.9 7.9l-6.9 6.9a2.1 2.1 0 0 1-3-3l6.9-6.9a6 6 0 0 1 7.9-7.9z",
  plus: "M12 5v14M5 12h14",
  chart: "M3 3v18h18M7 15l4-4 3 3 5-6",
  book: "M4 19.5A2.5 2.5 0 0 1 6.5 17H20V2H6.5A2.5 2.5 0 0 0 4 4.5v15zM4 19.5A2.5 2.5 0 0 0 6.5 22H20v-5",
  box: "M21 16V8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4a2 2 0 0 0 1-1.7zM3.3 7 12 12l8.7-5M12 22V12",
  calendar: "M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z",
  bell: "M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0",
  users: "M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM23 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8",
  link: "M10 13a5 5 0 0 0 7.5.5l3-3a5 5 0 0 0-7-7l-1.7 1.7M14 11a5 5 0 0 0-7.5-.5l-3 3a5 5 0 0 0 7 7l1.7-1.7",
  wifiOff: "M2 2l20 20M8.5 16.4a5 5 0 0 1 7 0M5 12.6a10 10 0 0 1 5.2-2.7M19 12.6a10 10 0 0 0-2.4-1.7M1.4 9a15 15 0 0 1 4.4-2.7M22.6 9A15 15 0 0 0 10.7 5M12 20h.01",
};

export function Icon({ name, size = 24 }: { name: keyof typeof PATHS | string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.2}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={PATHS[name] ?? PATHS.help} />
    </svg>
  );
}

// ---- layout ---------------------------------------------------------------------------------
export function Header({ title, back = true, right }: { title: string; back?: boolean; right?: ReactNode }) {
  const { lang, setLang, online, meta, t } = useApp();
  const navigate = useNavigate();
  return (
    <header className="topbar">
      {back ? (
        <button className="icon-btn" onClick={() => navigate(-1)} aria-label={t("back")}>
          <Icon name="back" />
        </button>
      ) : (
        <span className="brand-dot" aria-hidden="true" />
      )}
      <h1 className="topbar-title">{title}</h1>
      {!online && (
        <span className="pill pill-warn" title={t("offline")}>
          <Icon name="wifiOff" size={16} /> {t("offline")}
        </span>
      )}
      {meta?.demo_ai && <span className="pill pill-demo" title={t("demo_ai_note")}>Demo</span>}
      {right}
      <button className="lang-btn" onClick={() => setLang(lang === "en" ? "ta" : "en")} aria-label="Change language / மொழி மாற்று">
        {lang === "en" ? "தமிழ்" : "EN"}
      </button>
    </header>
  );
}

export function Page({ children, footer }: { children: ReactNode; footer?: ReactNode }) {
  return (
    <>
      <main className="page">{children}</main>
      {footer && <div className="footer-bar">{footer}</div>}
    </>
  );
}

export function OfflineBanner() {
  const { online, queueCount, sync, t } = useApp();
  if (online && !queueCount) return null;
  return (
    <div className={`banner ${online ? "banner-info" : "banner-warn"}`} role="status">
      <span>{online ? t("queued", { n: queueCount }) : t("offline_banner")}</span>
      {online && queueCount > 0 && (
        <button className="btn btn-small" onClick={() => void sync()}>
          {t("sync_now")}
        </button>
      )}
      {!online && queueCount > 0 && <strong>{t("queued", { n: queueCount })}</strong>}
    </div>
  );
}

export function Toast() {
  const { toastText } = useApp();
  if (!toastText) return null;
  return (
    <div className="toast" role="status" aria-live="polite">
      {toastText}
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="spinner-wrap" role="status">
      <span className="spinner" aria-hidden="true" />
      {label && <span>{label}</span>}
    </div>
  );
}

export function Sheet({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const { t } = useApp();
  return (
    <div className="sheet-backdrop" onClick={onClose}>
      <div className="sheet" role="dialog" aria-modal="true" aria-label={title} onClick={(e) => e.stopPropagation()}>
        <div className="sheet-head">
          <h2>{title}</h2>
          <button className="icon-btn" onClick={onClose} aria-label={t("close")}>
            <Icon name="x" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function StatusChip({ status }: { status: Log["status"] }) {
  const { t } = useApp();
  return <span className={`chip chip-${status}`}>{t(`status_${status}` as "status_open")}</span>;
}

export function ErrorNote({ error }: { error: unknown }) {
  const { t } = useApp();
  if (!error) return null;
  const message = error instanceof OfflineError ? t("offline_banner") : error instanceof Error ? error.message : t("error_generic");
  return (
    <p className="note note-danger" role="alert">
      {message}
    </p>
  );
}

// ---- voice ----------------------------------------------------------------------------------
export interface VoiceResult {
  text: string;
  mediaId: number | null;
  blob: Blob;
}

/**
 * Push-to-talk: hold to record and release to stop. A short tap starts a hands-free recording
 * that stops on the next tap (easier with thick gloves). The audio is sent for transcription;
 * offline, the recording is returned without text so the caller can queue it.
 */
export function MicButton({ onResult, language, compact = false }: {
  onResult: (r: VoiceResult) => void;
  language: string;
  compact?: boolean;
}) {
  const { t, toast } = useApp();
  const [busy, setBusy] = useState(false);
  const [tapMode, setTapMode] = useState(false);
  const pressedAt = useRef(0);

  const handleBlob = useCallback(
    async (blob: Blob) => {
      setBusy(true);
      const form = new FormData();
      form.append("file", blob, blob.type.includes("mp4") ? "voice.m4a" : "voice.webm");
      try {
        const r = await api.upload<{ media_id: number; transcript: string; status: string }>(
          `/api/media/audio?language=${language}`,
          form,
        );
        if (!r.transcript) toast(t("stt_failed"));
        onResult({ text: r.transcript, mediaId: r.media_id, blob });
      } catch (e) {
        if (!(e instanceof OfflineError)) toast(t("stt_failed"));
        onResult({ text: "", mediaId: null, blob });
      } finally {
        setBusy(false);
      }
    },
    [language, onResult, t, toast],
  );

  const { state, seconds, start, stop } = useRecorder(handleBlob);
  const recording = state === "recording";

  useEffect(() => {
    if (state === "denied") toast(t("mic_denied"));
  }, [state, t, toast]);

  useEffect(() => {
    if (!recording) setTapMode(false); // also covers the 60-second auto stop
  }, [recording]);

  if (state === "unsupported") return null;

  const down = (e: React.PointerEvent) => {
    e.preventDefault();
    if (tapMode) {
      setTapMode(false);
      stop();
      return;
    }
    pressedAt.current = Date.now();
    void start();
  };
  const up = () => {
    if (!pressedAt.current) return;
    const held = Date.now() - pressedAt.current;
    pressedAt.current = 0;
    if (held < 400) setTapMode(true); // short tap: keep recording until the next tap
    else stop();
  };

  return (
    <div className={`mic-wrap ${compact ? "mic-compact" : ""}`}>
      <button
        type="button"
        className={`mic-btn ${recording ? "mic-on" : ""}`}
        onPointerDown={down}
        onPointerUp={up}
        onPointerCancel={up}
        onContextMenu={(e) => e.preventDefault()}
        disabled={busy}
        aria-label={t("hold_to_talk")}
      >
        <Icon name="mic" size={compact ? 30 : 44} />
      </button>
      <span className="mic-label">
        {busy ? t("transcribing") : recording ? `${seconds}s · ${tapMode ? t("tap_to_stop") : t("release_to_stop")}` : t("hold_to_talk")}
      </span>
    </div>
  );
}

// ---- supervisor -----------------------------------------------------------------------------
export function SupervisorSheet({ summary, supervisors, onClose }: {
  summary: string;
  supervisors: Supervisor[];
  onClose: () => void;
}) {
  const { t, toast } = useApp();
  const share = async () => {
    if (navigator.share) {
      try {
        await navigator.share({ title: "Thunai", text: summary });
        return;
      } catch {
        /* cancelled */
      }
    }
    await navigator.clipboard?.writeText(summary);
    toast(t("copied"));
  };
  return (
    <Sheet title={t("call_supervisor")} onClose={onClose}>
      {supervisors.map((s) => (
        <div className="row-between card-lite" key={s.name}>
          <div>
            <strong>{s.name}</strong>
            <div className="muted">{s.zone}</div>
          </div>
          {s.phone && (
            <a className="btn btn-primary" href={`tel:${s.phone}`}>
              <Icon name="phone" /> {t("call")}
            </a>
          )}
        </div>
      ))}
      <h3>{t("supervisor_summary")}</h3>
      <pre className="summary">{summary}</pre>
      <button className="btn btn-primary btn-block" onClick={() => void share()}>
        {t("share")}
      </button>
    </Sheet>
  );
}

// Times are shown in plant time whatever the phone's own setting.
const PLANT_TZ = "Asia/Kolkata";

export function formatDate(iso: string | null | undefined, withTime = false): string {
  if (!iso) return "";
  const d = new Date(iso.length === 10 ? `${iso}T12:00:00+05:30` : iso);
  return d.toLocaleString("en-IN", {
    timeZone: PLANT_TZ,
    day: "numeric",
    month: "short",
    year: "numeric",
    ...(withTime ? { hour: "2-digit", minute: "2-digit" } : {}),
  });
}

/** "14:05" in plant time. */
export function formatTime(iso: string | null | undefined): string {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString("en-IN", { timeZone: PLANT_TZ, hour: "2-digit", minute: "2-digit", hour12: false });
}

/** "2 EA in stock", "Out of stock" or "Stock not known". */
export function stockText(part: PartInfo, t: ReturnType<typeof useApp>["t"]): string {
  if (part.stock_qty === null) return t("stock_unknown");
  if (part.stock_qty <= 0) return t("out_of_stock");
  return t("in_stock", { n: part.stock_qty, unit: part.unit }).replace(/\s{2,}/g, " ");
}

/** A catalogue part with stock as the stores system last reported it. */
export function PartChip({ part }: { part: PartInfo }) {
  const { t } = useApp();
  const out = part.stock_qty !== null && part.stock_qty <= 0;
  const stock = stockText(part, t) + (!out && part.stock_qty !== null && part.location ? ` · ${part.location}` : "");
  return (
    <div className={`part-chip ${out ? "part-out" : part.low ? "part-low" : ""}`}>
      <Icon name="box" size={18} />
      <div>
        <strong className="mono">{part.part_no}</strong> {part.description}
        <div className="small">
          {stock}
          {part.low && !out && ` · ${t("low_stock")}`}
          {part.stock_at && <span className="muted"> · {t("as_of", { date: formatDate(part.stock_at) })}</span>}
        </div>
      </div>
    </div>
  );
}
