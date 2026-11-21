import { Link } from "react-router-dom";
import { api, enc } from "../api";
import { Badge, Card, Change, DemoBanner, Empty, ErrorNote, Spinner, useAsync } from "../components";
import { ago, CLASS_LABEL, compactInr, money, num, priceDigits } from "../format";
import type { DigestSummary, Instrument, Overview, Portfolio } from "../types";

type Alert = { id: number; kind: string; title: string; body: string; url: string; created_at: string };

export default function Dashboard() {
  const ov = useAsync(() => api.get<Overview>("/market/overview"), []);
  const pf = useAsync(() => api.get<Portfolio>("/portfolio"), []);
  const wl = useAsync(() => api.get<{ instruments: Instrument[] }>("/instruments"), []);
  const dg = useAsync(() => api.get<{ digests: DigestSummary[] }>("/digests?limit=5"), []);
  const al = useAsync(() => api.get<{ alerts: Alert[] }>("/alerts"), []);

  const groups = ["India", "Global", "Currencies", "Commodities", "Rates", "Crypto"];
  const t = pf.data?.totals;

  return (
    <div className="page">
      <DemoBanner show={!!ov.data?.demo} />
      <div className="grid-2">
        <Card title="Your portfolio" actions={<Link to="/portfolio" className="link">Open</Link>}>
          {pf.loading && <Spinner />}
          <ErrorNote error={pf.error} />
          {t && (t.value > 0 ? (
            <div className="kpis">
              <div className="kpi big">
                <span className="kpi-label">Value</span>
                <span className="kpi-value">{compactInr(t.value)}</span>
              </div>
              <div className="kpi">
                <span className="kpi-label">Today</span>
                <span className={`kpi-value ${t.day_change >= 0 ? "up" : "down"}`}>{compactInr(t.day_change)}</span>
                <Change v={t.day_change_pct ?? null} />
              </div>
              <div className="kpi">
                <span className="kpi-label">Total P&amp;L</span>
                <span className={`kpi-value ${t.pnl >= 0 ? "up" : "down"}`}>{compactInr(t.pnl)}</span>
                <Change v={t.pnl_pct} />
              </div>
              <div className="kpi">
                <span className="kpi-label">XIRR</span>
                <span className="kpi-value">{t.xirr_pct === null ? "–" : `${t.xirr_pct.toFixed(1)}%`}</span>
              </div>
            </div>
          ) : (
            <Empty>No holdings yet. <Link to="/portfolio">Add trades or import a broker CSV.</Link></Empty>
          ))}
        </Card>
        <Card title="Latest digest" actions={<Link to="/digests" className="link">All digests</Link>}>
          {dg.data?.digests.filter((d) => d.kind !== "alert").slice(0, 3).map((d) => (
            <Link key={d.id} to={`/digests/${d.id}`} className="row-link">
              <span>{d.title}</span>
              <span className="muted small">{ago(d.created_at)}</span>
            </Link>
          ))}
          {dg.data && dg.data.digests.filter((d) => d.kind !== "alert").length === 0 && (
            <Empty>No digests yet. They arrive each morning, evening and Sunday, or <Link to="/digests">run one now</Link>.</Empty>
          )}
        </Card>
      </div>

      <Card title="Markets">
        {ov.loading && <Spinner />}
        <ErrorNote error={ov.error} />
        {ov.data && (
          <div className="market-groups">
            {groups.map((g) => {
              const rows = ov.data!.markets.filter((m) => m.group === g && m.price !== null);
              if (!rows.length) return null;
              return (
                <div key={g} className="market-group">
                  <h3>{g}</h3>
                  {rows.map((m) => (
                    <Link key={m.symbol} to={`/instrument/${enc(m.symbol)}`} className="market-row"
                      onClick={() => api.post("/instruments", { symbol: m.symbol, name: m.label, asset_class: assetFor(m.symbol), region: g === "India" ? "IN" : "GLOBAL" })}>
                      <span>{m.label}</span>
                      <span className="num">{num(m.price, priceDigits(m.price))}</span>
                      <Change v={m.change_pct} />
                    </Link>
                  ))}
                </div>
              );
            })}
            {ov.data.rates.length > 0 && (
              <div className="market-group">
                <h3>Macro</h3>
                {ov.data.rates.map((r) => (
                  <div key={r.id} className="market-row static">
                    <span>{r.label}</span>
                    <span className="num">{r.value.toFixed(2)}</span>
                    <span className="muted small">{r.date}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </Card>

      <div className="grid-2">
        <Card title="Followed" actions={<span className="muted small">Everything you search stays here</span>}>
          {wl.loading && <Spinner />}
          {wl.data && wl.data.instruments.length === 0 && <Empty>Search for anything above to start following it.</Empty>}
          <div className="watch">
            {wl.data?.instruments.map((i) => (
              <Link key={i.symbol} to={`/instrument/${enc(i.symbol)}`} className="watch-row">
                <div>
                  <div className="w-name">{i.pinned && <span className="star">★</span>}{i.name}</div>
                  <div className="muted small">{i.symbol} · {CLASS_LABEL[i.asset_class] ?? i.asset_class}{i.held ? " · held" : ""}</div>
                </div>
                <div className="w-right">
                  <div className="num">{money(i.quote?.price ?? null, i.quote?.currency || i.currency, priceDigits(i.quote?.price))}</div>
                  <Change v={i.quote?.change_pct} />
                </div>
              </Link>
            ))}
          </div>
        </Card>
        <Card title="Recent alerts" actions={<Link to="/alerts" className="link">All alerts</Link>}>
          {al.data?.alerts.slice(0, 8).map((a) => (
            <div key={a.id} className="alert-row">
              <Badge tone={a.kind === "price" ? "warn" : "info"}>{a.kind}</Badge>
              <div>
                <div>{a.title}</div>
                <div className="muted small">{a.body} · {ago(a.created_at)}</div>
              </div>
            </div>
          ))}
          {al.data && al.data.alerts.length === 0 && <Empty>No alerts yet. You'll get one when something you follow moves sharply or has big news.</Empty>}
        </Card>
      </div>
    </div>
  );
}

function assetFor(symbol: string): string {
  if (symbol.startsWith("CRYPTO:")) return "crypto";
  if (symbol.endsWith("=X")) return "forex";
  if (symbol.endsWith("=F")) return "commodity";
  if (symbol === "^TNX") return "bond";
  return "index";
}
