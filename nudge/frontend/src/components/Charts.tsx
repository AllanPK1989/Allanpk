// Dashboard charts. Specs: thin marks, 4px rounded data ends, 2px lines, ≥8px end dots with a
// surface ring, hairline solid grid, text in ink tokens (never the series colour), hover/focus
// tooltips, and a table view so no value is hover-only. Colours come from the validated palette.
import { useEffect, useRef, useState } from "react";
import { shortDate } from "../format";

function useWidth<T extends HTMLElement>(): [React.RefObject<T | null>, number] {
  const ref = useRef<T>(null);
  const [w, setW] = useState(320);
  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([e]) => setW(Math.max(200, Math.floor(e.contentRect.width))));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, w];
}

function niceMax(v: number): number {
  if (v <= 4) return 4;
  const pow = 10 ** Math.floor(Math.log10(v));
  for (const m of [1, 2, 2.5, 5, 10]) if (m * pow >= v) return m * pow;
  return 10 * pow;
}

function TableToggle({ show, onToggle }: { show: boolean; onToggle: () => void }) {
  return <button className="btn small ghost" onClick={onToggle} aria-pressed={show}>{show ? "Chart" : "Table"}</button>;
}

/** Open work by age. Ordinal one-hue ramp: older = darker on light, brighter on dark. */
export function AgingBars({ data, onPick }: { data: { label: string; count: number }[]; onPick?: (i: number) => void }) {
  const [table, setTable] = useState(false);
  const max = Math.max(1, ...data.map((d) => d.count));
  const total = data.reduce((s, d) => s + d.count, 0);
  return (
    <div>
      <div className="row" style={{ marginBottom: 8 }}>
        <div className="small muted grow">{total} open, by how long they've been waiting</div>
        <TableToggle show={table} onToggle={() => setTable(!table)} />
      </div>
      {table ? (
        <table className="data"><thead><tr><th>Age</th><th className="n">Tasks</th></tr></thead>
          <tbody>{data.map((d) => <tr key={d.label}><td>{d.label}</td><td className="n">{d.count}</td></tr>)}</tbody></table>
      ) : (
        <div role="list" aria-label="Open tasks by age">
          {data.map((d, i) => (
            <button key={d.label} className="hbar" role="listitem" style={{ width: "100%", background: "none", border: 0, padding: 0, cursor: onPick ? "pointer" : "default", color: "inherit" }}
              onClick={() => onPick?.(i)} aria-label={`${d.label}: ${d.count} tasks`}>
              <span className="muted" style={{ textAlign: "left" }}>{d.label}</span>
              <span className="track"><span className="fill" style={{ width: `${(d.count / max) * 100}%`, background: `var(--age-${i + 1})` }} /></span>
              <span className="val">{d.count}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/** Created vs closed per week: two lines, legend, end labels, crosshair tooltip. */
export function TrendChart({ data }: { data: { week_start: string; created: number; closed: number }[] }) {
  const [ref, w] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);
  const [table, setTable] = useState(false);
  const h = 190;
  const pad = { l: 28, r: 64, t: 12, b: 26 };
  const iw = w - pad.l - pad.r;
  const ih = h - pad.t - pad.b;
  const max = niceMax(Math.max(1, ...data.flatMap((d) => [d.created, d.closed])));
  const x = (i: number) => pad.l + (data.length <= 1 ? iw / 2 : (i * iw) / (data.length - 1));
  const y = (v: number) => pad.t + ih - (v / max) * ih;
  const ticks = [0, max / 2, max];
  const series = [
    { key: "created" as const, label: "Added", color: "var(--series-1)" },
    { key: "closed" as const, label: "Closed", color: "var(--series-2)" },
  ];
  const path = (k: "created" | "closed") => data.map((d, i) => `${i ? "L" : "M"}${x(i)},${y(d[k])}`).join("");
  const last = data.length - 1;
  const ends = series.map((s) => ({ ...s, v: data[last]?.[s.key] ?? 0 }));
  const tooClose = Math.abs(y(ends[0].v) - y(ends[1].v)) < 14;

  const onMove = (e: React.PointerEvent<SVGRectElement>) => {
    const box = e.currentTarget.getBoundingClientRect();
    const px = e.clientX - box.left;
    const i = Math.round(((px - 0) / box.width) * (data.length - 1));
    setHover(Math.max(0, Math.min(data.length - 1, i)));
  };

  return (
    <div>
      <div className="row" style={{ marginBottom: 8 }}>
        <div className="legend grow">{series.map((s) => <span key={s.key}><i style={{ background: s.color }} />{s.label}</span>)}</div>
        <TableToggle show={table} onToggle={() => setTable(!table)} />
      </div>
      {table ? (
        <table className="data"><thead><tr><th>Week of</th><th className="n">Added</th><th className="n">Closed</th></tr></thead>
          <tbody>{data.map((d) => <tr key={d.week_start}><td>{shortDate(d.week_start)}</td><td className="n">{d.created}</td><td className="n">{d.closed}</td></tr>)}</tbody></table>
      ) : (
        <div className="chart" ref={ref} onPointerLeave={() => setHover(null)}>
          <svg height={h} role="img" aria-label="Tasks added and closed per week, last 8 weeks">
            {ticks.map((t) => (
              <g key={t}>
                <line x1={pad.l} x2={w - pad.r} y1={y(t)} y2={y(t)} stroke={t === 0 ? "var(--axis)" : "var(--grid)"} strokeWidth={1} />
                <text x={pad.l - 6} y={y(t) + 4} textAnchor="end" fontSize="11" fill="var(--ink-3)" className="num">{Math.round(t)}</text>
              </g>
            ))}
            {data.map((d, i) => (i % 2 === (last % 2) || data.length <= 4) && (
              <text key={d.week_start} x={x(i)} y={h - 6} textAnchor="middle" fontSize="11" fill="var(--ink-3)">{shortDate(d.week_start)}</text>
            ))}
            {hover !== null && <line x1={x(hover)} x2={x(hover)} y1={pad.t} y2={pad.t + ih} stroke="var(--axis)" strokeWidth={1} />}
            {series.map((s) => <path key={s.key} d={path(s.key)} fill="none" stroke={s.color} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />)}
            {series.map((s) => {
              const i = hover ?? last;
              const v = data[i]?.[s.key] ?? 0;
              return <circle key={s.key} cx={x(i)} cy={y(v)} r={4.5} fill={s.color} stroke="var(--surface)" strokeWidth={2} />;
            })}
            {ends.map((s, k) => (
              <text key={s.key} x={x(last) + 10} y={y(s.v) + 4 + (tooClose ? (k === 0 ? -8 : 8) : 0)} fontSize="12" fill="var(--ink-2)">
                <tspan fontWeight="700" fill="var(--ink)">{s.v}</tspan> {s.label.toLowerCase()}
              </text>
            ))}
            <rect x={pad.l} y={pad.t} width={iw} height={ih} fill="transparent" onPointerMove={onMove} onPointerDown={onMove} style={{ touchAction: "pan-y" }} />
          </svg>
          {hover !== null && data[hover] && (
            <div className="tip" style={{ left: Math.min(Math.max(0, x(hover) - 70), w - 150), top: 0 }}>
              <div className="tiny muted">Week of {shortDate(data[hover].week_start)}</div>
              {series.map((s) => (
                <div key={s.key} className="row" style={{ gap: 6 }}>
                  <i style={{ width: 12, height: 2, background: s.color, display: "inline-block" }} />
                  <b>{data[hover][s.key]}</b><span className="muted">{s.label.toLowerCase()}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/** Closed per day for the weekly review (single series, so no legend). */
export function DayColumns({ data }: { data: { date: string; closed: number }[] }) {
  const [ref, w] = useWidth<HTMLDivElement>();
  const [hover, setHover] = useState<number | null>(null);
  const h = 150;
  const pad = { l: 24, r: 8, t: 18, b: 24 };
  const iw = w - pad.l - pad.r;
  const ih = h - pad.t - pad.b;
  const max = niceMax(Math.max(1, ...data.map((d) => d.closed)));
  const band = iw / data.length;
  const bw = Math.min(24, band * 0.55);
  const y = (v: number) => pad.t + ih - (v / max) * ih;
  const best = data.reduce((bi, d, i) => (d.closed > data[bi].closed ? i : bi), 0);
  const day = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString("en-IN", { weekday: "short" });
  return (
    <div className="chart" ref={ref}>
      <svg height={h} role="img" aria-label="Tasks closed each day this week">
        {[0, max].map((t) => (
          <g key={t}>
            <line x1={pad.l} x2={w - pad.r} y1={y(t)} y2={y(t)} stroke={t === 0 ? "var(--axis)" : "var(--grid)"} />
            <text x={pad.l - 6} y={y(t) + 4} textAnchor="end" fontSize="11" fill="var(--ink-3)">{t}</text>
          </g>
        ))}
        {data.map((d, i) => {
          const cx = pad.l + band * i + band / 2;
          const top = y(d.closed);
          const hgt = pad.t + ih - top;
          const r = Math.min(4, hgt / 2);
          const shape = d.closed > 0
            ? `M${cx - bw / 2},${pad.t + ih} V${top + r} Q${cx - bw / 2},${top} ${cx - bw / 2 + r},${top} H${cx + bw / 2 - r} Q${cx + bw / 2},${top} ${cx + bw / 2},${top + r} V${pad.t + ih} Z`
            : "";
          return (
            <g key={d.date} onPointerEnter={() => setHover(i)} onPointerLeave={() => setHover(null)} tabIndex={0}
              onFocus={() => setHover(i)} onBlur={() => setHover(null)} aria-label={`${day(d.date)}: ${d.closed} closed`}>
              <rect x={cx - band / 2} y={pad.t} width={band} height={ih} fill="transparent" />
              {shape && <path d={shape} fill="var(--series-1)" opacity={hover === null || hover === i ? 1 : 0.55} />}
              {i === best && d.closed > 0 && <text x={cx} y={top - 6} textAnchor="middle" fontSize="12" fontWeight="700" fill="var(--ink)">{d.closed}</text>}
              <text x={cx} y={h - 6} textAnchor="middle" fontSize="11" fill="var(--ink-3)">{day(d.date)}</text>
            </g>
          );
        })}
      </svg>
      {hover !== null && (
        <div className="tip" style={{ left: Math.min(pad.l + band * hover, w - 120), top: 0 }}>
          <b>{data[hover].closed}</b> <span className="muted">closed · {day(data[hover].date)}</span>
        </div>
      )}
    </div>
  );
}
