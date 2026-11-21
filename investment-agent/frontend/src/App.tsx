import { useCallback, useEffect, useRef, useState } from "react";
import { NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api, setUnauthorizedHandler } from "./api";
import { CLASS_LABEL } from "./format";
import Alerts from "./pages/Alerts";
import Chat from "./pages/Chat";
import Dashboard from "./pages/Dashboard";
import DigestView from "./pages/DigestView";
import Digests from "./pages/Digests";
import InstrumentPage from "./pages/Instrument";
import Login from "./pages/Login";
import News from "./pages/News";
import Planner from "./pages/Planner";
import PortfolioPage from "./pages/Portfolio";
import SearchPage from "./pages/Search";
import SettingsPage from "./pages/Settings";
import type { SearchResult, Status } from "./types";

const NAV = [
  { to: "/", label: "Home", icon: "M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z", end: true },
  { to: "/portfolio", label: "Portfolio", icon: "M4 19V9m6 10V5m6 14v-7m4 7H2" },
  { to: "/chat", label: "Adviser", icon: "M4 5h16v11H8l-4 4z" },
  { to: "/news", label: "News", icon: "M5 4h11v16H6a2 2 0 0 1-2-2V5zm11 4h4v10a2 2 0 0 1-2 2M8 8h5M8 12h5M8 16h3" },
  { to: "/digests", label: "Digests", icon: "M4 6l8 6 8-6M4 6h16v12H4z" },
  { to: "/alerts", label: "Alerts", icon: "M12 3a6 6 0 0 0-6 6v4l-2 3h16l-2-3V9a6 6 0 0 0-6-6zm-2 16a2 2 0 0 0 4 0" },
  { to: "/planner", label: "Planner", icon: "M12 3v18M5 8h9a3 3 0 0 1 0 6H8a3 3 0 0 0 0 6h11" },
  { to: "/settings", label: "Settings", icon: "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm8-3 2-1-2-4-2 1-2-1V5h-4v2l-2 1-2-1-2 4 2 1v2l-2 1 2 4 2-1 2 1v2h4v-2l2-1 2 1 2-4-2-1z" },
];
const MOBILE_NAV = ["/", "/portfolio", "/chat", "/news", "/more"];
const MORE_ICON = "M5 12h.01M12 12h.01M19 12h.01";

function Icon({ d }: { d: string }) {
  return (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d={d} />
    </svg>
  );
}

function GlobalSearch() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();
  const timer = useRef<number>(undefined);
  useEffect(() => {
    window.clearTimeout(timer.current);
    if (q.trim().length < 2) {
      setResults([]);
      return;
    }
    timer.current = window.setTimeout(() => {
      setBusy(true);
      api.get<{ results: SearchResult[] }>(`/search?q=${encodeURIComponent(q.trim())}`)
        .then((r) => setResults(r.results))
        .catch(() => setResults([]))
        .finally(() => setBusy(false));
    }, 350);
  }, [q]);
  const pick = async (r: SearchResult) => {
    await api.post("/instruments", r);
    setOpen(false);
    setQ("");
    nav(`/instrument/${encodeURIComponent(r.symbol)}`);
  };
  return (
    <div className="gsearch">
      <input
        type="search"
        placeholder="Search stocks, funds, crypto, gold, FX…"
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 200)}
        aria-label="Search instruments"
      />
      {open && q.trim().length >= 2 && (
        <div className="gsearch-results">
          {busy && <div className="muted pad">Searching…</div>}
          {!busy && results.length === 0 && <div className="muted pad">No matches.</div>}
          {results.map((r) => (
            <button key={r.symbol} onMouseDown={(e) => e.preventDefault()} onClick={() => pick(r)}>
              <span className="r-name">{r.name}</span>
              <span className="r-meta">{r.symbol} · {CLASS_LABEL[r.asset_class] ?? r.asset_class}{r.exchange ? ` · ${r.exchange}` : ""}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function More() {
  return (
    <div className="page">
      <h1>More</h1>
      <div className="more-grid">
        {NAV.filter((n) => !MOBILE_NAV.includes(n.to)).map((n) => (
          <NavLink key={n.to} to={n.to} className="more-item">
            <Icon d={n.icon} />
            {n.label}
          </NavLink>
        ))}
        <NavLink to="/search" className="more-item">
          <Icon d="M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zm9 16-4.3-4.3" />
          Search
        </NavLink>
      </div>
    </div>
  );
}

export default function App() {
  const [auth, setAuth] = useState<"checking" | "in" | "out">("checking");
  const [status, setStatus] = useState<Status | null>(null);
  const loc = useLocation();
  const check = useCallback(() => {
    api.get<{ authenticated: boolean }>("/auth/me")
      .then((r) => setAuth(r.authenticated ? "in" : "out"))
      .catch(() => setAuth("out"));
  }, []);
  useEffect(() => {
    setUnauthorizedHandler(() => setAuth("out"));
    check();
  }, [check]);
  useEffect(() => {
    if (auth === "in") api.get<Status>("/status").then(setStatus).catch(() => {});
  }, [auth]);

  if (auth === "checking") return <div className="boot">Loading…</div>;
  if (auth === "out") return <Login onLogin={() => setAuth("in")} />;

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <img src="/icon.svg" alt="" width="28" height="28" />
          <span>Investment Analyst</span>
        </div>
        <nav>
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end} className={({ isActive }) => (isActive ? "active" : "")}>
              <Icon d={n.icon} />
              {n.label}
            </NavLink>
          ))}
        </nav>
        {status && (
          <div className="side-status">
            {status.demo && <span className="pill warn">Demo data</span>}
            <span className={`pill ${status.ai ? "ok" : "off"}`}>AI {status.ai ? "on" : "off"}</span>
          </div>
        )}
      </aside>
      <div className="main">
        <header className="topbar">
          <img className="mobile-logo" src="/icon.svg" alt="" width="26" height="26" />
          <GlobalSearch />
          {status?.demo && <span className="pill warn hide-sm">Demo data</span>}
        </header>
        <main className="content" key={loc.pathname.split("/")[1]}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="/instrument/:symbol" element={<InstrumentPage />} />
            <Route path="/portfolio" element={<PortfolioPage />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/chat/:sid" element={<Chat />} />
            <Route path="/news" element={<News />} />
            <Route path="/digests" element={<Digests />} />
            <Route path="/digests/:id" element={<DigestView />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/planner" element={<Planner />} />
            <Route path="/settings" element={<SettingsPage status={status} onLogout={() => setAuth("out")} />} />
            <Route path="/more" element={<More />} />
            <Route path="*" element={<Dashboard />} />
          </Routes>
        </main>
      </div>
      <nav className="bottomnav">
        {MOBILE_NAV.map((to) => {
          const n = NAV.find((x) => x.to === to) ?? { to: "/more", label: "More", icon: MORE_ICON, end: false };
          return (
            <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>
              <Icon d={n.icon} />
              <span>{n.label}</span>
            </NavLink>
          );
        })}
      </nav>
    </div>
  );
}
