import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { Badge, Card, Empty, ErrorNote, Spinner, useAsync } from "../components";
import { when } from "../format";
import type { DigestSummary } from "../types";

const KIND_TONE: Record<string, "info" | "good" | "warn" | "neutral"> = { morning: "info", evening: "good", weekly: "neutral", alert: "warn" };

export default function Digests() {
  const [kind, setKind] = useState("");
  const list = useAsync(() => api.get<{ digests: DigestSummary[] }>(`/digests?limit=60${kind ? `&kind=${kind}` : ""}`), [kind]);
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState<unknown>();
  const nav = useNavigate();
  const run = async (k: string, send: boolean) => {
    setBusy(k);
    setErr(undefined);
    try {
      const r = await api.post<{ id: number }>("/digests/run", { kind: k, send });
      nav(`/digests/${r.id}`);
    } catch (e) {
      setErr(e);
    } finally {
      setBusy("");
    }
  };
  return (
    <div className="page">
      <h1>Digests</h1>
      <p className="muted">Sent automatically: morning (about 8:00 IST), evening (about 16:30 IST) and weekly (Sunday), by email and push. Alerts appear here too.</p>
      <Card title="Make one now">
        <div className="btn-row">
          {["morning", "evening", "weekly"].map((k) => (
            <button key={k} className="btn" disabled={!!busy} onClick={() => run(k, false)}>{busy === k ? "Building… (about a minute)" : `${k[0].toUpperCase()}${k.slice(1)} digest`}</button>
          ))}
        </div>
        <p className="muted small">Built and saved here only; scheduled digests are the ones that email and push.</p>
        <ErrorNote error={err} />
      </Card>
      <div className="filters">
        {["", "morning", "evening", "weekly", "alert"].map((k) => (
          <button key={k} className={`chip ${kind === k ? "active" : ""}`} onClick={() => setKind(k)}>{k || "All"}</button>
        ))}
      </div>
      <Card>
        {list.loading && <Spinner />}
        {list.data && list.data.digests.length === 0 && <Empty>Nothing yet.</Empty>}
        {list.data?.digests.map((d) => (
          <Link key={d.id} to={`/digests/${d.id}`} className="row-link">
            <span><Badge tone={KIND_TONE[d.kind] ?? "neutral"}>{d.kind}</Badge> {d.title}</span>
            <span className="muted small">{when(d.created_at)}{d.emailed ? " · emailed" : ""}{d.pushed ? " · pushed" : ""}</span>
          </Link>
        ))}
      </Card>
    </div>
  );
}
