import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { Card, Empty, Spinner } from "../components";
import { CLASS_LABEL } from "../format";
import type { SearchResult } from "../types";

const IDEAS = ["HDFC Bank", "Infosys", "Nifty 50", "Parag Parikh Flexi Cap", "Apple", "NVIDIA", "Bitcoin", "Gold", "USD INR"];

export default function SearchPage() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();
  useEffect(() => {
    if (q.trim().length < 2) {
      setResults(null);
      return;
    }
    const t = setTimeout(() => {
      setBusy(true);
      api.get<{ results: SearchResult[] }>(`/search?q=${encodeURIComponent(q.trim())}`)
        .then((r) => setResults(r.results))
        .finally(() => setBusy(false));
    }, 350);
    return () => clearTimeout(t);
  }, [q]);
  const open = async (r: SearchResult) => {
    await api.post("/instruments", r);
    nav(`/instrument/${encodeURIComponent(r.symbol)}`);
  };
  const grouped = (results ?? []).reduce<Record<string, SearchResult[]>>((acc, r) => {
    (acc[r.asset_class] ??= []).push(r);
    return acc;
  }, {});
  return (
    <div className="page">
      <h1>Search</h1>
      <p className="muted">Stocks (NSE, BSE, US, global), ETFs, Indian mutual funds, crypto, commodities, currencies and indices. Anything you open is followed, so its news reaches your digests.</p>
      <input className="big-input" type="search" placeholder="Name or ticker" value={q} onChange={(e) => setQ(e.target.value)} autoFocus />
      {!q && (
        <div className="chips">
          {IDEAS.map((i) => <button key={i} className="chip" onClick={() => setQ(i)}>{i}</button>)}
        </div>
      )}
      {busy && <Spinner label="Searching" />}
      {results && results.length === 0 && !busy && <Empty>No matches. Try the company name or exchange ticker.</Empty>}
      {Object.entries(grouped).map(([cls, rows]) => (
        <Card key={cls} title={CLASS_LABEL[cls] ?? cls}>
          {rows.map((r) => (
            <button key={r.symbol} className="result-row" onClick={() => open(r)}>
              <span>{r.name}</span>
              <span className="muted small">{r.symbol}{r.exchange ? ` · ${r.exchange}` : ""}</span>
            </button>
          ))}
        </Card>
      ))}
    </div>
  );
}
