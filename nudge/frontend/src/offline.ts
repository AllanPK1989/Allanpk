// Offline support.
// - Reads: the last good copy of each screen is kept, so the app opens without a connection.
// - Writes: quick adds, closes, snoozes and voice notes made offline wait in IndexedDB and are sent
//   when the connection comes back. Voice notes then land in the Inbox for you to check.
import { createStore, del, entries, get, set } from "idb-keyval";
import { api, OfflineError } from "./api";

const outbox = createStore("nudge", "outbox");
const cache = createStore("nudge-cache", "screens");

export type QueuedOp =
  | { kind: "create"; body: Record<string, unknown> }
  | { kind: "close"; taskId: number }
  | { kind: "snooze"; taskId: number; preset: string }
  | { kind: "nudged"; taskId: number }
  | { kind: "voice"; audio: Blob };

interface Queued {
  id: string;
  at: string;
  op: QueuedOp;
}

function newId(): string {
  return crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export async function queue(op: QueuedOp): Promise<void> {
  const id = newId();
  await set(id, { id, at: new Date().toISOString(), op } satisfies Queued, outbox);
  window.dispatchEvent(new Event("nudge-queue"));
}

export async function queuedCount(): Promise<number> {
  try {
    return (await entries(outbox)).length;
  } catch {
    return 0;
  }
}

let syncing = false;

/** Send everything waiting. Returns how many were sent. */
export async function syncQueue(): Promise<number> {
  if (syncing || !navigator.onLine) return 0;
  syncing = true;
  let sent = 0;
  try {
    const items = (await entries<string, Queued>(outbox)).map(([, v]) => v).sort((a, b) => a.at.localeCompare(b.at));
    for (const item of items) {
      try {
        const { op } = item;
        if (op.kind === "create") await api.post("/api/tasks", op.body);
        else if (op.kind === "close") await api.post(`/api/tasks/${op.taskId}/close`, {});
        else if (op.kind === "snooze") await api.post(`/api/tasks/${op.taskId}/snooze`, { preset: op.preset });
        else if (op.kind === "nudged") await api.post(`/api/tasks/${op.taskId}/nudged`);
        else if (op.kind === "voice") {
          const form = new FormData();
          form.append("audio", op.audio, `voice.${op.audio.type.includes("mp4") ? "m4a" : "webm"}`);
          await api.upload("/api/assistant/voice?auto=true", form);
        }
        await del(item.id, outbox);
        sent++;
      } catch (e) {
        if (e instanceof OfflineError) break;
        await del(item.id, outbox); // the server refused it (e.g. the task was deleted); don't retry forever
      }
    }
  } finally {
    syncing = false;
    window.dispatchEvent(new Event("nudge-queue"));
  }
  return sent;
}

export async function cachedGet<T>(path: string): Promise<{ data: T; stale: boolean }> {
  try {
    const data = await api.get<T>(path);
    set(path, data, cache).catch(() => {});
    return { data, stale: false };
  } catch (e) {
    if (e instanceof OfflineError) {
      const saved = await get<T>(path, cache).catch(() => undefined);
      if (saved !== undefined) return { data: saved, stale: true };
    }
    throw e;
  }
}
