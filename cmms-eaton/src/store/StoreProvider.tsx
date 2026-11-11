import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { Asset, AuditEntry, Line, Part, Snapshot, User } from "../types";
import { LOCK_MINUTES, MAX_FAILED_LOGINS, verifyPassword } from "../lib/auth";
import { newId, nowIso } from "../lib/ids";
import { FolderAdapter, LocalAdapter, readStoredMode, type StorageAdapter, type StorageMode, writeStoredMode } from "./adapters";
import { buildDemoSnapshot } from "./seed";
import { emptySnapshot } from "./snapshot";

export interface AuditInfo {
  entity: string;
  entityId: string;
  action: string;
  summary: string;
}

export interface StorageStatus {
  mode: StorageMode;
  folderName: string | null;
  needsReconnect: boolean;
  error: string | null;
  lastSavedAt: string | null;
  saving: boolean;
  folderSupported: boolean;
}

export type LoginResult = { ok: true } | { ok: false; message: string };

export interface StoreValue {
  ready: boolean;
  snapshot: Snapshot;
  user: User | null;
  storage: StorageStatus;
  usersById: Map<string, User>;
  assetsById: Map<string, Asset>;
  partsById: Map<string, Part>;
  linesById: Map<string, Line>;
  login(employeeId: string, password: string): Promise<LoginResult>;
  logout(): void;
  /** Apply a change to a copy of the snapshot. The function may return an audit summary override. */
  mutate(fn: (draft: Snapshot) => void, audit?: AuditInfo): void;
  replaceSnapshot(next: Snapshot, audit?: AuditInfo): void;
  setStorageMode(mode: StorageMode): Promise<void>;
  connectFolder(): Promise<void>;
  reconnectFolder(): Promise<void>;
  disconnectFolder(): Promise<void>;
  reloadFromStorage(): Promise<void>;
  resetToDemo(): Promise<void>;
  startFresh(): Promise<void>;
}

const StoreContext = createContext<StoreValue | null>(null);
const SESSION_KEY = "cmms-eaton:session";
const POLL_MS = 15_000;

function readSession(): string | null {
  try {
    return sessionStorage.getItem(SESSION_KEY);
  } catch {
    return null;
  }
}

function writeSession(userId: string | null): void {
  try {
    if (userId) sessionStorage.setItem(SESSION_KEY, userId);
    else sessionStorage.removeItem(SESSION_KEY);
  } catch {
    /* storage blocked */
  }
}

function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

