import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { api, setToken, setUnauthorizedHandler } from "./api";
import type { Meta, User } from "./api";
import { translate } from "./i18n";
import type { Lang, TKey } from "./i18n";
import { queued, syncQueue } from "./offline";

const IDLE_MINUTES_SHARED = 10;

interface AppState {
  user: User | null;
  shared: boolean;
  lang: Lang;
  meta: Meta | null;
  online: boolean;
  queueCount: number;
  toastText: string;
  t: (key: TKey, vars?: Record<string, string | number>) => string;
  setLang: (lang: Lang) => void;
  login: (token: string, user: User, shared: boolean) => void;
  logout: (message?: string) => void;
  toast: (text: string) => void;
  sync: () => Promise<void>;
  sessionFinished: () => void;
}

const Ctx = createContext<AppState | null>(null);

function readStored(): { token: string; user: User; shared: boolean } | null {
  try {
    const raw = sessionStorage.getItem("thunai-auth") ?? localStorage.getItem("thunai-auth");
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function AppProvider({ children }: { children: ReactNode }) {
  const stored = readStored();
  if (stored) setToken(stored.token);
  const [user, setUser] = useState<User | null>(stored?.user ?? null);
  const [shared, setShared] = useState(stored?.shared ?? false);
  const [lang, setLangState] = useState<Lang>(
    (localStorage.getItem("thunai-lang") as Lang) || stored?.user.preferred_language || "ta",
  );
  const [meta, setMeta] = useState<Meta | null>(null);
  const [online, setOnline] = useState(navigator.onLine);
  const [queueCount, setQueueCount] = useState(0);
  const [toastText, setToastText] = useState("");
  const toastTimer = useRef<number | undefined>(undefined);

  const toast = useCallback((text: string) => {
    setToastText(text);
    window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToastText(""), 3500);
  }, []);

  const logout = useCallback(
    (message?: string) => {
      sessionStorage.removeItem("thunai-auth");
      localStorage.removeItem("thunai-auth");
      setToken(null);
      setUser(null);
      if (message) toast(message);
    },
    [toast],
  );

  const login = useCallback((token: string, u: User, isShared: boolean) => {
    setToken(token);
    const value = JSON.stringify({ token, user: u, shared: isShared });
    // Shared devices keep the login only for this browser tab session.
    if (isShared) sessionStorage.setItem("thunai-auth", value);
    else localStorage.setItem("thunai-auth", value);
    setUser(u);
    setShared(isShared);
    setLangState(u.preferred_language);
    localStorage.setItem("thunai-lang", u.preferred_language);
  }, []);

  const setLang = useCallback(
    (value: Lang) => {
      setLangState(value);
      localStorage.setItem("thunai-lang", value);
      if (user && !shared) api.patch("/api/auth/me", { preferred_language: value }).catch(() => {});
    },
    [user, shared],
  );

  const refreshQueue = useCallback(async () => setQueueCount((await queued()).length), []);

  const sync = useCallback(async () => {
    if (!user) return;
    const sent = await syncQueue();
    if (sent) toast(translate(lang, "saved"));
    await refreshQueue();
  }, [user, lang, toast, refreshQueue]);

  const sessionFinished = useCallback(() => {
    if (shared) window.setTimeout(() => logout(translate(lang, "logged_out_shared")), 4000);
  }, [shared, logout, lang]);

  useEffect(() => {
    setUnauthorizedHandler(() => logout());
    api.get<Meta>("/api/meta").then(setMeta).catch(() => {});
  }, [logout]);

  useEffect(() => {
    const up = () => {
      setOnline(true);
      void sync();
    };
    const down = () => setOnline(false);
    const q = () => void refreshQueue();
    window.addEventListener("online", up);
    window.addEventListener("offline", down);
    window.addEventListener("thunai-queue", q);
    void refreshQueue();
    if (navigator.onLine) void sync();
    return () => {
      window.removeEventListener("online", up);
      window.removeEventListener("offline", down);
      window.removeEventListener("thunai-queue", q);
    };
  }, [sync, refreshQueue]);

  // Shared devices: log out after a few idle minutes.
  useEffect(() => {
    if (!user || !shared) return;
    let timer = window.setTimeout(() => logout(translate(lang, "logged_out_shared")), IDLE_MINUTES_SHARED * 60_000);
    const reset = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => logout(translate(lang, "logged_out_shared")), IDLE_MINUTES_SHARED * 60_000);
    };
    const events = ["pointerdown", "keydown"];
    events.forEach((e) => window.addEventListener(e, reset));
    return () => {
      window.clearTimeout(timer);
      events.forEach((e) => window.removeEventListener(e, reset));
    };
  }, [user, shared, logout, lang]);

  const t = useCallback((key: TKey, vars?: Record<string, string | number>) => translate(lang, key, vars), [lang]);

  const value = useMemo(
    () => ({ user, shared, lang, meta, online, queueCount, toastText, t, setLang, login, logout, toast, sync, sessionFinished }),
    [user, shared, lang, meta, online, queueCount, toastText, t, setLang, login, logout, toast, sync, sessionFinished],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useApp(): AppState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useApp outside AppProvider");
  return ctx;
}
