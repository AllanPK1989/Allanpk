// Push-to-talk recording with MediaRecorder (Opus/WebM on Android Chrome, MP4 on iOS).
import { useCallback, useRef, useState } from "react";

const MAX_SECONDS = 60;

function pickMime(): string {
  for (const type of ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg"]) {
    if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(type)) return type;
  }
  return "";
}

export type RecorderState = "idle" | "recording" | "denied" | "unsupported";

export function useRecorder(onDone: (blob: Blob) => void) {
  const [state, setState] = useState<RecorderState>(
    typeof MediaRecorder === "undefined" || !navigator.mediaDevices ? "unsupported" : "idle",
  );
  const [seconds, setSeconds] = useState(0);
  const recorder = useRef<MediaRecorder | null>(null);
  const timer = useRef<number | undefined>(undefined);
  const starting = useRef(false);
  const stopRequested = useRef(false);

  const stop = useCallback(() => {
    window.clearInterval(timer.current);
    if (starting.current) stopRequested.current = true; // released before the mic was ready
    if (recorder.current && recorder.current.state !== "inactive") recorder.current.stop();
  }, []);

  const start = useCallback(async () => {
    if (starting.current || (recorder.current && recorder.current.state === "recording")) return;
    starting.current = true;
    stopRequested.current = false;
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
    } catch {
      starting.current = false;
      setState("denied");
      return;
    }
    starting.current = false;
    if (stopRequested.current) {
      stream.getTracks().forEach((t) => t.stop());
      return;
    }
    const mime = pickMime();
    const rec = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
    const chunks: Blob[] = [];
    rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    rec.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());
      setState("idle");
      const blob = new Blob(chunks, { type: (rec.mimeType || "audio/webm").split(";")[0] });
      if (blob.size > 1000) onDone(blob);
    };
    recorder.current = rec;
    rec.start(250);
    setSeconds(0);
    setState("recording");
    const began = Date.now();
    timer.current = window.setInterval(() => {
      const s = Math.round((Date.now() - began) / 1000);
      setSeconds(s);
      if (s >= MAX_SECONDS) stop();
    }, 250);
  }, [onDone, stop]);

  return { state, seconds, start, stop };
}
