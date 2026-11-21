import { type FormEvent, useState } from "react";
import { api } from "../api";
import { Card, ErrorNote, Tabs } from "../components";
import { compactInr, money } from "../format";

type Row = { year: number; invested: number; value: number };
type GoalResult = { future_target: number; monthly_sip: number; lumpsum_today_instead: number; suggested_equity_pct: number; table: Row[] };
type RetireResult = { years_to_retirement: number; years_in_retirement: number; monthly_expense_at_retirement: number; corpus_needed: number; monthly_sip: number; table: Row[] };

function GrowthChart({ rows }: { rows: Row[] }) {
  if (!rows.length) return null;
  const max = Math.max(...rows.map((r) => r.value));
  return (
    <div className="growth">
      {rows.map((r) => (
        <div key={r.year} className="growth-col" title={`Year ${r.year}: invested ${compactInr(r.invested)}, value ${compactInr(r.value)}`}>
          <div className="growth-bar" style={{ height: `${(r.value / max) * 100}%` }}>
            <div className="growth-inv" style={{ height: `${(r.invested / r.value) * 100}%` }} />
          </div>
          <span className="small muted">{r.year}</span>
        </div>
      ))}
    </div>
  );
}

function Field({ label, value, onChange, step = "any" }: { label: string; value: string; onChange: (v: string) => void; step?: string }) {
  return <label>{label}<input type="number" step={step} value={value} onChange={(e) => onChange(e.target.value)} required /></label>;
}

export default function Planner() {
  const [tab, setTab] = useState<"goal" | "retire">("goal");
  const [g, setG] = useState({ target_amount_today: "5000000", years: "12", inflation_pct: "6", expected_return_pct: "11", current_savings: "0", step_up_pct: "10" });
  const [r, setR] = useState({ current_age: "35", retire_age: "60", life_expectancy: "85", monthly_expense_today: "60000", inflation_pct: "6", pre_return_pct: "11", post_return_pct: "7.5", current_corpus: "0", step_up_pct: "10" });
  const [goal, setGoal] = useState<GoalResult | null>(null);
  const [ret, setRet] = useState<RetireResult | null>(null);
  const [err, setErr] = useState<unknown>();
  const toNums = (o: Record<string, string>) => Object.fromEntries(Object.entries(o).map(([k, v]) => [k, Number(v)]));
  const runGoal = async (e: FormEvent) => {
    e.preventDefault();
    setErr(undefined);
    try { setGoal(await api.post<GoalResult>("/plan/goal", toNums(g))); } catch (e2) { setErr(e2); }
  };
  const runRet = async (e: FormEvent) => {
    e.preventDefault();
    setErr(undefined);
    try { setRet(await api.post<RetireResult>("/plan/retirement", toNums(r))); } catch (e2) { setErr(e2); }
  };
  return (
    <div className="page">
      <h1>Planner</h1>
      <Tabs tabs={[{ id: "goal", label: "Goal SIP" }, { id: "retire", label: "Retirement" }]} value={tab} onChange={setTab} />
      <ErrorNote error={err} />
      {tab === "goal" && (
        <div className="grid-2">
          <Card title="Your goal">
            <form className="form" onSubmit={runGoal}>
              <Field label="Cost in today's rupees" value={g.target_amount_today} onChange={(v) => setG({ ...g, target_amount_today: v })} />
              <div className="row"><Field label="Years away" value={g.years} onChange={(v) => setG({ ...g, years: v })} /><Field label="Inflation %" value={g.inflation_pct} onChange={(v) => setG({ ...g, inflation_pct: v })} /></div>
              <div className="row"><Field label="Expected return %" value={g.expected_return_pct} onChange={(v) => setG({ ...g, expected_return_pct: v })} /><Field label="Yearly SIP step-up %" value={g.step_up_pct} onChange={(v) => setG({ ...g, step_up_pct: v })} /></div>
              <Field label="Already saved for it (₹)" value={g.current_savings} onChange={(v) => setG({ ...g, current_savings: v })} />
              <button className="btn primary">Calculate</button>
            </form>
          </Card>
          <Card title="Plan">
            {!goal ? <p className="muted">Fill in the goal and press Calculate.</p> : (
              <>
                <div className="kpis">
                  <div className="kpi big"><span className="kpi-label">Monthly SIP to start</span><span className="kpi-value">{money(goal.monthly_sip, "INR", 0)}</span></div>
                  <div className="kpi"><span className="kpi-label">Goal in future rupees</span><span className="kpi-value">{compactInr(goal.future_target)}</span></div>
                  <div className="kpi"><span className="kpi-label">Or lump sum today</span><span className="kpi-value">{compactInr(goal.lumpsum_today_instead)}</span></div>
                  <div className="kpi"><span className="kpi-label">Suggested equity share</span><span className="kpi-value">{goal.suggested_equity_pct}%</span></div>
                </div>
                <GrowthChart rows={goal.table} />
                <p className="muted small">Dark: amount invested. Light: projected value. Projections assume a steady return; real returns vary year to year.</p>
              </>
            )}
          </Card>
        </div>
      )}
      {tab === "retire" && (
        <div className="grid-2">
          <Card title="About you">
            <form className="form" onSubmit={runRet}>
              <div className="row"><Field label="Age now" step="1" value={r.current_age} onChange={(v) => setR({ ...r, current_age: v })} /><Field label="Retire at" step="1" value={r.retire_age} onChange={(v) => setR({ ...r, retire_age: v })} /></div>
              <div className="row"><Field label="Plan until age" step="1" value={r.life_expectancy} onChange={(v) => setR({ ...r, life_expectancy: v })} /><Field label="Monthly expenses today (₹)" value={r.monthly_expense_today} onChange={(v) => setR({ ...r, monthly_expense_today: v })} /></div>
              <div className="row"><Field label="Inflation %" value={r.inflation_pct} onChange={(v) => setR({ ...r, inflation_pct: v })} /><Field label="Return before retiring %" value={r.pre_return_pct} onChange={(v) => setR({ ...r, pre_return_pct: v })} /></div>
              <div className="row"><Field label="Return after retiring %" value={r.post_return_pct} onChange={(v) => setR({ ...r, post_return_pct: v })} /><Field label="Yearly SIP step-up %" value={r.step_up_pct} onChange={(v) => setR({ ...r, step_up_pct: v })} /></div>
              <Field label="Retirement savings so far (₹)" value={r.current_corpus} onChange={(v) => setR({ ...r, current_corpus: v })} />
              <button className="btn primary">Calculate</button>
            </form>
          </Card>
          <Card title="Plan">
            {!ret ? <p className="muted">Fill in your details and press Calculate.</p> : (
              <>
                <div className="kpis">
                  <div className="kpi big"><span className="kpi-label">Corpus needed</span><span className="kpi-value">{compactInr(ret.corpus_needed)}</span></div>
                  <div className="kpi"><span className="kpi-label">Monthly SIP to start</span><span className="kpi-value">{money(ret.monthly_sip, "INR", 0)}</span></div>
                  <div className="kpi"><span className="kpi-label">Monthly expenses at retirement</span><span className="kpi-value">{money(ret.monthly_expense_at_retirement, "INR", 0)}</span></div>
                </div>
                <GrowthChart rows={ret.table} />
                <p className="muted small">{ret.years_to_retirement} years to build it, {ret.years_in_retirement} years of withdrawals growing with inflation.</p>
              </>
            )}
          </Card>
        </div>
      )}
    </div>
  );
}
