import { useState } from "react";

/** Horizontal bars as HTML rows: label, track and a direct value label. */
export function BarRows({ rows, format, color = "var(--series-1)" }: { rows: { label: string; value: number; hint?: string }[]; format: (v: number) => string; color?: string }) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  if (rows.length === 0) return <p className="muted">No data for this period.</p>;
  return (
    <div className="bar-rows">
      {rows.map((r) => (
        <div className="bar-row" key={r.label} title={r.hint ?? `${r.label}: ${format(r.value)}`}>
          <span className="lbl">{r.label}</span>
          <div className="track">
            <div className="fill" style={{ width: `${(r.value / max) * 100}%`, background: color }} />
          </div>
          <span className="mono">{format(r.value)}</span>
        </div>
      ))}
    </div>
  );
}

export interface Series {
  name: string;
  color: string;
  values: number[];
}

/** Grouped vertical bars with a legend, hairline grid and a hover tooltip. */
export function GroupedBars({ categories, series, height = 200, format = (v: number) => String(v), suffix = "" }: { categories: string[]; series: Series[]; height?: number; format?: (v: number) => string; suffix?: string }) {
  const [hover, setHover] = useState<{ i: number; x: number; y: number } | null>(null);
  const width = 640;
  const pad = { l: 36, r: 8, t: 10, b: 26 };
  const innerW = width - pad.l - pad.r;
  const innerH = height - pad.t - pad.b;
  const max = Math.max(1, ...series.flatMap((s) => s.values));
  const niceMax = niceCeil(max);
  const groupW = innerW / Math.max(1, categories.length);
  const gap = 2;
  const barW = Math.max(4, Math.min(28, (groupW - 12) / series.length - gap));
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((f) => f * niceMax);
  const y = (v: number) => pad.t + innerH - (v / niceMax) * innerH;

  return (
    <div className="chart">
      {series.length > 1 && (
        <div className="legend">
          {series.map((s) => (
            <span key={s.name}>
              <i style={{ background: s.color }} />
              {s.name}
            </span>
          ))}
        </div>
      )}
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={series.map((s) => s.name).join(" and ")} onMouseLeave={() => setHover(null)}>
        {ticks.map((t) => (
          <g key={t}>
            <line x1={pad.l} x2={width - pad.r} y1={y(t)} y2={y(t)} stroke="var(--grid)" strokeWidth={1} />
            <text x={pad.l - 6} y={y(t) + 4} fontSize={11} textAnchor="end" fill="var(--muted)">
              {format(t)}
            </text>
          </g>
        ))}
        <line x1={pad.l} x2={width - pad.r} y1={y(0)} y2={y(0)} stroke="var(--axis)" strokeWidth={1} />
        {categories.map((c, i) => {
          const gx = pad.l + i * groupW;
          const totalW = series.length * barW + (series.length - 1) * gap;
          const start = gx + (groupW - totalW) / 2;
          return (
            <g key={c} onMouseEnter={() => setHover({ i, x: gx + groupW / 2, y: Math.min(...series.map((s) => y(s.values[i] ?? 0))) })}>
              <rect x={gx} y={pad.t} width={groupW} height={innerH} fill="transparent" />
              {series.map((s, si) => {
                const v = s.values[i] ?? 0;
                const bx = start + si * (barW + gap);
                const top = y(v);
                const h = Math.max(0, y(0) - top);
                const r = Math.min(4, barW / 2, h);
                const d = `M${bx},${y(0)} v${-(h - r)} a${r},${r} 0 0 1 ${r},${-r} h${barW - 2 * r} a${r},${r} 0 0 1 ${r},${r} v${h - r} z`;
                return <path key={s.name} d={h > 0 ? d : ""} fill={s.color} opacity={hover && hover.i !== i ? 0.55 : 1} />;
              })}
              <text x={gx + groupW / 2} y={height - 8} fontSize={11} textAnchor="middle" fill="var(--muted)">
                {c}
              </text>
            </g>
          );
        })}
      </svg>
      {hover && (
        <div className="tip" style={{ left: `${(hover.x / width) * 100}%`, top: `${(hover.y / height) * 100}%` }}>
          <div style={{ fontWeight: 600 }}>{categories[hover.i]}</div>
          {series.map((s) => (
            <div key={s.name}>
              {s.name}: {format(s.values[hover.i] ?? 0)}
              {suffix}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function niceCeil(v: number): number {
  if (v <= 5) return 5;
  const p = 10 ** Math.floor(Math.log10(v));
  const n = v / p;
  const m = n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10;
  return m * p;
}
