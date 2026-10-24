import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import type { Log } from "../api";
import { ErrorNote, Header, OfflineBanner, Page, Spinner, StatusChip, formatDate } from "../components";
import { useApp } from "../state";

type Tab = "mine" | "check" | "zone";

export default function Logs() {
  const { t, lang } = useApp();
  const [tab, setTab] = useState<Tab>("mine");
  const [logs, setLogs] = useState<Log[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    setLogs(null);
    const path =
      tab === "check" ? "/api/logs?scope=mine&needs_confirmation=true" : tab === "zone" ? "/api/logs?scope=zone" : "/api/logs?scope=mine";
    api.get<Log[]>(path).then(setLogs).catch(setError);
  }, [tab]);

  return (
    <>
      <Header title={t("my_logs")} />
      <OfflineBanner />
      <Page>
        <div className="tabs" role="tablist">
          {(["mine", "check", "zone"] as Tab[]).map((k) => (
            <button key={k} role="tab" aria-selected={tab === k} className={`tab ${tab === k ? "on" : ""}`} onClick={() => setTab(k)}>
              {k === "mine" ? t("my_logs") : k === "check" ? t("needs_check") : t("zone_logs")}
            </button>
          ))}
        </div>
        <ErrorNote error={error} />
        {!logs && !error && <Spinner label={t("loading")} />}
        {logs?.length === 0 && <p className="muted">{t("nothing_here")}</p>}
        {logs?.map((l) => (
          <Link key={l.id} to={`/log/${l.id}`} className="list-item">
            <div>
              <strong className="mono">{l.machine_no}</strong> · {formatDate(l.reported_at, true)}
              <div className="clamp">
                {l.texts.issue.original || (lang === "ta" ? l.texts.issue.ta || l.texts.issue.en : l.texts.issue.en)}
              </div>
              <div className="muted small">
                {l.log_no} · {l.technician_name}
              </div>
            </div>
            <StatusChip status={l.status} />
          </Link>
        ))}
      </Page>
    </>
  );
}
