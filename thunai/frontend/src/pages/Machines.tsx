import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api";
import type { Machine } from "../api";
import { Header, Icon, OfflineBanner, Page, Spinner } from "../components";
import { useApp } from "../state";

const CACHE_KEY = "thunai-machines";

export function machineTarget(next: string | null, machineNo: string): string {
  const no = encodeURIComponent(machineNo);
  if (next === "ask") return `/ask/${no}`;
  if (next === "log") return `/log/new/${no}`;
  return `/m/${no}`;
}

function cached(): Machine[] {
  try {
    return JSON.parse(localStorage.getItem(CACHE_KEY) ?? "[]");
  } catch {
    return [];
  }
}

export default function Machines() {
  const { t } = useApp();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = params.get("next");
  const [all, setAll] = useState<Machine[]>(cached);
  const [recent, setRecent] = useState<Machine[]>([]);
  const [zone, setZone] = useState("");
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(all.length === 0);

  useEffect(() => {
    // The full list is cached so a machine can be picked for an offline log.
    api
      .get<Machine[]>("/api/machines?limit=1000")
      .then((list) => {
        setAll(list);
        localStorage.setItem(CACHE_KEY, JSON.stringify(list));
      })
      .catch(() => {})
      .finally(() => setLoading(false));
    api.get<Machine[]>("/api/machines/recent").then(setRecent).catch(() => {});
  }, []);

  const zones = useMemo(() => [...new Set(all.map((m) => m.zone).filter(Boolean))].sort(), [all]);
  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return all.filter(
      (m) => (!zone || m.zone === zone) && (!needle || m.machine_no.toLowerCase().includes(needle) || m.name.toLowerCase().includes(needle)),
    );
  }, [all, q, zone]);

  const pick = (m: Machine) => navigate(machineTarget(next, m.machine_no));

  return (
    <>
      <Header title={t("pick_machine")} />
      <OfflineBanner />
      <Page>
        <div className="search-row">
          <div className="search">
            <Icon name="search" />
            <input
              className="input"
              placeholder={t("search_machine")}
              value={q}
              onChange={(e) => setQ(e.target.value)}
              autoFocus
              inputMode="search"
            />
          </div>
          <button className="btn btn-square" onClick={() => navigate(`/scan${next ? `?next=${next}` : ""}`)} aria-label={t("scan_qr")}>
            <Icon name="qr" size={28} />
          </button>
        </div>
        {zones.length > 1 && (
          <div className="chips-row">
            <button className={`chip-btn ${zone === "" ? "on" : ""}`} onClick={() => setZone("")}>
              {t("all_machines")}
            </button>
            {zones.map((z) => (
              <button key={z} className={`chip-btn ${zone === z ? "on" : ""}`} onClick={() => setZone(z)}>
                {z}
              </button>
            ))}
          </div>
        )}
        {recent.length > 0 && !q && !zone && (
          <>
            <h2 className="section-title">{t("recent")}</h2>
            {recent.map((m) => (
              <MachineRow key={`r-${m.id}`} m={m} onPick={pick} />
            ))}
            <h2 className="section-title">{t("all_machines")}</h2>
          </>
        )}
        {loading && <Spinner label={t("loading")} />}
        {shown.map((m) => (
          <MachineRow key={m.id} m={m} onPick={pick} />
        ))}
        {!loading && shown.length === 0 && <p className="muted">{t("nothing_here")}</p>}
      </Page>
    </>
  );
}

function MachineRow({ m, onPick }: { m: Machine; onPick: (m: Machine) => void }) {
  return (
    <button className="list-item" onClick={() => onPick(m)}>
      <div>
        <strong className="mono">{m.machine_no}</strong>
        <div className="muted">
          {m.name} · {m.zone}
        </div>
      </div>
      <span className={`dot-status status-${m.status}`} title={m.status} />
    </button>
  );
}
