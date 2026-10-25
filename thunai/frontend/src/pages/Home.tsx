import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import type { Log } from "../api";
import { Header, Icon, OfflineBanner, Page, StatusChip, formatDate } from "../components";
import { useApp } from "../state";

export default function Home() {
  const { t, user, logout, lang, meta } = useApp();
  const navigate = useNavigate();
  const [pending, setPending] = useState<Log[]>([]);

  useEffect(() => {
    api.get<Log[]>("/api/logs?scope=mine&needs_confirmation=true&limit=10").then(setPending).catch(() => {});
  }, []);

  if (!user) return null;
  const isSup = user.role !== "technician";
  return (
    <>
      <Header title={t("app_name")} back={false} />
      <OfflineBanner />
      <Page>
        <p className="greeting">{t("hello", { name: user.name })}</p>
        {meta?.copilot?.enabled && meta.copilot.teams_url && (
          <a className="note note-info teams-link" href={meta.copilot.teams_url} target="_blank" rel="noreferrer">
            <Icon name="chat" size={20} />
            <span>
              <strong>{t("open_in_teams")}</strong> {t("open_in_teams_sub")}
            </span>
          </a>
        )}
        <button className="tile tile-primary" onClick={() => navigate("/machines?next=ask")}>
          <Icon name="help" size={40} />
          <span>
            <strong>{t("ask")}</strong>
            <small>{t("ask_sub")}</small>
          </span>
        </button>
        <button className="tile tile-accent" onClick={() => navigate("/machines?next=log")}>
          <Icon name="mic" size={40} />
          <span>
            <strong>{t("new_log")}</strong>
            <small>{t("new_log_sub")}</small>
          </span>
        </button>
        <div className="tile-row">
          <button className="tile tile-small" onClick={() => navigate("/scan")}>
            <Icon name="qr" size={32} />
            <strong>{t("scan_qr")}</strong>
          </button>
          <button className="tile tile-small" onClick={() => navigate("/machines?next=view")}>
            <Icon name="wrench" size={32} />
            <strong>{t("machines")}</strong>
          </button>
          <button className="tile tile-small" onClick={() => navigate("/logs")}>
            <Icon name="list" size={32} />
            <strong>{t("my_logs")}</strong>
          </button>
          {isSup && (
            <button className="tile tile-small" onClick={() => navigate("/review")}>
              <Icon name="check" size={32} />
              <strong>{t("review")}</strong>
            </button>
          )}
          {isSup && (
            <button className="tile tile-small" onClick={() => navigate("/dashboard")}>
              <Icon name="chart" size={32} />
              <strong>{t("dashboard")}</strong>
            </button>
          )}
          {isSup && (
            <button className="tile tile-small" onClick={() => navigate("/skills")}>
              <Icon name="users" size={32} />
              <strong>{t("skills")}</strong>
            </button>
          )}
          {user.role === "admin" && (
            <button className="tile tile-small" onClick={() => navigate("/admin")}>
              <Icon name="settings" size={32} />
              <strong>{t("admin")}</strong>
            </button>
          )}
        </div>
        {pending.length > 0 && (
          <section>
            <h2 className="section-title">{t("needs_check")}</h2>
            {pending.map((l) => (
              <Link key={l.id} className="list-item" to={`/log/${l.id}`}>
                <div>
                  <strong>{l.machine_no}</strong> · {formatDate(l.reported_at, true)}
                  <div className="muted clamp">
                    {l.texts.issue.original || (lang === "ta" ? l.texts.issue.ta : l.texts.issue.en)}
                  </div>
                </div>
                <StatusChip status={l.status} />
              </Link>
            ))}
          </section>
        )}
        <div className="logout-row">
          <button className="btn btn-ghost" onClick={() => logout()}>
            <Icon name="logout" /> {t("logout")} · {user.employee_id}
          </button>
        </div>
      </Page>
    </>
  );
}
