import { useCallback, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { api, errorText, type Basket, type Settings as S, type SettingsResponse } from "../api";
import { localDateTime, timeAgo } from "../format";
import { BASKET_ICONS, Icon } from "../icons";
import { disablePush, enablePush, pushState, type PushState } from "../push";
import { useApp, type Theme } from "../store";
import { BasketIcon, Card, Sheet, Spinner, Toggle } from "../ui";

const COLORS = ["blue", "orange", "teal", "amber", "pink", "green", "violet", "red", "slate"];
const ZONES = ["Asia/Kolkata", "Asia/Dubai", "Asia/Singapore", "Europe/London", "America/New_York", "Australia/Sydney", "UTC"];

function Row({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="setting">
      <div className="grow"><div>{title}</div>{hint && <div className="small muted">{hint}</div>}</div>
      {children}
    </div>
  );
}

function BasketEditor({ basket, onClose }: { basket: Basket | "new"; onClose: () => void }) {
  const { baskets, reloadBaskets, bump, toast } = useApp();
  const isNew = basket === "new";
  const [name, setName] = useState(isNew ? "" : basket.name);
  const [color, setColor] = useState(isNew ? COLORS[baskets.length % 8] : basket.color);
  const [icon, setIcon] = useState(isNew ? "briefcase" : basket.icon);
  const [moveTo, setMoveTo] = useState<number | "">("");
  const save = async () => {
    try {
      if (isNew) await api.post("/api/baskets", { name, color, icon });
      else await api.patch(`/api/baskets/${basket.id}`, { name, color, icon });
      await reloadBaskets();
      bump();
      onClose();
    } catch (e) {
      toast({ text: errorText(e), kind: "error" });
    }
  };
  const remove = async () => {
    if (isNew) return;
    if (!window.confirm(`Delete “${basket.name}”? Its tasks move to ${moveTo ? baskets.find((b) => b.id === moveTo)?.name : "No basket"}.`)) return;
    try {
      await api.del(`/api/baskets/${basket.id}${moveTo ? `?move_to=${moveTo}` : ""}`);
      await reloadBaskets();
      bump();
      onClose();
    } catch (e) {
      toast({ text: errorText(e), kind: "error" });
    }
  };
  return (
    <Sheet title={isNew ? "New basket" : "Edit basket"} onClose={onClose}>
      <div className="stack">
        <div className="row"><BasketIcon basket={{ id: 0, name, color, icon, position: 0, archived: false }} size={44} />
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Name, e.g. Plant 2 or Family" maxLength={60} autoFocus /></div>
        <div className="mini">Colour
          <div className="row wrap">{COLORS.map((c) => (
            <button key={c} onClick={() => setColor(c)} aria-label={c} aria-pressed={color === c}
              style={{ width: 36, height: 36, borderRadius: 10, background: `var(--c-${c})`, border: color === c ? "3px solid var(--ink)" : "3px solid transparent", cursor: "pointer" }} />
          ))}</div>
        </div>
        <div className="mini">Icon
          <div className="row wrap">{BASKET_ICONS.map((i) => (
            <button key={i} className="icon-btn" onClick={() => setIcon(i)} aria-label={i} aria-pressed={icon === i}
              style={{ border: icon === i ? "2px solid var(--accent)" : "2px solid var(--line)" }}><Icon name={i} /></button>
          ))}</div>
        </div>
        <button className="btn primary block" onClick={save} disabled={!name.trim()}>Save</button>
        {!isNew && (
          <div className="stack" style={{ borderTop: "1px solid var(--line)", paddingTop: 12 }}>
            <label className="mini">When deleting, move its tasks to
              <select className="input" value={moveTo} onChange={(e) => setMoveTo(e.target.value ? Number(e.target.value) : "")}>
                <option value="">No basket</option>
                {baskets.filter((b) => b.id !== basket.id).map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
              </select>
            </label>
            <button className="btn danger" onClick={remove}><Icon name="trash" />Delete basket</button>
          </div>
        )}
      </div>
    </Sheet>
  );
}

export function Settings() {
  const { baskets, reloadBaskets, toast, theme, setTheme } = useApp();
  const loc = useLocation();
  const [data, setData] = useState<SettingsResponse | null>(null);
  const [push, setPush] = useState<PushState>("off");
  const [editing, setEditing] = useState<Basket | "new" | null>(null);
  const [pinOpen, setPinOpen] = useState(false);
  const [pins, setPins] = useState({ current: "", next: "" });

  const load = useCallback(() => {
    api.get<SettingsResponse>("/api/settings").then(setData).catch((e) => toast({ text: errorText(e), kind: "error" }));
  }, [toast]);
  useEffect(() => { load(); pushState().then(setPush); }, [load]);
  useEffect(() => {
    if (data && loc.hash) document.getElementById(loc.hash.slice(1))?.scrollIntoView({ behavior: "smooth" });
  }, [data, loc.hash]);

  if (!data) return <Spinner />;
  const s = data.settings;
  const st = data.status;

  const save = async (patch: Partial<S>) => {
    setData({ ...data, settings: { ...s, ...patch } });
    try {
      await api.patch("/api/settings", patch);
    } catch (e) {
      toast({ text: errorText(e), kind: "error" });
      load();
    }
  };
  const timeInput = (key: keyof S) => (
    <input className="input" type="time" style={{ width: 130 }} value={String(s[key])} onChange={(e) => e.target.value && save({ [key]: e.target.value })} aria-label={key} />
  );
  const flag = (key: keyof S, label: string) => <Toggle checked={Boolean(s[key])} onChange={(v) => save({ [key]: v })} label={label} />;

  const turnOnPush = async () => {
    try {
      const r = await enablePush();
      setPush(r);
      if (r === "on") { toast({ text: "Notifications are on for this device" }); load(); }
      else if (r === "denied") toast({ text: "Notifications are blocked. Allow them in your browser or phone settings.", kind: "error" });
    } catch (e) {
      toast({ text: errorText(e), kind: "error" });
    }
  };
  const run = async (fn: () => Promise<unknown>, ok: string) => {
    try { await fn(); toast({ text: ok }); load(); } catch (e) { toast({ text: errorText(e), kind: "error" }); }
  };
  const move = async (i: number, dir: -1 | 1) => {
    const ids = baskets.map((b) => b.id);
    const j = i + dir;
    if (j < 0 || j >= ids.length) return;
    [ids[i], ids[j]] = [ids[j], ids[i]];
    await api.post("/api/baskets/reorder", { ids });
    reloadBaskets();
  };

  return (
    <div className="page-narrow stack">
      <h1>Settings</h1>

      <div className="section-title">You</div>
      <Card>
        <Row title="Your name" hint="Used in greetings and to sign follow-up messages">
          <input className="input" style={{ width: 180 }} defaultValue={s.display_name} onBlur={(e) => e.target.value !== s.display_name && save({ display_name: e.target.value })} placeholder="Optional" />
        </Row>
        <Row title="Appearance">
          <div className="seg">{(["system", "light", "dark"] as Theme[]).map((t) => (
            <button key={t} className={theme === t ? "on" : ""} onClick={() => setTheme(t)}>{t === "system" ? "Auto" : t[0].toUpperCase() + t.slice(1)}</button>
          ))}</div>
        </Row>
      </Card>

      <div className="section-title" id="notifications">Notifications on this device</div>
      <Card>
        <div className="setting">
          <span className="bicon" style={{ background: push === "on" ? "var(--good)" : "var(--c-slate)" }}><Icon name="bell" size={18} /></span>
          <div className="grow">
            <div>{push === "on" ? "On for this device" : push === "denied" ? "Blocked by the browser" : push === "needs-install" ? "Add Nudge to your Home Screen first" : push === "unsupported" ? "Not supported in this browser" : "Off"}</div>
            <div className="small muted">
              {push === "needs-install" ? "On iPhone: tap Share → Add to Home Screen, open Nudge from there, then turn this on."
                : `${st.push_devices} device${st.push_devices === 1 ? "" : "s"} getting reminders`}
            </div>
          </div>
          {push === "on" ? (
            <div className="row">
              <button className="btn small" onClick={() => run(() => api.post("/api/push/test"), "Test sent")}>Test</button>
              <button className="btn small ghost" onClick={async () => setPush(await disablePush())}>Turn off</button>
            </div>
          ) : push === "off" ? <button className="btn primary small" onClick={turnOnPush}>Turn on</button> : null}
        </div>
        <Row title="Reminders at the due time" hint="With Done / Snooze / Tomorrow buttons">{flag("push_reminders", "Reminders")}</Row>
        <Row title="Follow-up nudges" hint="When someone hasn't got back to you">{flag("push_nudges", "Nudges")}</Row>
        <Row title="Morning briefing">{flag("push_briefing", "Morning briefing")}</Row>
        <Row title="Overdue check" hint="Once a day, only if something is overdue">{flag("push_overdue", "Overdue check")}</Row>
        <Row title="Evening wrap-up">{flag("push_wrapup", "Evening wrap-up")}</Row>
      </Card>

      <div className="section-title">Times</div>
      <Card>
        <Row title="Morning briefing">{timeInput("briefing_time")}</Row>
        <Row title="Overdue check">{timeInput("overdue_nag_time")}</Row>
        <Row title="Evening wrap-up">{timeInput("wrapup_time")}</Row>
        <Row title="Follow-up nudges arrive at">{timeInput("nudge_time")}</Row>
        <Row title="Quiet hours" hint="Reminders wait until quiet hours end">
          <div className="row">{timeInput("quiet_start")}<span className="muted">to</span>{timeInput("quiet_end")}</div>
        </Row>
        <Row title="Time zone">
          <select className="input" style={{ width: 180 }} value={s.timezone} onChange={(e) => save({ timezone: e.target.value })}>
            {[...new Set([s.timezone, ...ZONES])].map((z) => <option key={z}>{z}</option>)}
          </select>
        </Row>
      </Card>

      <div className="section-title">Follow-ups</div>
      <Card>
        <Row title="Nudge me again every" hint="Default for new “waiting on” tasks">
          <select className="input" style={{ width: 120 }} value={s.default_nudge_days} onChange={(e) => save({ default_nudge_days: Number(e.target.value) })}>
            {[1, 2, 3, 5, 7].map((n) => <option key={n} value={n}>{n} day{n > 1 ? "s" : ""}</option>)}
          </select>
        </Row>
        <Row title="Ask about quiet tasks after" hint="Untouched tasks with no future date">
          <select className="input" style={{ width: 120 }} value={s.stale_days} onChange={(e) => save({ stale_days: Number(e.target.value) })}>
            {[7, 10, 14, 21, 30].map((n) => <option key={n} value={n}>{n} days</option>)}
          </select>
        </Row>
      </Card>

      <div className="section-title">E-mail digest</div>
      <Card>
        <Row title="Send to">
          <input className="input" type="email" style={{ width: 230 }} defaultValue={s.digest_email} placeholder="you@example.com"
            onBlur={(e) => e.target.value !== s.digest_email && save({ digest_email: e.target.value.trim() })} />
        </Row>
        <Row title="Morning briefing e-mail">{flag("email_briefing", "Morning e-mail")}</Row>
        <Row title="Evening wrap-up e-mail">{flag("email_wrapup", "Evening e-mail")}</Row>
        <div className="setting">
          <div className="grow small muted">{st.email_configured ? "E-mail server connected." : "The e-mail server isn't set up yet, so digests are saved for preview. See RUNBOOK.md to connect Gmail or your company mail."}</div>
          <a className="btn small" href="/api/digest/preview" target="_blank" rel="noreferrer">Preview</a>
          <button className="btn small" onClick={() => run(() => api.post("/api/digest/send-now"), st.email_configured ? "Sent" : "Saved to the outbox")} disabled={!s.digest_email}>Send now</button>
        </div>
      </Card>

      <div className="section-title" id="baskets">Baskets</div>
      <Card>
        {baskets.map((b, i) => (
          <div className="setting" key={b.id}>
            <BasketIcon basket={b} size={32} />
            <div className="grow"><div>{b.name}</div><div className="small muted">{b.open ?? 0} open</div></div>
            <button className="icon-btn" onClick={() => move(i, -1)} disabled={i === 0} aria-label={`Move ${b.name} up`}><Icon name="chevron" style={{ transform: "rotate(-90deg)" }} /></button>
            <button className="icon-btn" onClick={() => move(i, 1)} disabled={i === baskets.length - 1} aria-label={`Move ${b.name} down`}><Icon name="chevron" style={{ transform: "rotate(90deg)" }} /></button>
            <button className="icon-btn" onClick={() => setEditing(b)} aria-label={`Edit ${b.name}`}><Icon name="edit" /></button>
          </div>
        ))}
        <div className="setting"><button className="btn" onClick={() => setEditing("new")}><Icon name="plus" />New basket</button></div>
      </Card>

      <div className="section-title">Voice and privacy</div>
      <Card>
        <Row title="Understanding notes" hint="Built in. Runs on your server, costs nothing, nothing is sent anywhere">
          <span className="badge good">Free</span>
        </Row>
        <Row title="Speech to text" hint={st.voice.provider === "whisper" ? `Whisper ${st.voice.model ?? ""} on your server` : st.voice.provider === "mock" ? "Demo voice (returns a sample sentence)" : "Not set up"}>
          <span className={`badge ${st.voice.ready ? "good" : "warning"}`}>{st.voice.ready ? "Ready" : st.voice.provider === "whisper" ? "Loading" : "Off"}</span>
        </Row>
        <div className="setting small muted" style={{ display: "block" }}>
          <b style={{ color: "var(--ink)" }}>What leaves your server:</b> nothing about your tasks, except
          {" "}push notifications (encrypted end to end, so Google and Apple, who deliver them, can't read them)
          {st.email_configured ? " and the e-mail digest, which goes through your own mail provider" : ""}.
          Recordings are turned into text on your server and deleted straight away. Read-aloud uses only voices built into your device.
        </div>
      </Card>

      <div className="section-title">Your data</div>
      <Card>
        <Row title="Export everything to Excel" hint="Open tasks, follow-ups, closed history and a basket summary">
          <a className="btn small" href="/api/export.xlsx"><Icon name="download" size={16} />Download</a>
        </Row>
        <Row title="Backups" hint={st.backups[0] ? `Last: ${st.backups[0].name.replace("nudge-", "").replace(".sqlite", "")} · nightly at 2 AM, last 14 kept` : "Nightly at 2 AM, last 14 kept"}>
          <button className="btn small" onClick={() => run(() => api.post("/api/backups"), "Backed up")}>Back up now</button>
        </Row>
        {st.backups.slice(0, 3).map((b) => (
          <div className="setting" key={b.name}><div className="grow small">{b.name}</div><a className="btn small ghost" href={`/api/backups/${b.name}`}><Icon name="download" size={16} /></a></div>
        ))}
      </Card>

      <div className="section-title">Recent notifications</div>
      <Card>
        {data.recent_notifications.length === 0 && <div className="setting small muted">Nothing sent yet.</div>}
        {data.recent_notifications.map((n, i) => (
          <div className="setting" key={i}>
            <Icon name={n.channel === "email" ? "mail" : "bell"} />
            <div className="grow"><div className="small" style={{ fontWeight: 560 }}>{n.title}</div>
              <div className="tiny muted">{localDateTime(n.at)} · {timeAgo(n.at)}{n.error ? ` · ${n.error}` : n.delivered ? ` · delivered to ${n.delivered}` : ""}</div></div>
          </div>
        ))}
      </Card>

      <div className="section-title">Security</div>
      <Card>
        <Row title="PIN"><button className="btn small" onClick={() => setPinOpen(true)}>Change PIN</button></Row>
        <Row title="Log out of this device">
          <button className="btn small" onClick={async () => { await api.post("/api/auth/logout"); location.href = "/"; }}><Icon name="logout" size={16} />Log out</button>
        </Row>
      </Card>
      <div className="tiny muted" style={{ textAlign: "center" }}>Nudge {st.version}{st.demo ? " · demo mode" : ""}</div>

      {editing && <BasketEditor basket={editing} onClose={() => setEditing(null)} />}
      {pinOpen && (
        <Sheet title="Change PIN" onClose={() => setPinOpen(false)}>
          <form className="stack" onSubmit={async (e) => {
            e.preventDefault();
            try { await api.post("/api/auth/change-pin", { current_pin: pins.current, new_pin: pins.next }); toast({ text: "PIN changed" }); setPinOpen(false); }
            catch (err) { toast({ text: errorText(err), kind: "error" }); }
          }}>
            <label className="field">Current PIN<input className="input" type="password" inputMode="numeric" autoComplete="current-password" value={pins.current} onChange={(e) => setPins({ ...pins, current: e.target.value })} /></label>
            <label className="field">New PIN (4–8 digits)<input className="input" type="password" inputMode="numeric" autoComplete="new-password" value={pins.next} onChange={(e) => setPins({ ...pins, next: e.target.value.replace(/\D/g, "").slice(0, 8) })} /></label>
            <button className="btn primary" disabled={pins.next.length < 4}>Change PIN</button>
          </form>
        </Sheet>
      )}
    </div>
  );
}
