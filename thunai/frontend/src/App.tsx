import { lazy, Suspense } from "react";
import type { ReactElement } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import type { Role } from "./api";
import { Spinner, Toast } from "./components";
import Ask from "./pages/Ask";
import Home from "./pages/Home";
import LogPage from "./pages/LogPage";
import Login from "./pages/Login";
import Logs from "./pages/Logs";
import MachinePage from "./pages/MachinePage";
import Machines from "./pages/Machines";
import Review from "./pages/Review";
import { useApp } from "./state";

// Loaded on demand to keep the first download small on slow networks.
const Admin = lazy(() => import("./pages/Admin"));
const CardPage = lazy(() => import("./pages/CardPage"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const Skills = lazy(() => import("./pages/Skills"));
const QrSheet = lazy(() => import("./pages/QrSheet"));
const Scan = lazy(() => import("./pages/Scan"));

function Guard({ children, roles }: { children: ReactElement; roles?: Role[] }) {
  const { user } = useApp();
  const location = useLocation();
  // A scanned QR code opens /m/<no>; after login the user lands back on that machine.
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  const { lang } = useApp();
  return (
    <div className={`app lang-${lang}`} lang={lang}>
      <Suspense fallback={<Spinner />}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Guard><Home /></Guard>} />
        <Route path="/machines" element={<Guard><Machines /></Guard>} />
        <Route path="/scan" element={<Guard><Scan /></Guard>} />
        <Route path="/m/:no" element={<Guard><MachinePage /></Guard>} />
        <Route path="/ask/:no" element={<Guard><Ask /></Guard>} />
        <Route path="/log/new/:no" element={<Guard><LogPage /></Guard>} />
        <Route path="/log/:id" element={<Guard><LogPage /></Guard>} />
        <Route path="/logs" element={<Guard><Logs /></Guard>} />
        <Route path="/review" element={<Guard roles={["supervisor", "admin"]}><Review /></Guard>} />
        <Route path="/dashboard" element={<Guard roles={["supervisor", "admin"]}><Dashboard /></Guard>} />
        <Route path="/cards/:id" element={<Guard roles={["supervisor", "admin"]}><CardPage /></Guard>} />
        <Route path="/skills" element={<Guard roles={["supervisor", "admin"]}><Skills /></Guard>} />
        <Route path="/admin" element={<Guard roles={["admin"]}><Admin /></Guard>} />
        <Route path="/admin/qr" element={<Guard roles={["admin"]}><QrSheet /></Guard>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </Suspense>
      <Toast />
    </div>
  );
}
