import { useEffect, useState, type ButtonHTMLAttributes, type ReactNode } from "react";
import type { Priority, WOStatus } from "../types";
import { PLAN_STATE_LABEL, type PlanState } from "../lib/pm";
import { PRIORITY_LABEL, WO_STATUS_LABEL } from "../lib/workorders";
import { Icon, type IconName } from "./icons";

type Tone = "neutral" | "accent" | "good" | "warning" | "serious" | "critical";

export function Button({
  variant = "default",
  size,
  icon,
  children,
  className = "",
  type = "button",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "default" | "primary" | "danger" | "ghost"; size?: "sm"; icon?: IconName }) {
  const cls = ["btn", variant !== "default" ? variant : "", size ?? "", !children ? "icon" : "", className].filter(Boolean).join(" ");
  return (
    <button type={type} className={cls} {...rest}>
      {icon && <Icon name={icon} size={size === "sm" ? 15 : 17} />}
      {children}
    </button>
  );
}

export function PageHeader({ title, subtitle, actions }: { title: ReactNode; subtitle?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle && <div className="sub">{subtitle}</div>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </div>
  );
}

export function Card({ title, actions, children, tight, className = "" }: { title?: ReactNode; actions?: ReactNode; children: ReactNode; tight?: boolean; className?: string }) {
  return (
    <section className={`card ${className}`}>
      {(title || actions) && (
        <div className="card-head">
          <h2>{title}</h2>
          {actions && <div className="flex">{actions}</div>}
        </div>
      )}
      <div className={`card-body ${tight ? "tight" : ""}`}>{children}</div>
    </section>
  );
}

export function Stat({ label, value, hint, tone, onClick }: { label: string; value: ReactNode; hint?: ReactNode; tone?: Tone; onClick?: () => void }) {
  const cls = `stat ${tone ? `tone-${tone}` : ""}`;
  const body = (
    <>
      <span className="label">{label}</span>
      <span className="value">{value}</span>
      {hint && <span className="hint">{hint}</span>}
    </>
  );
  return onClick ? (
    <button type="button" className={cls} onClick={onClick}>
      {body}
    </button>
  ) : (
    <div className={cls}>{body}</div>
  );
}

export function Badge({ tone = "neutral", children, outline, dot }: { tone?: Tone; children: ReactNode; outline?: boolean; dot?: boolean }) {
  return (
    <span className={`badge ${tone} ${outline ? "outline" : ""}`}>
      {dot && <span className="dot" />}
      {children}
    </span>
  );
}

const STATUS_TONE: Record<WOStatus, Tone> = {
  open: "serious",
  assigned: "accent",
  in_progress: "accent",
  on_hold: "warning",
  completed: "good",
  closed: "neutral",
  cancelled: "neutral",
};

export function StatusBadge({ status }: { status: WOStatus }) {
  return (
    <Badge tone={STATUS_TONE[status]} dot>
      {WO_STATUS_LABEL[status]}
    </Badge>
  );
}

const PRIORITY_TONE: Record<Priority, Tone> = { critical: "critical", high: "serious", medium: "warning", low: "neutral" };

export function PriorityBadge({ priority }: { priority: Priority }) {
  return <Badge tone={PRIORITY_TONE[priority]}>{PRIORITY_LABEL[priority]}</Badge>;
}

const PLAN_TONE: Record<PlanState, Tone> = { overdue: "critical", due: "serious", upcoming: "warning", ok: "good", inactive: "neutral" };

export function PlanStateBadge({ state }: { state: PlanState }) {
  return (
    <Badge tone={PLAN_TONE[state]} dot>
      {PLAN_STATE_LABEL[state]}
    </Badge>
  );
}

export function Field({ label, hint, error, required, children, className = "" }: { label: ReactNode; hint?: ReactNode; error?: string | null; required?: boolean; children: ReactNode; className?: string }) {
  return (
    <label className={`field ${className}`}>
      <span className="label">
        {label} {required && <span className="req">*</span>}
      </span>
      {children}
      {hint && !error && <span className="hint">{hint}</span>}
      {error && <span className="error">{error}</span>}
    </label>
  );
}

