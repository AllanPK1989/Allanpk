/// <reference lib="webworker" />
// Service worker: keeps the app shell available offline and shows push reminders.
// Done / Snooze / Tomorrow buttons on a notification act straight away using a signed token,
// so they work from the lock screen without opening the app.
import { cleanupOutdatedCaches, createHandlerBoundToURL, precacheAndRoute } from "workbox-precaching";
import { NavigationRoute, registerRoute } from "workbox-routing";
import { createStore, set } from "idb-keyval";

declare const self: ServiceWorkerGlobalScope;

precacheAndRoute(self.__WB_MANIFEST);
cleanupOutdatedCaches();
registerRoute(new NavigationRoute(createHandlerBoundToURL("/index.html"), { denylist: [/^\/api\//] }));

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));

interface PushPayload {
  title: string;
  body: string;
  url?: string;
  tag?: string;
  kind?: string;
  task_id?: number;
  token?: string;
  actions?: { action: string; title: string }[];
}

self.addEventListener("push", (event) => {
  let data: PushPayload;
  try {
    data = event.data?.json() as PushPayload;
  } catch {
    data = { title: "Nudge", body: event.data?.text() ?? "" };
  }
  const max = (Notification as unknown as { maxActions?: number }).maxActions ?? 2;
  const options: NotificationOptions & { actions?: { action: string; title: string }[]; renotify?: boolean } = {
    body: data.body,
    tag: data.tag,
    icon: "/icon-192.png",
    badge: "/icon-192.png",
    data: { url: data.url ?? "/", token: data.token, taskId: data.task_id },
    actions: (data.actions ?? []).slice(0, max),
    renotify: true,
  };
  event.waitUntil(self.registration.showNotification(data.title, options));
});

// Same store the app's offline queue reads (src/offline.ts), so the press syncs next time it opens.
const outbox = createStore("nudge", "outbox");
const OFFLINE_OPS: Record<string, (taskId: number) => Record<string, unknown>> = {
  done: (taskId) => ({ kind: "close", taskId }),
  snooze_1h: (taskId) => ({ kind: "snooze", taskId, preset: "1h" }),
  tomorrow: (taskId) => ({ kind: "snooze", taskId, preset: "tomorrow" }),
  nudged: (taskId) => ({ kind: "nudged", taskId }),
};

async function acknowledge(title: string, body: string) {
  await self.registration.showNotification(title, { body, tag: "nudge-ack", silent: true } as NotificationOptions);
  setTimeout(() => self.registration.getNotifications({ tag: "nudge-ack" }).then((ns) => ns.forEach((x) => x.close())), 5000);
}

async function openApp(url: string) {
  const all = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
  for (const c of all) {
    if ("focus" in c) {
      await c.focus();
      if ("navigate" in c) await (c as WindowClient).navigate(url).catch(() => {});
      return;
    }
  }
  await self.clients.openWindow(url);
}

self.addEventListener("notificationclick", (event) => {
  const n = event.notification;
  const { url, token, taskId } = (n.data ?? {}) as { url: string; token?: string; taskId?: number };
  n.close();
  if (event.action && token) {
    event.waitUntil((async () => {
      const done: Record<string, string> = {
        done: "Marked done", snooze_1h: "Snoozed for an hour", tomorrow: "Moved to tomorrow", nudged: "Noted. I'll remind you again later",
      };
      let res: Response;
      try {
        res = await fetch("/api/push/action", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token, action: event.action }),
        });
      } catch {
        // Server not reachable (for example Nudge runs at home and you're out): keep the press.
        const make = OFFLINE_OPS[event.action];
        if (make && typeof taskId === "number") {
          const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
          await set(id, { id, at: new Date().toISOString(), op: make(taskId) }, outbox);
          await acknowledge(done[event.action] ?? "Saved", `${n.title}. Saved on your phone; it syncs when Nudge can reach your server.`);
        } else await openApp(url);
        return;
      }
      if (res.ok) await acknowledge(done[event.action] ?? "Done", n.title);
      else await openApp(url); // expired or already closed: open the task instead
    })());
    return;
  }
  event.waitUntil(openApp(url));
});
