// App-wide state: baskets, system status, toasts, the capture sheet, theme and connectivity.
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api, errorText, OfflineError, type Basket, type ShortTask, type Task } from "./api";
import { dayLabel } from "./format";
import { queue, queuedCount, syncQueue } from "./offline";

export interface ToastAction {
  label: string;
  onClick: () => void;
  chip?: boolean;
}

export interface ToastItem {
  id: number;
  text: string;
  kind?: "info" | "error";
  actions?: ToastAction[];
  ms?: number;
}

export type Theme = "system" | "light" | "dark";

interface AppState {
  baskets: Basket[];
  reloadBaskets: () => Promise<void>;
  demo: boolean;
  setDemo: (v: boolean) => void;
  refreshKey: number;
  bump: () => void;
  toasts: ToastItem[];
  toast: (t: Omit<ToastItem, "id">) => number;
  dismiss: (id: number) => void;
  capture: { open: boolean; mode: "voice" | "text"; autostart: boolean };
  openCapture: (mode?: "voice" | "text", autostart?: boolean) => void;
  closeCapture: () => void;
  noteFor: Task | ShortTask | null;
  setNoteFor: (t: Task | ShortTask | null) => void;
  nudgeFor: ShortTask | Task | null;
  setNudgeFor: (t: ShortTask | Task | null) => void;
  menuFor: ShortTask | Task | null;
  setMenuFor: (t: ShortTask | Task | null) => void;
  theme: Theme;
  setTheme: (t: Theme) => void;
  online: boolean;
  queued: number;
}

const Ctx = createContext<AppState | null>(null);

function readTheme(): Theme {
  try {
    const t = localStorage.getItem("nudge-theme");
    return t === "light" || t === "dark" ? t : "system";
  } catch {
    return "system";
  }
}

export function applyTheme(t: Theme) {
  const root = document.documentElement;
  if (t === "system") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", t);
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [baskets, setBaskets] = useState<Basket[]>([]);
  const [demo, setDemo] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [capture, setCapture] = useState({ open: false, mode: "voice" as "voice" | "text", autostart: false });
  const [noteFor, setNoteFor] = useState<Task | ShortTask | null>(null);
  const [nudgeFor, setNudgeFor] = useState<ShortTask | Task | null>(null);
  const [menuFor, setMenuFor] = useState<ShortTask | Task | null>(null);
  const [theme, setThemeState] = useState<Theme>(readTheme);
  const [online, setOnline] = useState(navigator.onLine);
  const [queued, setQueued] = useState(0);
  const nextId = useRef(1);
  const timers = useRef(new Map<number, number>());

  const bump = useCallback(() => setRefreshKey((k) => k + 1), []);

  const reloadBaskets = useCallback(async () => {
    try {
      const { baskets } = await api.get<{ baskets: Basket[] }>("/api/baskets");
      setBaskets(baskets);
      localStorage.setItem("nudge-baskets", JSON.stringify(baskets));
    } catch {
      try {
        setBaskets(JSON.parse(localStorage.getItem("nudge-baskets") || "[]"));
      } catch {
        /* nothing saved */
      }
    }
  }, []);

  const dismiss = useCallback((id: number) => {
    setToasts((ts) => ts.filter((t) => t.id !== id));
    const h = timers.current.get(id);
    if (h) window.clearTimeout(h);
    timers.current.delete(id);
  }, []);

  const toast = useCallback((t: Omit<ToastItem, "id">) => {
    const id = nextId.current++;
    setToasts((ts) => [...ts.slice(-2), { ...t, id }]);
    timers.current.set(id, window.setTimeout(() => dismiss(id), t.ms ?? (t.actions?.length ? 9000 : 4000)));
    return id;
  }, [dismiss]);

  const setTheme = useCallback((t: Theme) => {
    setThemeState(t);
    try {
      localStorage.setItem("nudge-theme", t);
    } catch {
      /* private mode */
    }
    applyTheme(t);
  }, []);

  useEffect(() => {
    const refreshQueue = () => queuedCount().then(setQueued);
    const goOnline = async () => {
      setOnline(true);
      const n = await syncQueue();
      if (n) {
        toast({ text: `Synced ${n} change${n === 1 ? "" : "s"} made offline` });
        bump();
      }
    };
    const goOffline = () => setOnline(false);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    window.addEventListener("nudge-queue", refreshQueue);
    refreshQueue();
    if (navigator.onLine) goOnline();
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
      window.removeEventListener("nudge-queue", refreshQueue);
    };
  }, [bump, toast]);

  const value = useMemo<AppState>(() => ({
    baskets, reloadBaskets, demo, setDemo, refreshKey, bump, toasts, toast, dismiss, capture,
    openCapture: (mode = "voice", autostart = false) => setCapture({ open: true, mode, autostart }),
    closeCapture: () => setCapture((c) => ({ ...c, open: false, autostart: false })),
    noteFor, setNoteFor, nudgeFor, setNudgeFor, menuFor, setMenuFor, theme, setTheme, online, queued,
  }), [baskets, reloadBaskets, demo, refreshKey, bump, toasts, toast, dismiss, capture, noteFor, nudgeFor, menuFor,
    theme, setTheme, online, queued]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useApp(): AppState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useApp outside AppProvider");
  return v;
}

