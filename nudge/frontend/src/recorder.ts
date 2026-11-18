// Voice recording with MediaRecorder (Opus/WebM on Android and desktop Chrome, MP4 on iPhone),
// plus a live level meter so you can see it's listening.
import { useCallback, useEffect, useRef, useState } from "react";

const MAX_SECONDS = 90;

function pickMime(): string {
  for (const type of ["audio/webm;codecs=opus", "audio/webm", "audio/mp4", "audio/ogg"]) {
    if (typeof MediaRecorder !== "undefined" && MediaRecorder.isTypeSupported(type)) return type;
  }
  return "";
}

export type RecorderState = "idle" | "starting" | "recording" | "denied" | "unsupported";

export function useRecorder(onDone: (blob: Blob) => void) {
  const supported = typeof MediaRecorder !== "undefined" && !!navigator.mediaDevices?.getUserMedia;
  const [state, setState] = useState<RecorderState>(supported ? "idle" : "unsupported");
  const [seconds, setSeconds] = useState(0);
  const [levels, setLevels] = useState<number[]>(() => Array(16).fill(0.08));
  const recorder = useRef<MediaRecorder | null>(null);
  const timer = useRef<number | undefined>(undefined);
  const raf = useRef<number | undefined>(undefined);
  const audioCtx = useRef<AudioContext | null>(null);
  const cancelled = useRef(false);
  const stopRequested = useRef(false);
  const doneRef = useRef(onDone);
  doneRef.current = onDone;

  const cleanupMeter = () => {
    if (raf.current) cancelAnimationFrame(raf.current);
    audioCtx.current?.close().catch(() => {});
    audioCtx.current = null;
  };

  const stop = useCallback(() => {
    window.clearInterval(timer.current);
    stopRequested.current = true;
    if (recorder.current && recorder.current.state !== "inactive") recorder.current.stop();
  }, []);

  const cancel = useCallback(() => {
    cancelled.current = true;
    stop();
  }, [stop]);

  const start = useCallback(async () => {
    if (!supported || state === "recording" || state === "starting") return;
    cancelled.current = false;
    stopRequested.current = false;
    setState("starting");
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
    } catch {
      setState("denied");
      return;
    }
    if (stopRequested.current) {
      stream.getTracks().forEach((t) => t.stop());
      setState("idle");
      return;
    }
    const mime = pickMime();
    const rec = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
    const chunks: Blob[] = [];
    rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    rec.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());
      cleanupMeter();
      setState("idle");
      const blob = new Blob(chunks, { type: (rec.mimeType || "audio/webm").split(";")[0] });
      if (!cancelled.current && blob.size > 1500) doneRef.current(blob);
    };
    recorder.current = rec;
    rec.start(250);

    try {
      const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = new Ctx();
      audioCtx.current = ctx;
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      ctx.createMediaStreamSource(stream).connect(analyser);
      const data = new Uint8Array(analyser.frequencyBinCount);
      const tick = () => {
        analyser.getByteFrequencyData(data);
        const bands = 16;
        const step = Math.floor(data.length / bands / 2) || 1;
        const next = Array.from({ length: bands }, (_, i) => {
          let sum = 0;
          for (let j = 0; j < step; j++) sum += data[i * step + j];
          return Math.max(0.08, Math.min(1, sum / step / 160));
        });
        setLevels(next);
        raf.current = requestAnimationFrame(tick);
      };
      tick();
    } catch {
      /* meter is optional */
    }

    setSeconds(0);
    setState("recording");
    const began = Date.now();
    timer.current = window.setInterval(() => {
      const s = Math.floor((Date.now() - began) / 1000);
      setSeconds(s);
      if (s >= MAX_SECONDS) stop();
    }, 250);
  }, [state, stop, supported]);

  useEffect(() => () => {
    window.clearInterval(timer.current);
    cleanupMeter();
    if (recorder.current && recorder.current.state !== "inactive") {
      cancelled.current = true;
      recorder.current.stop();
    }
  }, []);

  return { state, seconds, levels, start, stop, cancel, maxSeconds: MAX_SECONDS };
}
