import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { registerSW } from "virtual:pwa-register";
import { App } from "./App";
import { AppProvider, applyTheme } from "./store";
import "./styles.css";

try {
  const t = localStorage.getItem("nudge-theme");
  if (t === "light" || t === "dark") applyTheme(t);
} catch {
  /* private mode */
}

if ("serviceWorker" in navigator) registerSW({ immediate: true });

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AppProvider>
        <App />
      </AppProvider>
    </BrowserRouter>
  </StrictMode>,
);
