import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api";
import type { User } from "../api";
import { useApp } from "../state";

const KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "", "0", "⌫"];

export default function Login() {
  const { t, login, lang, setLang } = useApp();
  const navigate = useNavigate();
  const location = useLocation();
  const [employeeId, setEmployeeId] = useState(localStorage.getItem("thunai-last-emp") ?? "");
  const [pin, setPin] = useState("");
  const [shared, setShared] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const press = (key: string) => {
    setError("");
    if (key === "⌫") setPin((p) => p.slice(0, -1));
    else if (key && pin.length < 4) setPin((p) => p + key);
  };

  const submit = async () => {
    if (!employeeId.trim() || pin.length !== 4) return;
    setBusy(true);
    try {
      const r = await api.post<{ token: string; user: User }>("/api/auth/login", {
        employee_id: employeeId.trim(),
        pin,
        shared_device: shared,
      });
      if (!shared) localStorage.setItem("thunai-last-emp", employeeId.trim());
      login(r.token, r.user, shared);
      const next = (location.state as { from?: string } | null)?.from ?? "/";
      navigate(next, { replace: true });
    } catch (e) {
      setPin("");
      setError(e instanceof ApiError && e.status === 423 ? t("locked") : e instanceof ApiError ? t("wrong_pin") : t("error_generic"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="login">
      <div className="login-head">
        <img src="/icon.svg" alt="" width={56} height={56} />
        <div>
          <h1>{t("app_name")}</h1>
          <p className="muted">{t("tagline")}</p>
        </div>
        <button className="lang-btn" onClick={() => setLang(lang === "en" ? "ta" : "en")}>
          {lang === "en" ? "தமிழ்" : "English"}
        </button>
      </div>
      <label className="field">
        <span>{t("employee_id")}</span>
        <input
          className="input input-big"
          value={employeeId}
          onChange={(e) => setEmployeeId(e.target.value.toUpperCase())}
          autoCapitalize="characters"
          autoComplete="username"
          inputMode="text"
        />
      </label>
      <div className="field">
        <span>{t("pin")}</span>
        <div className="pin-dots" aria-label={`${pin.length} of 4`}>
          {[0, 1, 2, 3].map((i) => (
            <span key={i} className={i < pin.length ? "dot dot-on" : "dot"} />
          ))}
        </div>
      </div>
      <div className="keypad">
        {KEYS.map((k, i) =>
          k ? (
            <button key={i} className="key" onClick={() => press(k)} aria-label={k === "⌫" ? "Delete" : k}>
              {k}
            </button>
          ) : (
            <span key={i} />
          ),
        )}
      </div>
      <label className="check-row">
        <input type="checkbox" checked={shared} onChange={(e) => setShared(e.target.checked)} />
        <span>{t("shared_device")}</span>
      </label>
      {error && (
        <p className="note note-danger" role="alert">
          {error}
        </p>
      )}
      <button className="btn btn-primary btn-block btn-big" disabled={busy || pin.length !== 4 || !employeeId} onClick={() => void submit()}>
        {t("login")}
      </button>
    </main>
  );
}