/** One-tap actions on a task, with Undo and the "Need a follow-up?" prompt after closing. */
export function useTaskActions() {
  const app = useApp();
  const { toast, bump, setNoteFor } = app;

  const complete = useCallback(async (t: ShortTask | Task) => {
    try {
      const res = await api.post<{ task: Task; spawned: Task[] }>(`/api/tasks/${t.id}/close`, {});
      bump();
      const next = res.spawned.find((s) => s.source === "repeat");
      const addFollowUp = async (days: number) => {
        try {
          const fu = await api.post<Task>(`/api/tasks/${t.id}/follow-up`, { in_days: days });
          bump();
          toast({ text: `Follow-up set for ${fu.due_date ? dayLabel(fu.due_date) : "later"}${fu.person ? ` · waiting on ${fu.person}` : ""}` });
        } catch (e) {
          toast({ text: errorText(e), kind: "error" });
        }
      };
      toast({
        text: next ? `Done. Next one: ${dayLabel(next.due_date!)}` : `Done: ${t.title}`,
        actions: [
          { label: "Undo", onClick: async () => { await api.post(`/api/tasks/${t.id}/undo-close`); bump(); } },
          { label: "Follow up in 3 days", chip: true, onClick: () => addFollowUp(3) },
          { label: "In a week", chip: true, onClick: () => addFollowUp(7) },
          { label: "Add note", chip: true, onClick: () => setNoteFor(res.task) },
        ],
      });
    } catch (e) {
      if (e instanceof OfflineError) {
        await queue({ kind: "close", taskId: t.id });
        toast({ text: "Closed offline. It will sync when you're back online." });
      } else toast({ text: errorText(e), kind: "error" });
    }
  }, [bump, toast, setNoteFor]);

  const snooze = useCallback(async (t: ShortTask | Task, preset: string, date?: string) => {
    try {
      const r = await api.post<Task>(`/api/tasks/${t.id}/snooze`, { preset, ...(date ? { date } : {}) });
      bump();
      const where = preset === "1h" ? "for an hour" : preset === "3h" ? "for 3 hours" : preset === "tonight" ? "till tonight"
        : r.due_date ? `to ${dayLabel(r.due_date)}` : "";
      toast({ text: `Snoozed ${where}` });
    } catch (e) {
      if (e instanceof OfflineError && preset !== "date") {
        await queue({ kind: "snooze", taskId: t.id, preset });
        toast({ text: "Snoozed offline. It will sync later." });
      } else toast({ text: errorText(e), kind: "error" });
    }
  }, [bump, toast]);

  const run = useCallback(async (path: string, body: unknown, ok: string) => {
    try {
      await api.post(path, body);
      bump();
      if (ok) toast({ text: ok });
      return true;
    } catch (e) {
      toast({ text: errorText(e), kind: "error" });
      return false;
    }
  }, [bump, toast]);

  return {
    complete,
    snooze,
    focus: (t: ShortTask | Task, on: boolean) => run(`/api/tasks/${t.id}/focus`, { on }, on ? "Added to Top 3" : "Removed from Top 3"),
    drop: async (t: ShortTask | Task) => {
      const ok = await run(`/api/tasks/${t.id}/drop`, {}, "");
      if (ok) toast({ text: "Dropped", actions: [{ label: "Undo", onClick: () => run(`/api/tasks/${t.id}/reopen`, {}, "Back on your list") }] });
    },
    keep: (t: ShortTask | Task) => run(`/api/tasks/${t.id}/keep`, {}, "Kept. I'll check again in a couple of weeks."),
    nudged: (t: ShortTask | Task) => run(`/api/tasks/${t.id}/nudged`, {}, "Noted. I'll remind you again if there's no reply."),
    reopen: (t: ShortTask | Task) => run(`/api/tasks/${t.id}/reopen`, {}, "Reopened"),
  };
}
