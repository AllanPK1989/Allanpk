import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, type ChatEvent, streamChat } from "../api";
import { Markdown, Spinner } from "../components";
import { ago } from "../format";

type ToolChip = { name: string; input?: Record<string, unknown>; done?: boolean; error?: boolean };
type Msg = { role: "user" | "assistant"; text: string; tools?: ToolChip[] };
type SessionRow = { id: number; title: string; updated_at: string };

const TOOL_LABEL: Record<string, string> = {
  search_instruments: "Searching", analyze_instrument: "Analysing", compare_instruments: "Comparing", get_price_history: "Reading price history",
  get_news: "Reading news", get_market_overview: "Checking markets", get_portfolio: "Reading your portfolio", get_portfolio_risk: "Measuring risk",
  get_tax_view: "Checking taxes", get_rebalance_plan: "Checking allocation", estimate_sale_tax: "Estimating tax", plan_goal: "Planning goal",
  plan_retirement: "Planning retirement", get_watchlist: "Reading your watchlist", follow_instrument: "Following",
};

const STARTERS = [
  "How is my portfolio positioned? Anything I should change?",
  "Compare HDFC Bank, ICICI Bank and Kotak Mahindra Bank. Which would you buy?",
  "Is now a good time to add gold? How much, given my portfolio?",
  "What moved the markets today and does it affect my holdings?",
  "I want ₹50 lakh in 12 years for my child's education. What SIP and which funds?",
  "Which of my holdings should I sell for tax-loss harvesting this year?",
];

function chipText(t: ToolChip): string {
  const arg = (t.input?.symbol as string) ?? (t.input?.query as string) ?? ((t.input?.symbols as string[]) ?? []).join(", ");
  return `${TOOL_LABEL[t.name] ?? t.name}${arg ? ` ${arg}` : ""}`;
}

export default function Chat() {
  const { sid } = useParams();
  const [params, setParams] = useSearchParams();
  const nav = useNavigate();
  const [sessions, setSessions] = useState<SessionRow[]>([]);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const createdHere = useRef<number | null>(null); // a session started in this view is already on screen
  const sessionId = sid ? Number(sid) : null;

  const loadSessions = () => api.get<{ sessions: SessionRow[] }>("/chat/sessions").then((r) => setSessions(r.sessions)).catch(() => {});
  useEffect(() => {
    loadSessions();
  }, []);
  useEffect(() => {
    setError("");
    if (!sessionId) {
      setMessages([]);
      return;
    }
    if (createdHere.current === sessionId) return;
    setLoading(true);
    api.get<{ messages: Msg[] }>(`/chat/sessions/${sessionId}`)
      .then((r) => setMessages(r.messages.map((m) => ({ ...m, tools: (m.tools ?? []).map((t) => ({ ...t, done: true })) }))))
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setLoading(false));
  }, [sessionId]);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);
  useEffect(() => {
    const q = params.get("q");
    if (q && !busy) {
      setParams({}, { replace: true });
      void send(q);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  const send = async (text: string) => {
    if (!text.trim() || busy) return;
    setError("");
    setBusy(true);
    let id = sessionId;
    try {
      if (!id) {
        id = (await api.post<{ id: number }>("/chat/sessions")).id;
        createdHere.current = id;
        nav(`/chat/${id}`, { replace: true });
      }
      setMessages((m) => [...m, { role: "user", text }, { role: "assistant", text: "", tools: [] }]);
      setInput("");
      const ctrl = new AbortController();
      abortRef.current = ctrl;
      await streamChat(id, text, (e: ChatEvent) => {
        setMessages((prev) => {
          const copy = [...prev];
          const last = { ...copy[copy.length - 1] };
          if (e.type === "text") last.text += e.text;
          if (e.type === "tool") {
            last.tools = [...(last.tools ?? []), { name: e.name, input: e.input }];
            if (last.text && !last.text.endsWith("\n\n")) last.text += "\n\n";
          }
          if (e.type === "tool_done") last.tools = (last.tools ?? []).map((t, i, arr) => (i === arr.findIndex((x) => x.name === e.name && !x.done) ? { ...t, done: true, error: e.error } : t));
          if (e.type === "error") setError(e.message);
          copy[copy.length - 1] = last;
          return copy;
        });
      }, ctrl.signal);
    } catch (e) {
      if ((e as Error).name !== "AbortError") setError((e as Error).message);
    } finally {
      setBusy(false);
      abortRef.current = null;
      loadSessions();
    }
  };
  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    void send(input);
  };
  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send(input);
    }
  };
  const remove = async (id: number) => {
    if (!window.confirm("Delete this conversation?")) return;
    await api.del(`/chat/sessions/${id}`);
    if (id === sessionId) nav("/chat");
    loadSessions();
  };

  return (
    <div className="chat-layout">
      <aside className="chat-sessions">
        <button className="btn primary block" onClick={() => nav("/chat")}>New conversation</button>
        {sessions.map((s) => (
          <div key={s.id} className={`session ${s.id === sessionId ? "active" : ""}`}>
            <button className="session-title" onClick={() => nav(`/chat/${s.id}`)}>{s.title}<span className="muted small">{ago(s.updated_at)}</span></button>
            <button className="link-btn danger" aria-label="Delete conversation" onClick={() => remove(s.id)}>×</button>
          </div>
        ))}
      </aside>
      <section className="chat-main">
        <div className="chat-scroll">
          {loading && <Spinner />}
          {!loading && messages.length === 0 && (
            <div className="chat-empty">
              <h1>Your investment adviser</h1>
              <p className="muted">Ask about any stock, fund, coin, commodity or currency, your portfolio, taxes or goals. It checks live data, your holdings and the latest news before answering.</p>
              <div className="starters">
                {STARTERS.map((s) => <button key={s} className="starter" onClick={() => send(s)}>{s}</button>)}
              </div>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.role}`}>
              {m.role === "assistant" && (m.tools?.length ?? 0) > 0 && (
                <div className="tool-chips">
                  {m.tools!.map((t, j) => <span key={j} className={`tool-chip ${t.done ? (t.error ? "err" : "done") : "run"}`}>{chipText(t)}</span>)}
                </div>
              )}
              {m.role === "assistant" ? (m.text ? <Markdown text={m.text} /> : busy && i === messages.length - 1 ? <Spinner label="Thinking" /> : null) : <p>{m.text}</p>}
            </div>
          ))}
          {error && <div className="error-note">{error}</div>}
          <div ref={endRef} />
        </div>
        <form className="chat-input" onSubmit={onSubmit}>
          <textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={onKey} rows={2} maxLength={8000}
            placeholder="Ask about a stock, fund, your portfolio, taxes, a goal…" aria-label="Message" />
          {busy ? <button type="button" className="btn" onClick={() => abortRef.current?.abort()}>Stop</button>
            : <button className="btn primary" disabled={!input.trim()}>Send</button>}
        </form>
      </section>
    </div>
  );
}
