// Small shared pieces.
import { useEffect, useRef, type ReactNode } from "react";
import type { Basket } from "./api";
import { Icon } from "./icons";

export function colorVar(color: string | undefined): string {
  return `var(--c-${color || "slate"})`;
}

export function BasketDot({ basket }: { basket: Basket | null | undefined }) {
  return <i className="bdot" style={{ background: colorVar(basket?.color) }} aria-hidden="true" />;
}

export function BasketIcon({ basket, size = 36 }: { basket: Basket | null | undefined; size?: number }) {
  return (
    <span className="bicon" style={{ background: colorVar(basket?.color), width: size, height: size }} aria-hidden="true">
      <Icon name={basket?.icon || "inbox"} size={Math.round(size * 0.52)} />
    </span>
  );
}

export function Sheet({ title, onClose, children, wide }: { title?: ReactNode; onClose: () => void; children: ReactNode; wide?: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    ref.current?.focus();
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
      prev?.focus?.();
    };
  }, [onClose]);
  return (
    <div className="scrim" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="sheet" role="dialog" aria-modal="true" aria-label={typeof title === "string" ? title : undefined}
        tabIndex={-1} ref={ref} style={wide ? { maxWidth: 760 } : undefined}>
        <div className="grab" />
        {title !== undefined && (
          <div className="sheet-head">
            <h2>{title}</h2>
            <button className="icon-btn" onClick={onClose} aria-label="Close"><Icon name="x" /></button>
          </div>
        )}
        {children}
      </div>
    </div>
  );
}

export function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <label className="toggle">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} aria-label={label} />
      <span />
    </label>
  );
}

export function Spinner({ label = "Loading" }: { label?: string }) {
  return <div className="row" style={{ justifyContent: "center", padding: 24 }} role="status"><div className="spin" /><span className="sr-only">{label}</span></div>;
}

export function Empty({ icon, title, children }: { icon: string; title: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <div className="big" aria-hidden="true"><Icon name={icon} size={34} /></div>
      <div style={{ fontWeight: 650, color: "var(--ink)" }}>{title}</div>
      {children && <div className="small" style={{ marginTop: 4 }}>{children}</div>}
    </div>
  );
}

export function Card({ title, action, children, className = "" }: { title?: ReactNode; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`card ${className}`}>
      {title && <div className="card-head"><h2>{title}</h2>{action}</div>}
      {children}
    </section>
  );
}
