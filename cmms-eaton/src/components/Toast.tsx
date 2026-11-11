import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

interface ToastItem {
  id: number;
  text: string;
  kind: "info" | "success" | "error";
}

interface ToastApi {
  info(text: string): void;
  success(text: string): void;
  error(text: string): void;
}

const ToastContext = createContext<ToastApi | null>(null);
let counter = 0;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const push = useCallback((text: string, kind: ToastItem["kind"]) => {
    const id = ++counter;
    setItems((list) => [...list, { id, text, kind }]);
    window.setTimeout(() => setItems((list) => list.filter((t) => t.id !== id)), kind === "error" ? 6000 : 3500);
  }, []);
  const api = useMemo<ToastApi>(
    () => ({
      info: (t) => push(t, "info"),
      success: (t) => push(t, "success"),
      error: (t) => push(t, "error"),
    }),
    [push],
  );
  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {items.map((t) => (
          <div key={t.id} className={`toast ${t.kind}`}>
            {t.text}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside ToastProvider");
  return ctx;
}
