import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { Badge, Card, ErrorNote, SafeHtml, Spinner, useAsync } from "../components";
import { when } from "../format";

type Digest = { id: number; kind: string; title: string; html: string; created_at: string; ai_generated: boolean; emailed: boolean; pushed: boolean };

export default function DigestView() {
  const { id } = useParams();
  const d = useAsync(() => api.get<Digest>(`/digests/${id}`), [id]);
  return (
    <div className="page narrow">
      <Link to="/digests" className="link">← All digests</Link>
      {d.loading && <Spinner />}
      <ErrorNote error={d.error} />
      {d.data && (
        <Card>
          <div className="muted small">
            <Badge>{d.data.kind}</Badge> {when(d.data.created_at)} · {d.data.ai_generated ? "written by AI from live data" : "data only"}
            {d.data.emailed ? " · emailed" : ""}{d.data.pushed ? " · pushed" : ""}
          </div>
          <h1 className="digest-title">{d.data.title}</h1>
          <SafeHtml html={d.data.html} />
        </Card>
      )}
    </div>
  );
}
