import { type FormEvent, useState } from "react";
import { api } from "../api";

export default function Login({ onLogin }: { onLogin: () => void }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.post("/auth/login", { password });
      onLogin();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="login">
      <form onSubmit={submit} className="login-card">
        <img src="/icon.svg" alt="" width="48" height="48" />
        <h1>Investment Analyst</h1>
        <p className="muted">Your private markets, portfolio and AI adviser.</p>
        <label>
          Password
          <input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} autoFocus required />
        </label>
        {error && <div className="error-note">{error}</div>}
        <button className="btn primary" disabled={busy || !password}>{busy ? "Signing in…" : "Sign in"}</button>
      </form>
    </div>
  );
}