export function StoreProvider({ children }: { children: ReactNode }): ReactNode {
  const [snapshot, setSnapshot] = useState<Snapshot>(() => emptySnapshot());
  const [ready, setReady] = useState(false);
  const [userId, setUserId] = useState<string | null>(() => readSession());
  const [storage, setStorage] = useState<StorageStatus>(() => ({
    mode: readStoredMode(),
    folderName: null,
    needsReconnect: false,
    error: null,
    lastSavedAt: null,
    saving: false,
    folderSupported: FolderAdapter.supported(),
  }));

  const adapterRef = useRef<StorageAdapter>(new LocalAdapter());
  const folderRef = useRef<FolderAdapter>(new FolderAdapter());
  const skipNextSaveRef = useRef(true);
  const saveTimerRef = useRef<number | null>(null);
  const userIdRef = useRef<string | null>(userId);
  userIdRef.current = userId;

  const patchStorage = useCallback((patch: Partial<StorageStatus>) => setStorage((s) => ({ ...s, ...patch })), []);

  /** Load from the adapter; seed demo data when the store is empty. */
  const loadFrom = useCallback(
    async (adapter: StorageAdapter, seedIfEmpty: boolean): Promise<void> => {
      let loaded: Snapshot | null = null;
      try {
        loaded = await adapter.load();
        patchStorage({ error: null });
      } catch (err) {
        patchStorage({ error: errorMessage(err) });
      }
      if (!loaded && seedIfEmpty) {
        loaded = await buildDemoSnapshot();
        try {
          await adapter.save(loaded);
        } catch (err) {
          patchStorage({ error: errorMessage(err) });
        }
      }
      skipNextSaveRef.current = true;
      setSnapshot(loaded ?? emptySnapshot());
    },
    [patchStorage],
  );

  // Initial load.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const mode = readStoredMode();
      if (mode === "folder" && FolderAdapter.supported()) {
        const state = await folderRef.current.restore();
        const name = folderRef.current.folderName ?? (await folderRef.current.storedFolderName());
        if (state === "granted") {
          adapterRef.current = folderRef.current;
          patchStorage({ mode: "folder", folderName: name, needsReconnect: false });
          await loadFrom(folderRef.current, true);
        } else {
          // Folder chosen earlier but the browser wants a click before giving access again.
          adapterRef.current = new LocalAdapter();
          patchStorage({ mode: "folder", folderName: name, needsReconnect: true, error: state === "none" ? "Shared folder not chosen yet" : null });
          await loadFrom(adapterRef.current, true);
        }
      } else if (mode === "sharepoint") {
        adapterRef.current = new LocalAdapter();
        patchStorage({ mode: "sharepoint", error: "SharePoint online is not connected yet; working with the data on this device." });
        await loadFrom(adapterRef.current, true);
      } else {
        adapterRef.current = new LocalAdapter();
        patchStorage({ mode: "local" });
        await loadFrom(adapterRef.current, true);
      }
      if (!cancelled) setReady(true);
    })();
    return () => {
      cancelled = true;
    };
  }, [loadFrom, patchStorage]);

  // Persist on change (debounced).
  useEffect(() => {
    if (!ready) return;
    if (skipNextSaveRef.current) {
      skipNextSaveRef.current = false;
      return;
    }
    if (saveTimerRef.current) window.clearTimeout(saveTimerRef.current);
    saveTimerRef.current = window.setTimeout(async () => {
      patchStorage({ saving: true });
      try {
        await adapterRef.current.save(snapshot);
        patchStorage({ saving: false, lastSavedAt: nowIso(), error: null });
      } catch (err) {
        patchStorage({ saving: false, error: `Could not save: ${errorMessage(err)}` });
      }
    }, 400);
    return () => {
      if (saveTimerRef.current) window.clearTimeout(saveTimerRef.current);
    };
  }, [snapshot, ready, patchStorage]);

  // Pick up changes other people wrote to the shared folder.
  useEffect(() => {
    if (!ready || adapterRef.current.mode !== "folder") return;
    const id = window.setInterval(async () => {
      try {
        const next = await adapterRef.current.pollExternal?.();
        if (next) {
          skipNextSaveRef.current = true;
          setSnapshot(next);
        }
      } catch (err) {
        patchStorage({ error: `Shared folder check failed: ${errorMessage(err)}` });
      }
    }, POLL_MS);
    return () => window.clearInterval(id);
  }, [ready, storage.mode, storage.needsReconnect, patchStorage]);

  const mutate = useCallback((fn: (draft: Snapshot) => void, audit?: AuditInfo) => {
    setSnapshot((prev) => {
      const draft = structuredClone(prev);
      fn(draft);
      const at = nowIso();
      draft.updatedAt = at;
      if (audit) {
        const entry: AuditEntry = { id: newId(), at, userId: userIdRef.current, ...audit };
        draft.audit.unshift(entry);
        if (draft.audit.length > 5000) draft.audit.length = 5000;
      }
      return draft;
    });
  }, []);

  const replaceSnapshot = useCallback((next: Snapshot, audit?: AuditInfo) => {
    const copy = structuredClone(next);
    const at = nowIso();
    copy.updatedAt = at;
    if (audit) copy.audit.unshift({ id: newId(), at, userId: userIdRef.current, ...audit });
    setSnapshot(copy);
  }, []);

  const login = useCallback(
    async (employeeId: string, password: string): Promise<LoginResult> => {
      const id = employeeId.trim().toLowerCase();
      const user = snapshot.users.find((u) => u.employeeId.toLowerCase() === id);
      const generic = { ok: false as const, message: "Invalid employee ID or password" };
      if (!user || !user.active) return generic;
      if (user.lockedUntil && new Date(user.lockedUntil).getTime() > Date.now()) {
        const minutes = Math.ceil((new Date(user.lockedUntil).getTime() - Date.now()) / 60_000);
        return { ok: false, message: `Account locked after ${MAX_FAILED_LOGINS} failed attempts. Try again in ${minutes} min.` };
      }
      const ok = await verifyPassword(password, user.passwordSalt, user.passwordHash);
      if (!ok) {
        mutate((d) => {
          const u = d.users.find((x) => x.id === user.id);
          if (!u) return;
          u.failedAttempts += 1;
          if (u.failedAttempts >= MAX_FAILED_LOGINS) {
            u.lockedUntil = new Date(Date.now() + LOCK_MINUTES * 60_000).toISOString();
            u.failedAttempts = 0;
          }
        });
        return generic;
      }
      mutate(
        (d) => {
          const u = d.users.find((x) => x.id === user.id);
          if (!u) return;
          u.failedAttempts = 0;
          u.lockedUntil = null;
          u.lastLoginAt = nowIso();
        },
        { entity: "auth", entityId: user.id, action: "login", summary: `${user.name} logged in` },
      );
      writeSession(user.id);
      setUserId(user.id);
      return { ok: true };
    },
    [snapshot.users, mutate],
  );

  const logout = useCallback(() => {
    writeSession(null);
    setUserId(null);
  }, []);

  const setStorageMode = useCallback(
    async (mode: StorageMode) => {
      writeStoredMode(mode);
      if (mode === "local") {
        adapterRef.current = new LocalAdapter();
        patchStorage({ mode, needsReconnect: false, error: null, folderName: null });
        // Keep the data the user is looking at: write it to this device.
        skipNextSaveRef.current = true;
        await adapterRef.current.save(snapshot);
        patchStorage({ lastSavedAt: nowIso() });
      } else if (mode === "sharepoint") {
        adapterRef.current = new LocalAdapter();
        patchStorage({ mode, needsReconnect: false, error: "SharePoint online is not connected yet; data stays on this device until the connection is set up." });
      } else {
        patchStorage({ mode, needsReconnect: !folderRef.current.connected, error: null });
      }
    },
    [snapshot, patchStorage],
  );

  const connectFolder = useCallback(async () => {
    try {
      const name = await folderRef.current.connect();
      writeStoredMode("folder");
      adapterRef.current = folderRef.current;
      patchStorage({ mode: "folder", folderName: name, needsReconnect: false, error: null });
      const existing = await folderRef.current.load();
      if (existing) {
        skipNextSaveRef.current = true;
        setSnapshot(existing);
      } else {
        // First device to use the folder seeds it with the data it already has.
        await folderRef.current.save(snapshot);
        patchStorage({ lastSavedAt: nowIso() });
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      patchStorage({ error: errorMessage(err) });
    }
  }, [snapshot, patchStorage]);

  const reconnectFolder = useCallback(async () => {
    try {
      const ok = await folderRef.current.reconnect();
      if (!ok) {
        patchStorage({ error: "Folder access was not granted" });
        return;
      }
      adapterRef.current = folderRef.current;
      patchStorage({ needsReconnect: false, error: null, folderName: folderRef.current.folderName });
      await loadFrom(folderRef.current, false);
    } catch (err) {
      patchStorage({ error: errorMessage(err) });
    }
  }, [loadFrom, patchStorage]);

  const disconnectFolder = useCallback(async () => {
    await folderRef.current.disconnect();
    writeStoredMode("local");
    adapterRef.current = new LocalAdapter();
    patchStorage({ mode: "local", folderName: null, needsReconnect: false, error: null });
    skipNextSaveRef.current = true;
    await adapterRef.current.save(snapshot);
  }, [snapshot, patchStorage]);

  const reloadFromStorage = useCallback(async () => {
    await loadFrom(adapterRef.current, false);
  }, [loadFrom]);

  const resetToDemo = useCallback(async () => {
    const demo = await buildDemoSnapshot();
    setSnapshot(demo);
    writeSession(null);
    setUserId(null);
  }, []);

  const startFresh = useCallback(async () => {
    setSnapshot(emptySnapshot());
    writeSession(null);
    setUserId(null);
  }, []);

  const user = useMemo(() => {
    const u = userId ? snapshot.users.find((x) => x.id === userId) : undefined;
    return u && u.active ? u : null;
  }, [snapshot.users, userId]);

  // Deactivated users lose their session immediately.
  useEffect(() => {
    if (ready && userId && !user) {
      writeSession(null);
      setUserId(null);
    }
  }, [ready, userId, user]);

  const usersById = useMemo(() => new Map(snapshot.users.map((u) => [u.id, u])), [snapshot.users]);
  const assetsById = useMemo(() => new Map(snapshot.assets.map((a) => [a.id, a])), [snapshot.assets]);
  const partsById = useMemo(() => new Map(snapshot.parts.map((p) => [p.id, p])), [snapshot.parts]);
  const linesById = useMemo(() => new Map(snapshot.lines.map((l) => [l.id, l])), [snapshot.lines]);

  const value: StoreValue = {
    ready,
    snapshot,
    user,
    storage,
    usersById,
    assetsById,
    partsById,
    linesById,
    login,
    logout,
    mutate,
    replaceSnapshot,
    setStorageMode,
    connectFolder,
    reconnectFolder,
    disconnectFolder,
    reloadFromStorage,
    resetToDemo,
    startFresh,
  };

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStore(): StoreValue {
  const ctx = useContext(StoreContext);
  if (!ctx) throw new Error("useStore must be used inside StoreProvider");
  return ctx;
}

/** The logged-in user; pages behind the auth guard can rely on it. */
export function useCurrentUser(): User {
  const { user } = useStore();
  if (!user) throw new Error("No user logged in");
  return user;
}
