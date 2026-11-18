import { useCallback, useEffect, useRef, useState } from "react";
import { NavLink, Route, Routes, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { api, setUnauthorizedHandler, type Dashboard as D } from "./api";
import { Capture } from "./components/Capture";
import { NoteSheet, NudgeSheet, TaskMenu } from "./components/Sheets";
import { Icon } from "./icons";
import { Briefing, Wrapup } from "./pages/Briefing";
import { Dashboard } from "./pages/Dashboard";
import { Login } from "./pages/Login";
import { People } from "./pages/People";
import { Review } from "./pages/Review";
import { Settings } from "./pages/Settings";
import { TaskDetail } from "./pages/TaskDetail";
import { Tasks } from "./pages/Tasks";
import { useApp } from "./store";
import { BasketDot } from "./ui";

interface AuthStatus {
  has_pin: boolean;
  logged_in: boolean;
  demo: boolean;
  demo_pin: string | null;
}

function Fab() {
  const { openCapture, capture } = useApp();
  const down = useRef(0);
  return (
    <button className={`fab ${capture.open ? "recording" : ""}`} aria-label="Add tasks by voice (hold to talk)"
      onPointerDown={() => { down.current = Date.now(); if (!capture.open) openCapture("voice", true); }}
      onPointerUp={() => { if (Date.now() - down.current > 700) window.dispatchEvent(new Event("nudge-stop-recording")); }}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openCapture("voice", true); } }}>
      <Icon name="mic" size={30} />
    </button>
  );
}

function Sidebar({ lanes }: { lanes: D["lanes"] | null }) {
  const { baskets, demo, openCapture } = useApp();
  const items: [string, string, string, number | undefined][] = [
    ["/", "Dashboard", "home", undefined],
    ["/tasks?lane=today", "Today", "sun", lanes?.today],
    ["/tasks?lane=overdue", "Overdue", "alert", lanes?.overdue],
    ["/tasks?lane=upcoming", "Upcoming", "upcoming", lanes?.upcoming],
    ["/tasks?lane=waiting", "Waiting on others", "hourglass", lanes?.waiting],
    ["/tasks?lane=inbox", "Inbox", "inbox", lanes?.inbox],
    ["/tasks?lane=done", "Done", "done", undefined],
  ];
  const loc = useLocation();
  const here = loc.pathname + loc.search;
  return (
    <nav className="sidebar" aria-label="Main">
      <div className="brand"><img src="/icon.svg" width={30} height={30} alt="" style={{ borderRadius: 8 }} />Nudge {demo && <span className="demo-pill">DEMO</span>}</div>
      <button className="btn primary" style={{ margin: "0 4px 12px" }} onClick={() => openCapture("text")}><Icon name="plus" />New task <span className="tiny" style={{ opacity: 0.8 }}>N</span></button>
      {items.map(([to, label, icon, count]) => (
        <NavLink key={to} to={to} className={() => (here === to || (to === "/" && loc.pathname === "/") ? "active" : "")} end>
          <Icon name={icon} size={18} />{label}{count ? <span className="count">{count}</span> : null}
        </NavLink>
      ))}
      <div className="section">Baskets</div>
      {baskets.map((b) => (
        <NavLink key={b.id} to={`/basket/${b.id}`}><BasketDot basket={b} />{b.name}{b.open ? <span className="count">{b.open}</span> : null}</NavLink>
      ))}
      <div className="section">Review</div>
      <NavLink to="/people"><Icon name="users" size={18} />People</NavLink>
      <NavLink to="/review"><Icon name="chart" size={18} />Weekly review</NavLink>
      <NavLink to="/briefing"><Icon name="sun" size={18} />Morning briefing</NavLink>
      <NavLink to="/wrapup"><Icon name="sunset" size={18} />Evening wrap-up</NavLink>
      <div style={{ flex: 1 }} />
      <NavLink to="/settings"><Icon name="settings" size={18} />Settings</NavLink>
    </nav>
  );
}

function BottomNav() {
  return (
    <nav className="bottomnav" aria-label="Main">
      <NavLink to="/" end><Icon name="home" size={22} />Home</NavLink>
      <NavLink to="/tasks"><Icon name="list" size={22} />Tasks</NavLink>
      <div className="mic-slot" aria-hidden="true" />
      <NavLink to="/people"><Icon name="users" size={22} />People</NavLink>
      <NavLink to="/review"><Icon name="chart" size={22} />Review</NavLink>
    </nav>
  );
}

