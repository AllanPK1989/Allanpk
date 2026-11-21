import { useState } from "react";
import { api } from "../api";
import { Card, Empty, ErrorNote, Spinner, useAsync } from "../components";
import type { NewsItem } from "../types";
import { NewsList } from "./Instrument";

export default function News() {
  const [impact, setImpact] = useState<"" | "high" | "medium" | "low">("");
  const [days, setDays] = useState(3);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const params = new URLSearchParams({ days: String(days), limit: "100" });
  if (impact) params.set("impact", impact);
  if (q.trim().length >= 2) params.set("q", q.trim());
  const news = useAsync(() => api.get<{ news: NewsItem[] }>(`/news?${params}`), [impact, days, q.trim().length >= 2 ? q : ""]);
  const refresh = async () => {
    setBusy(true);
    try {
      const r = await api.post<{ new: number; triaged: number }>("/news/refresh");
      setMsg(`${r.new} new articles, ${r.triaged} summarised.`);
      news.reload();
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="page">
      <div className="page-head">
        <h1>News</h1>
        <button className="btn" onClick={refresh} disabled={busy}>{busy ? "Collecting… (up to a minute)" : "Collect now"}</button>
      </div>
      <p className="muted">Collected for everything you follow plus Indian and US market feeds, then summarised and rated for impact by AI.</p>
      {msg && <div className="ok-note">{msg}</div>}
      <div className="filters">
        {(["", "high", "medium", "low"] as const).map((i) => (
          <button key={i} className={`chip ${impact === i ? "active" : ""}`} onClick={() => setImpact(i)}>{i ? `${i} impact` : "All"}</button>
        ))}
        <select value={days} onChange={(e) => setDays(Number(e.target.value))} aria-label="Period">
          <option value={1}>24 hours</option><option value={3}>3 days</option><option value={7}>7 days</option><option value={30}>30 days</option>
        </select>
        <input type="search" placeholder="Filter headlines" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      <Card>
        {news.loading && <Spinner />}
        <ErrorNote error={news.error} />
        {news.data && news.data.news.length === 0 && <Empty>No news yet for this filter. Press “Collect now”.</Empty>}
        {news.data && <NewsList items={news.data.news} />}
      </Card>
    </div>
  );
}
