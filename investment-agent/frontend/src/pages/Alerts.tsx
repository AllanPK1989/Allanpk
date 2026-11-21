import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Badge, Card, Empty, Spinner, useAsync } from "../components";
import { when } from "../format";

type Alert = { id: number; kind: string; title: string; body: string; url: string; created_at: string };

export default function Alerts() {
  const list = useAsync(() => api.get<{ alerts: Alert[] }>("/alerts"), []);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const check = async () => {
    setBusy(true);
    try {
      const r = await api.post<{ new: string[] }>("/alerts/check");
      setMsg(r.new.length ? `${r.new.length} new: ${r.new.join(", ")}` : "Nothing new crossed your thresholds.");
      list.reload();
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="page">
      <div className="page-head">
        <h1>Alerts</h1>
        <button className="btn" onClick={check} disabled={busy}>{busy ? "Checking…" : "Check now"}</button>
      </div>
      <p className="muted">Checked every 15–30 minutes during market hours: daily moves beyond your threshold (default ±3%, crypto ±6%; set per instrument on its page) and high-impact news. Thresholds are in <Link to="/settings">Settings</Link>.</p>
      {msg && <div className="ok-note">{msg}</div>}
      <Card>
        {list.loading && <Spinner />}
        {list.data && list.data.alerts.length === 0 && <Empty>No alerts yet.</Empty>}
        {list.data?.alerts.map((a) => (
          <div key={a.id} className="alert-row">
            <Badge tone={a.kind === "price" ? "warn" : "info"}>{a.kind}</Badge>
            <div>
              <div>{a.url.startsWith("/") ? <Link to={a.url}>{a.title}</Link> : a.url ? <a href={a.url} target="_blank" rel="noopener noreferrer">{a.title}</a> : a.title}</div>
              <div className="muted small">{a.body} · {when(a.created_at)}</div>
            </div>
          </div>
        ))}
      </Card>
    </div>
  );
}
