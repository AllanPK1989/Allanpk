import { api } from "./api";

function b64ToUint8(b64: string): Uint8Array<ArrayBuffer> {
  const pad = "=".repeat((4 - (b64.length % 4)) % 4);
  const raw = atob((b64 + pad).replace(/-/g, "+").replace(/_/g, "/"));
  const out = new Uint8Array(new ArrayBuffer(raw.length));
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i);
  return out;
}

export function pushSupported(): boolean {
  return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
}

export async function currentSubscription(): Promise<PushSubscription | null> {
  if (!pushSupported()) return null;
  const reg = await navigator.serviceWorker.getRegistration();
  return reg ? reg.pushManager.getSubscription() : null;
}

export async function enablePush(): Promise<void> {
  if (!pushSupported()) {
    throw new Error("This browser doesn't support push. On iPhone, add the app to the Home Screen first (Share → Add to Home Screen).");
  }
  const { enabled, public_key } = await api.get<{ enabled: boolean; public_key: string }>("/push/public-key");
  if (!enabled) throw new Error("Push isn't configured on the server yet (VAPID keys missing).");
  const perm = await Notification.requestPermission();
  if (perm !== "granted") throw new Error("Notifications were not allowed. Enable them in the browser's site settings.");
  const reg = await navigator.serviceWorker.ready;
  let sub = await reg.pushManager.getSubscription();
  if (!sub) {
    sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToUint8(public_key) });
  }
  const json = sub.toJSON() as { endpoint: string; keys: { p256dh: string; auth: string } };
  await api.post("/push/subscribe", { endpoint: json.endpoint, keys: json.keys, user_agent: navigator.userAgent.slice(0, 250) });
}

export async function disablePush(): Promise<void> {
  const sub = await currentSubscription();
  if (sub) {
    await api.post("/push/unsubscribe", { endpoint: sub.endpoint });
    await sub.unsubscribe();
  }
}
