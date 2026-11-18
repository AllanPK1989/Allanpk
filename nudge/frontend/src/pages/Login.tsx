// PIN keypad: first-run setup and everyday unlock.
import { useEffect, useState } from "react";
import { api, errorText } from "../api";
import { Icon } from "../icons";

export function Login({ hasPin, demoPin, onDone }: { hasPin: boolean; demoPin: string | null; onDone: () => void }) {
  const [pin, setPin] = useState("");
  const [first, setFirst] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const setup = !hasPin;
  const len = setup ? 6 : 8;

  const submit = async (value: string) => {
    setBusy(true);
    setError("");
    try {
      if (setup) {
        if (first === null) { setFirst(value); setPin(""); setBusy(false); return; }
        if (first !== value) { setError("Those didn't match. Start again."); setFirst(null); setPin(""); setBusy(false); return; }
        await api.post("/api/auth/setup", { pin: value });
      } else await api.post("/api/auth/login", { pin: value });
      onDone();
    } catch (e) {
      setError(errorText(e));
      setPin("");
    } finally {
      setBusy(false);
    }
  };

  const press = (d: string) => {
    if (busy) return;
    setError("");
    setPin((p) => (p.length < len ? p + d : p));
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (/^\d$/.test(e.key)) press(e.key);
      else if (e.key === "Backspace") setPin((p) => p.slice(0, -1));
      else if (e.key === "Enter" && pin.length >= 4) submit(pin);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  return (
    <div className="login">
      <div className="box">
        <img src="/icon.svg" width={64} height={64} alt="" style={{ borderRadius: 16 }} />
        <h1 style={{ marginTop: 12 }}>{setup ? (first === null ? "Create a PIN" : "Enter it again") : "Welcome back"}</h1>
        <div className="muted" style={{ marginTop: 6 }}>{setup ? "4 to 6 digits. You'll use it to open Nudge." : "Enter your PIN"}</div>
        {demoPin && !setup && <div className="small" style={{ marginTop: 8 }}><span className="demo-pill">DEMO</span> PIN is {demoPin}</div>}
        <div className="pin-dots" aria-label={`${pin.length} digits entered`}>
          {Array.from({ length: Math.max(4, pin.length) }, (_, i) => <i key={i} className={i < pin.length ? "on" : ""} />)}
        </div>
        <div style={{ minHeight: 24, color: "var(--critical-ink)", fontWeight: 600 }} role="alert">{error}</div>
        <div className="keypad">
          {["1", "2", "3", "4", "5", "6", "7", "8", "9"].map((d) => <button key={d} onClick={() => press(d)}>{d}</button>)}
          <button onClick={() => setPin((p) => p.slice(0, -1))} aria-label="Delete"><Icon name="back" /></button>
          <button onClick={() => press("0")}>0</button>
          <button onClick={() => pin.length >= 4 && submit(pin)} aria-label="Continue" disabled={pin.length < 4}
            style={{ background: pin.length >= 4 ? "var(--accent)" : undefined, color: pin.length >= 4 ? "#fff" : undefined }}>
            <Icon name="arrow" />
          </button>
        </div>
      </div>
    </div>
  );
}
