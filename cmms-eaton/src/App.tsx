import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import { Layout } from "./components/Layout";
import { ToastProvider } from "./components/Toast";
import { Notice } from "./components/ui";
import { can, type Permission } from "./lib/permissions";
import { useStore } from "./store/StoreProvider";
import { AssetDetail } from "./pages/AssetDetail";
import { Assets } from "./pages/Assets";
import { Dashboard } from "./pages/Dashboard";
import { Login } from "./pages/Login";
import { PartDetail } from "./pages/PartDetail";
import { Parts } from "./pages/Parts";
import { PM } from "./pages/PM";
import { QrSheet } from "./pages/QrSheet";
import { Reports } from "./pages/Reports";
import { Settings } from "./pages/Settings";
import { Users } from "./pages/Users";
import { WorkOrderDetail } from "./pages/WorkOrderDetail";
import { WorkOrders } from "./pages/WorkOrders";

function Loading() {
  return (
    <div className="login">
      <div className="card" style={{ padding: 24, textAlign: "center" }}>
        Loading CMMS_Eaton…
      </div>
    </div>
  );
}

function Guard({ permission, children }: { permission?: Permission; children: ReactNode }) {
  const { ready, user } = useStore();
  const location = useLocation();
  if (!ready) return <Loading />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (permission && !can(user, permission)) {
    return (
      <Layout>
        <Notice tone="warning" icon="lock">
          Your role does not have access to this page.
        </Notice>
      </Layout>
    );
  }
  return <Layout>{children}</Layout>;
}

export default function App() {
  return (
    <ToastProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Guard><Dashboard /></Guard>} />
        <Route path="/work-orders" element={<Guard><WorkOrders /></Guard>} />
        <Route path="/work-orders/:id" element={<Guard><WorkOrderDetail /></Guard>} />
        <Route path="/pm" element={<Guard permission="pm.view"><PM /></Guard>} />
        <Route path="/assets" element={<Guard permission="asset.view"><Assets /></Guard>} />
        <Route path="/assets/qr-sheet" element={<Guard permission="asset.view"><QrSheet /></Guard>} />
        <Route path="/assets/:id" element={<Guard permission="asset.view"><AssetDetail /></Guard>} />
        <Route path="/parts" element={<Guard permission="part.view"><Parts /></Guard>} />
        <Route path="/parts/:id" element={<Guard permission="part.view"><PartDetail /></Guard>} />
        <Route path="/reports" element={<Guard permission="reports.view"><Reports /></Guard>} />
        <Route path="/users" element={<Guard><Users /></Guard>} />
        <Route path="/settings" element={<Guard><Settings /></Guard>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ToastProvider>
  );
}
