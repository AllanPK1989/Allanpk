// Offline queue: logs created without network are kept in IndexedDB (with any voice recording)
// and sent to /api/logs/offline when the phone is back online. Each item carries a client_uuid
// so a retried send never creates a duplicate log.
import { createStore, del, entries, set } from "idb-keyval";
import { api, OfflineError } from "./api";

const store = createStore("thunai", "outbox");

export interface QueuedLog {
  id: string;
  createdAt: string;
  payload: Record<string, unknown> & { machine_no: string; client_uuid: string };
  audio?: Blob;
  language: string;
}

export function newId(): string {
  return crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export async function queueLog(item: Omit<QueuedLog, "id" | "createdAt">): Promise<void> {
  const id = item.payload.client_uuid;
  await set(id, { ...item, id, createdAt: new Date().toISOString() }, store);
  window.dispatchEvent(new Event("thunai-queue"));
}

export async function queued(): Promise<QueuedLog[]> {
  return (await entries<string, QueuedLog>(store)).map(([, v]) => v);
}

let syncing = false;

/** Send everything in the queue. Returns how many items were sent. */
export async function syncQueue(): Promise<number> {
  if (syncing || !navigator.onLine) return 0;
  syncing = true;
  let sent = 0;
  try {
    for (const item of await queued()) {
      const form = new FormData();
      form.append("payload", JSON.stringify(item.payload));
      form.append("language", item.language);
      if (item.audio) form.append("audio", item.audio, `voice.${item.audio.type.includes("mp4") ? "m4a" : "webm"}`);
      try {
        await api.upload("/api/logs/offline", form);
        await del(item.id, store);
        sent++;
      } catch (e) {
        if (e instanceof OfflineError) break; // still offline; try again later
        // Server refused this item (for example an unknown machine). Keep it for the user to see.
        console.warn("Offline log not accepted", item.id, e);
      }
    }
  } finally {
    syncing = false;
    window.dispatchEvent(new Event("thunai-queue"));
  }
  return sent;
}
