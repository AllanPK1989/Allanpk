import { useEffect, useState } from "react";
import { api } from "../api";
import { Badge, Card, ErrorNote, Spinner } from "../components";
import { when } from "../format";
import { currentSubscription, disablePush, enablePush, pushSupported } from "../push";
import type { Settings, Status } from "../types";

export default function SettingsPage({ status, onLogout }: { status: Status | null; onLogout: () => void }) {
  const [s, setS] = useState<Settings | null>(null);
  const [saved, setSaved] = useState("");
  const [err, setErr] = useState<unknown>();
  const [pushOn, setPushOn] = useState(false);
  const [pushMsg, setPushMsg] = useState("");
  useEffect(() => {
    api.get<Settings>("/settings").then(setS).catch(setErr);
    currentSubscription().then((sub) => setPushOn(!!sub)).catch(() => {});
  }, []);
  if (!s) return <div className="page">{err ? <ErrorNote error={err} /> : <Spinner />}</div>;

  const save = async (patch: Partial<Settings>) => {
    setErr(undefined);
    try {
      setS(await api.put<Settings>("/settings", patch));
      setSaved("Saved");
      setTimeout(() => setSaved(""), 1500);
    } catch (e) {
      setErr(e);
    }
  };
  const togglePush = async () => {
    setPushMsg("");
    try {
      if (pushOn) {
        await disablePush();
        setPushOn(false);
        setPushMsg("Push turned off on this device.");
      } else {
        await enablePush();
        setPushOn(true);
        setPushMsg("Push is on for this device.");
      }
    } catch (e) {
      setPushMsg((e as Error).message);
    }
  };
  const testPush = async () => {
    const r = await api.post<{ sent: number }>("/push/test");
    setPushMsg(r.sent ? `Sent to ${r.sent} device(s).` : "No devices subscribed yet.");
  };
  const num = (v: string) => (v === "" ? null : Number(v));

  return (
    <div className="page narrow">
      <div className="page-head">
        <h1>Settings</h1>
        {saved && <Badge tone="good">{saved}</Badge>}
      </div>
      <ErrorNote error={err} />
      <Card title="Your investor profile" actions={<span className="muted small">The adviser reads this</span>}>
        <div className="form">
          <div className="row">
            <label>Risk profile
              <select value={s.risk_profile} onChange={(e) => save({ risk_profile: e.target.value as Settings["risk_profile"] })}>
                <option value="conservative">Conservative</option><option value="moderate">Moderate</option><option value="aggressive">Aggressive</option>
              </select>
            </label>
            <label>Horizon (years)<input type="number" min={1} max={60} defaultValue={s.horizon_years} onBlur={(e) => save({ horizon_years: Number(e.target.value) })} /></label>
            <label>Age<input type="number" min={15} max={100} defaultValue={s.age ?? ""} onBlur={(e) => save({ age: num(e.target.value) })} /></label>
          </div>
          <label>Goals, preferences and things to avoid
            <textarea rows={4} maxLength={2000} defaultValue={s.goals_notes} onBlur={(e) => save({ goals_notes: e.target.value })}
              placeholder="e.g. House down-payment in 4 years; retire at 55; no tobacco or gambling stocks; prefer index funds for core." />
          </label>
        </div>
      </Card>
      <Card title="Tax and rates">
        <div className="form">
          <div className="row">
            <label>Income-tax slab %<input type="number" step="any" min={0} max={42.744} defaultValue={s.tax_slab_pct} onBlur={(e) => save({ tax_slab_pct: Number(e.target.value) })} /></label>
            <label>Equity LTCG already booked this FY (₹)<input type="number" min={0} defaultValue={s.ltcg_exemption_used} onBlur={(e) => save({ ltcg_exemption_used: Number(e.target.value) })} /></label>
          </div>
          <div className="row">
            <label>Risk-free rate % (for Sharpe)<input type="number" step="any" min={0} defaultValue={s.risk_free_pct} onBlur={(e) => save({ risk_free_pct: Number(e.target.value) })} /></label>
            <label>RBI repo rate % (optional)<input type="number" step="any" min={0} defaultValue={s.rbi_repo_rate_pct ?? ""} onBlur={(e) => save({ rbi_repo_rate_pct: num(e.target.value) })} /></label>
          </div>
        </div>
      </Card>
      <Card title="Notifications">
        <div className="form">
          <div className="toggle-grid">
            {(["morning", "evening", "weekly"] as const).map((k) => (
              <label key={k} className="toggle"><input type="checkbox" checked={s.digests_enabled[k]} onChange={(e) => save({ digests_enabled: { ...s.digests_enabled, [k]: e.target.checked } })} />{k[0].toUpperCase() + k.slice(1)} digest</label>
            ))}
            <label className="toggle"><input type="checkbox" checked={s.email_digests} onChange={(e) => save({ email_digests: e.target.checked })} />Email digests</label>
            <label className="toggle"><input type="checkbox" checked={s.push_digests} onChange={(e) => save({ push_digests: e.target.checked })} />Push digests</label>
            <label className="toggle"><input type="checkbox" checked={s.push_alerts} onChange={(e) => save({ push_alerts: e.target.checked })} />Push alerts</label>
            <label className="toggle"><input type="checkbox" checked={s.email_alerts} onChange={(e) => save({ email_alerts: e.target.checked })} />Email alerts too</label>
          </div>
          <div className="row">
            <label>Alert on daily move ≥ (%)<input type="number" step="any" min={0.1} defaultValue={s.alert_pct} onBlur={(e) => save({ alert_pct: Number(e.target.value) })} /></label>
            <label>…for crypto (%)<input type="number" step="any" min={0.1} defaultValue={s.alert_pct_crypto} onBlur={(e) => save({ alert_pct_crypto: Number(e.target.value) })} /></label>
          </div>
          <div className="btn-row">
            <button type="button" className="btn primary" onClick={togglePush} disabled={!pushSupported() && !pushOn}>{pushOn ? "Turn off push on this device" : "Turn on push on this device"}</button>
            {pushOn && <button type="button" className="btn" onClick={testPush}>Send a test</button>}
          </div>
          {pushMsg && <p className="small">{pushMsg}</p>}
          <p className="muted small">On iPhone, first add this app to your Home Screen (Share → Add to Home Screen), then open it from there and turn on push.</p>
        </div>
      </Card>
      {status && (
        <Card title="System status">
          <table className="kv"><tbody>
            <tr><td>Market data</td><td>{status.demo ? <Badge tone="warn">Demo (made up)</Badge> : <Badge tone="good">Live: Yahoo, AMFI, Crypto.com, FRED</Badge>}</td></tr>
            <tr><td>AI analyst</td><td>{status.ai ? <Badge tone="good">On · {status.models.analysis}, news: {status.models.news}</Badge> : <Badge tone="bad">Off (set ANTHROPIC_API_KEY)</Badge>}</td></tr>
            <tr><td>Email</td><td>{status.email ? <Badge tone="good">Gmail configured</Badge> : <Badge tone="bad">Not configured</Badge>}</td></tr>
            <tr><td>Push</td><td>{status.push ? <Badge tone="good">Configured · {status.push_subscriptions} device(s)</Badge> : <Badge tone="bad">VAPID keys missing</Badge>}</td></tr>
            {Object.entries(status.jobs).map(([job, j]) => (
              <tr key={job}><td>Last {job}</td><td><Badge tone={j.status === "ok" ? "good" : j.status === "error" ? "bad" : "neutral"}>{j.status}</Badge> {when(j.started_at)}</td></tr>
            ))}
          </tbody></table>
        </Card>
      )}
      <button className="btn ghost danger" onClick={async () => { await api.post("/auth/logout"); onLogout(); }}>Sign out</button>
    </div>
  );
}
