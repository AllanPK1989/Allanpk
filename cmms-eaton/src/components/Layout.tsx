import { useEffect, useMemo, useState, type ReactNode } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { ROLE_LABELS } from "../types";
import { hashPassword, validatePassword, verifyPassword } from "../lib/auth";
import { duePlans } from "../lib/kpi";
import { can, canAny } from "../lib/permissions";
import { isOpenStatus } from "../lib/workorders";
import { useStore } from "../store/StoreProvider";
import { Icon, type IconName } from "./icons";
import { useToast } from "./Toast";
import { Button, Field, Modal, Notice } from "./ui";

interface NavItem {
  to: string;
  label: string;
  icon: IconName;
  show: boolean;
  count?: number;
  hot?: boolean;
}

const TITLES: { prefix: string; title: string }[] = [
  { prefix: "/work-orders", title: "Work orders" },
  { prefix: "/pm", title: "Preventive maintenance" },
  { prefix: "/assets", title: "Assets" },
  { prefix: "/parts", title: "Spare parts" },
  { prefix: "/reports", title: "Reports" },
  { prefix: "/users", title: "Users" },
  { prefix: "/settings", title: "Settings" },
];

export function Layout({ children }: { children: ReactNode }) {
  const { user, snapshot, storage, logout, reconnectFolder } = useStore();
  const [open, setOpen] = useState(false);
  const [menu, setMenu] = useState(false);
  const [changePw, setChangePw] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    setOpen(false);
    setMenu(false);
  }, [location.pathname]);

  const openBreakdowns = useMemo(() => snapshot.workOrders.filter((w) => w.type === "breakdown" && isOpenStatus(w.status)), [snapshot.workOrders]);
  const dueCount = useMemo(() => duePlans(snapshot.pmPlans, snapshot.assets).length, [snapshot.pmPlans, snapshot.assets]);

  if (!user) return null;

  const items: NavItem[] = [
    { to: "/", label: "Dashboard", icon: "dashboard", show: true },
    {
      to: "/work-orders",
      label: "Work orders",
      icon: "wrench",
      show: true,
      count: openBreakdowns.length || undefined,
      hot: openBreakdowns.some((w) => w.priority === "critical"),
    },
    { to: "/pm", label: "Preventive maintenance", icon: "calendar", show: can(user, "pm.view"), count: dueCount || undefined },
    { to: "/assets", label: "Assets", icon: "box", show: can(user, "asset.view") },
    { to: "/parts", label: "Spare parts", icon: "package", show: can(user, "part.view") },
    { to: "/reports", label: "Reports", icon: "chart", show: can(user, "reports.view") },
    { to: "/users", label: "Users", icon: "users", show: canAny(user, "user.manage_technicians", "user.manage_all") },
    { to: "/settings", label: "Settings", icon: "settings", show: canAny(user, "settings.manage", "data.export", "storage.manage") },
  ];

  const title = TITLES.find((t) => location.pathname.startsWith(t.prefix))?.title ?? "Dashboard";
  const storageTone = storage.error ? "bad" : storage.needsReconnect ? "warn" : "";
  const storageLabel = storage.mode === "folder" ? `Shared folder${storage.folderName ? `: ${storage.folderName}` : ""}` : storage.mode === "sharepoint" ? "SharePoint (not connected)" : "This device";
  const initials = user.name
    .split(" ")
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className="app">
      {open && <div className="scrim" onClick={() => setOpen(false)} />}
      <aside className={`sidebar ${open ? "open" : ""}`}>
        <div className="brand">
          <img src="/icon.svg" alt="" />
          <div>
            CMMS_Eaton
            <small>{snapshot.settings.plantName}</small>
          </div>
        </div>
        <nav className="nav" aria-label="Main">
          {items
            .filter((i) => i.show)
            .map((i) => (
              <NavLink key={i.to} to={i.to} end={i.to === "/"} className={({ isActive }) => (isActive ? "active" : "")}>
                <Icon name={i.icon} size={18} />
                {i.label}
                {i.count !== undefined && <span className={`count ${i.hot ? "hot" : ""}`}>{i.count}</span>}
              </NavLink>
            ))}
        </nav>
        <div className="sidebar-foot">
          {ROLE_LABELS[user.role]}
          <br />
          {storageLabel}
        </div>
      </aside>
      <div className="main">
        <header className="topbar">
          <Button variant="ghost" icon="menu" className="hamburger" aria-label="Menu" onClick={() => setOpen(true)} />
          <span className="title">{title}</span>
          {snapshot.demo && <span className="badge warning">Sample data</span>}
          <span className="spacer" />
          <button type="button" className="btn ghost sm hide-mobile" onClick={() => navigate("/settings?tab=storage")} title="Data storage">
            <span className={`storage-dot ${storageTone}`} />
            {storage.saving ? "Saving…" : storageLabel}
          </button>
          <button type="button" className="user-chip" onClick={() => setMenu((m) => !m)} aria-haspopup="menu" aria-expanded={menu}>
            <span className="avatar">{initials}</span>
            <span className="hide-mobile">{user.name}</span>
            <Icon name="chevron-down" size={14} />
          </button>
          {menu && (
            <div className="menu" role="menu">
              <div className="menu-head">
                <div style={{ fontWeight: 600 }}>{user.name}</div>
                <div className="small muted">
                  {user.employeeId} · {ROLE_LABELS[user.role]}
                </div>
              </div>
              <button type="button" onClick={() => setChangePw(true)}>
                <Icon name="lock" size={16} /> Change password
              </button>
              <button type="button" onClick={logout}>
                <Icon name="logout" size={16} /> Log out
              </button>
            </div>
          )}
        </header>
        <main className="content">
          {storage.needsReconnect && (
            <div className="mb-8" style={{ marginBottom: 14 }}>
              <Notice tone="warning" icon="folder">
                <div className="flex between flex-wrap">
                  <span>
                    The shared folder{storage.folderName ? ` "${storage.folderName}"` : ""} needs permission again. Until then changes are saved on this device only.
                  </span>
                  <Button size="sm" variant="primary" onClick={reconnectFolder}>
                    Reconnect folder
                  </Button>
                </div>
              </Notice>
            </div>
          )}
          {storage.error && !storage.needsReconnect && (
            <div style={{ marginBottom: 14 }}>
              <Notice tone="critical" icon="alert">
                {storage.error}
              </Notice>
            </div>
          )}
          {children}
        </main>
      </div>
      <ChangePasswordModal open={changePw} onClose={() => setChangePw(false)} />
    </div>
  );
}

