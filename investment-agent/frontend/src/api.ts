export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

let onUnauthorized: () => void = () => {};
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const init: RequestInit = { method, credentials: "same-origin", headers: {} };
  if (body instanceof FormData) {
    init.body = body;
  } else if (body !== undefined) {
    (init.headers as Record<string, string>)["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }
  const res = await fetch(`/api${path}`, init);
  if (res.status === 401 && !path.startsWith("/auth/")) onUnauthorized();
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = typeof j.detail === "string" ? j.detail : Array.isArray(j.detail) ? j.detail.map((d: { msg: string }) => d.msg).join("; ") : msg;
    } catch {
      /* not JSON */
    }
    throw new ApiError(res.status, msg);
  }
  return (await res.json()) as T;
}

export const api = {
  get: <T,>(p: string) => request<T>("GET", p),
  post: <T,>(p: string, b?: unknown) => request<T>("POST", p, b ?? {}),
  put: <T,>(p: string, b: unknown) => request<T>("PUT", p, b),
  patch: <T,>(p: string, b: unknown) => request<T>("PATCH", p, b),
  del: <T,>(p: string) => request<T>("DELETE", p),
  upload: <T,>(p: string, form: FormData) => request<T>("POST", p, form),
};

export const enc = (symbol: string) => encodeURIComponent(symbol);

export type ChatEvent =
  | { type: "text"; text: string }
  | { type: "tool"; id: string; name: string; input: Record<string, unknown> }
  | { type: "tool_done"; id: string; name: string; error: boolean }
  | { type: "done" }
  | { type: "error"; message: string };

/** POST a chat message and read the Server-Sent Events stream. */
export async function streamChat(sessionId: number, text: string, onEvent: (e: ChatEvent) => void, signal?: AbortSignal) {
  const res = await fetch(`/api/chat/sessions/${sessionId}/messages`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
    signal,
  });
  if (res.status === 401) onUnauthorized();
  if (!res.ok || !res.body) throw new ApiError(res.status, "Chat request failed");
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const chunk = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      for (const line of chunk.split("\n")) {
        if (line.startsWith("data: ")) {
          try {
            onEvent(JSON.parse(line.slice(6)) as ChatEvent);
          } catch {
            /* ignore malformed line */
          }
        }
      }
    }
  }
}