function Toasts() {
  const { toasts, dismiss } = useApp();
  return (
    <div className="toasts" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`toast ${t.kind === "error" ? "error" : ""}`}>
          <div className="row">
            <span className="grow">{t.text}</span>
            {t.actions?.filter((a) => !a.chip).map((a) => <button key={a.label} className="tbtn" onClick={() => { dismiss(t.id); a.onClick(); }}>{a.label}</button>)}
            <button className="tbtn" aria-label="Dismiss" onClick={() => dismiss(t.id)} style={{ color: "#c3c2b7" }}><Icon name="x" size={16} /></button>
          </div>
          {t.actions?.some((a) => a.chip) && (
            <div className="row wrap" style={{ marginTop: 8, gap: 6 }}>
              {t.actions.filter((a) => a.chip).map((a) => <button key={a.label} className="tchip" onClick={() => { dismiss(t.id); a.onClick(); }}>{a.label}</button>)}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function TopBar() {
  const { demo, online, queued } = useApp();
  const nav = useNavigate();
  return (
    <header className="topbar mobile-only">
      <div className="title"><img src="/icon.svg" width={26} height={26} alt="" style={{ borderRadius: 7 }} /><span>Nudge</span>{demo && <span className="demo-pill">DEMO</span>}</div>
      {!online && <span className="badge neutral"><Icon name="wifioff" size={12} />Offline{queued ? ` · ${queued} waiting` : ""}</span>}
      <button className="icon-btn" onClick={() => nav("/tasks?q=")} aria-label="Search"><Icon name="search" /></button>
      <button className="icon-btn" onClick={() => nav("/settings")} aria-label="Settings"><Icon name="settings" /></button>
    </header>
  );
}

export function App() {
  const { reloadBaskets, setDemo, refreshKey, openCapture, online, queued } = useApp();
  const [auth, setAuth] = useState<AuthStatus | null>(null);
  const [lanes, setLanes] = useState<D["lanes"] | null>(null);
  const [params, setParams] = useSearchParams();
  const nav = useNavigate();

  const checkAuth = useCallback(() => {
    api.get<AuthStatus>("/api/auth/status").then((a) => { setAuth(a); setDemo(a.demo); })
      .catch(() => setAuth({ has_pin: true, logged_in: true, demo: false, demo_pin: null })); // offline: show cached screens
  }, [setDemo]);

  useEffect(() => {
    checkAuth();
    setUnauthorizedHandler(() => setAuth((a) => (a ? { ...a, logged_in: false } : a)));
  }, [checkAuth]);

  useEffect(() => {
    if (!auth?.logged_in) return;
    reloadBaskets();
    api.get<D>("/api/dashboard").then((d) => setLanes(d.lanes)).catch(() => {});
  }, [auth?.logged_in, refreshKey, reloadBaskets]);

  useEffect(() => {
    if (auth?.logged_in && params.get("capture")) {
      openCapture(params.get("capture") === "text" ? "text" : "voice", false);
      params.delete("capture");
      setParams(params, { replace: true });
    }
  }, [auth?.logged_in, params, setParams, openCapture]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement;
      if (el.closest("input, textarea, select, [contenteditable]") || e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "n") { e.preventDefault(); openCapture("text"); }
      else if (e.key === "v") { e.preventDefault(); openCapture("voice", true); }
      else if (e.key === "/") { e.preventDefault(); nav("/tasks?q="); setTimeout(() => document.getElementById("search")?.focus(), 50); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [openCapture, nav]);

  if (!auth) return null;
  if (!auth.logged_in) return <Login hasPin={auth.has_pin} demoPin={auth.demo_pin} onDone={checkAuth} />;

  return (
    <div className="shell">
      <Sidebar lanes={lanes} />
      <main className="main">
        <TopBar />
        {!online && <div className="offline desktop-only"><Icon name="wifioff" size={16} />You're offline. Changes are saved and will sync{queued ? ` (${queued} waiting)` : ""}.</div>}
        <div style={{ height: 8 }} />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/tasks" element={<Tasks />} />
          <Route path="/basket/:basketId" element={<Tasks />} />
          <Route path="/task/:id" element={<TaskDetail />} />
          <Route path="/people" element={<People />} />
          <Route path="/review" element={<Review />} />
          <Route path="/briefing" element={<Briefing />} />
          <Route path="/wrapup" element={<Wrapup />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Dashboard />} />
        </Routes>
      </main>
      <BottomNav />
      <Fab />
      <Capture />
      <TaskMenu />
      <NoteSheet />
      <NudgeSheet />
      <Toasts />
    </div>
  );
}