export function ChangePasswordModal({ open, onClose, forced }: { open: boolean; onClose: () => void; forced?: boolean }) {
  const { user, mutate } = useStore();
  const toast = useToast();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (open) {
      setCurrent("");
      setNext("");
      setConfirm("");
      setError(null);
    }
  }, [open]);

  if (!user) return null;

  const submit = async () => {
    setError(null);
    if (!forced && !(await verifyPassword(current, user.passwordSalt, user.passwordHash))) {
      setError("Current password is wrong");
      return;
    }
    const v = validatePassword(next);
    if (v) {
      setError(v);
      return;
    }
    if (next !== confirm) {
      setError("Passwords do not match");
      return;
    }
    setBusy(true);
    const { hash, salt } = await hashPassword(next);
    mutate(
      (d) => {
        const u = d.users.find((x) => x.id === user.id);
        if (!u) return;
        u.passwordHash = hash;
        u.passwordSalt = salt;
        u.mustChangePassword = false;
        u.updatedAt = new Date().toISOString();
      },
      { entity: "user", entityId: user.id, action: "password_change", summary: `${user.name} changed their password` },
    );
    setBusy(false);
    toast.success("Password changed");
    onClose();
  };

  return (
    <Modal
      title={forced ? "Set a new password" : "Change password"}
      open={open}
      onClose={forced ? () => undefined : onClose}
      size="narrow"
      footer={
        <>
          {!forced && <Button onClick={onClose}>Cancel</Button>}
          <Button variant="primary" onClick={submit} disabled={busy}>
            Save password
          </Button>
        </>
      }
    >
      <form
        className="stack"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        {forced && <p className="text-2">Your account was given a temporary password. Choose your own before continuing.</p>}
        {!forced && (
          <Field label="Current password" required>
            <input type="password" value={current} onChange={(e) => setCurrent(e.target.value)} autoComplete="current-password" />
          </Field>
        )}
        <Field label="New password" required hint="At least 8 characters">
          <input type="password" value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password" />
        </Field>
        <Field label="Confirm new password" required error={error}>
          <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" />
        </Field>
        <button type="submit" className="sr-only">
          Save
        </button>
      </form>
    </Modal>
  );
}