export function Modal({ title, open, onClose, children, footer, size }: { title: ReactNode; open: boolean; onClose: () => void; children: ReactNode; footer?: ReactNode; size?: "wide" | "narrow" }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal ${size ?? ""}`} role="dialog" aria-modal="true">
        <div className="modal-head">
          <h2>{title}</h2>
          <Button variant="ghost" icon="x" aria-label="Close" onClick={onClose} />
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-foot">{footer}</div>}
      </div>
    </div>
  );
}

export function Confirm({
  open,
  title,
  text,
  confirmLabel = "Confirm",
  danger,
  onConfirm,
  onClose,
}: {
  open: boolean;
  title: string;
  text: ReactNode;
  confirmLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}) {
  return (
    <Modal
      title={title}
      open={open}
      onClose={onClose}
      size="narrow"
      footer={
        <>
          <Button onClick={onClose}>Cancel</Button>
          <Button
            variant={danger ? "danger" : "primary"}
            onClick={() => {
              onConfirm();
              onClose();
            }}
          >
            {confirmLabel}
          </Button>
        </>
      }
    >
      <p>{text}</p>
    </Modal>
  );
}

export function Tabs<T extends string>({ tabs, active, onChange }: { tabs: { id: T; label: string; count?: number }[]; active: T; onChange: (id: T) => void }) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((t) => (
        <button key={t.id} type="button" role="tab" aria-selected={t.id === active} className={t.id === active ? "active" : ""} onClick={() => onChange(t.id)}>
          {t.label}
          {t.count !== undefined && <span className="count">{t.count}</span>}
        </button>
      ))}
    </div>
  );
}

export function Empty({ icon = "info", title, text, action }: { icon?: IconName; title: string; text?: ReactNode; action?: ReactNode }) {
  return (
    <div className="empty">
      <Icon name={icon} size={28} />
      <h3>{title}</h3>
      {text && <p>{text}</p>}
      {action && <div className="mt-8">{action}</div>}
    </div>
  );
}

export function Search({ value, onChange, placeholder = "Search" }: { value: string; onChange: (v: string) => void; placeholder?: string }) {
  return (
    <div className="search">
      <Icon name="search" size={16} />
      <input type="search" value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} aria-label={placeholder} />
    </div>
  );
}

export function Notice({ tone = "neutral", icon = "info", children }: { tone?: Tone; icon?: IconName; children: ReactNode }) {
  return (
    <div className={`notice ${tone === "neutral" ? "" : tone}`}>
      <Icon name={icon} size={18} />
      <div className="grow">{children}</div>
    </div>
  );
}

export function KV({ items }: { items: { k: ReactNode; v: ReactNode }[] }) {
  return (
    <dl className="kv">
      {items.map((it, i) => (
        <div key={i} style={{ display: "contents" }}>
          <dt>{it.k}</dt>
          <dd>{it.v}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Show the first N rows with a "Show more" footer. */
export function usePaged<T>(rows: T[], page = 50): { visible: T[]; more: boolean; showMore: () => void; total: number } {
  const [limit, setLimit] = useState(page);
  useEffect(() => setLimit(page), [rows.length, page]);
  return { visible: rows.slice(0, limit), more: rows.length > limit, showMore: () => setLimit((l) => l + page), total: rows.length };
}

export function ChipSelect<T extends string>({ options, value, onChange }: { options: { value: T; label: string }[]; value: T[]; onChange: (v: T[]) => void }) {
  return (
    <div className="chips">
      {options.map((o) => {
        const on = value.includes(o.value);
        return (
          <button key={o.value} type="button" className={`chip ${on ? "on" : ""}`} aria-pressed={on} onClick={() => onChange(on ? value.filter((v) => v !== o.value) : [...value, o.value])}>
            {on && <Icon name="check" size={13} />}
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

export function money(value: number, currency: string): string {
  try {
    return new Intl.NumberFormat(currency === "INR" ? "en-IN" : "en", { style: "currency", currency, maximumFractionDigits: 0 }).format(value);
  } catch {
    return `${currency} ${Math.round(value)}`;
  }
}
