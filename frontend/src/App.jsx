import { Navigate, Route, Routes } from "react-router-dom";
import AppLayout from "./layouts/AppLayout.jsx";
import AuthLayout from "./layouts/AuthLayout.jsx";
import ProtectedRoute from "./routes/ProtectedRoute.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import RegisterPage from "./pages/RegisterPage.jsx";
import PendingPage from "./pages/PendingPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import ProfilePage from "./pages/ProfilePage.jsx";
import AdminUsersPage from "./pages/admin/AdminUsersPage.jsx";
import AdminPendingPage from "./pages/admin/AdminPendingPage.jsx";
import AdminAuditPage from "./pages/admin/AdminAuditPage.jsx";
import SystemSettings from "./pages/admin/SystemSettings.jsx";
import AdminKnowledgePage from "./pages/admin/AdminKnowledgePage.jsx";
import SearchPage from "./pages/SearchPage.jsx";
import ChatPage from "./pages/ChatPage.jsx";

export default function App() {
  return (
    <Routes>
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/pending" element={<PendingPage />} />
      </Route>
      <Route
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route
          path="/admin/users"
          element={
            <ProtectedRoute roles={["ADMIN"]}>
              <AdminUsersPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/pending"
          element={
            <ProtectedRoute roles={["ADMIN"]}>
              <AdminPendingPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/knowledge"
          element={
            <ProtectedRoute roles={["ADMIN", "SUPER"]}>
              <AdminKnowledgePage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/audit"
          element={
            <ProtectedRoute roles={["ADMIN"]}>
              <AdminAuditPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/settings"
          element={
            <ProtectedRoute roles={["ADMIN"]}>
              <SystemSettings />
            </ProtectedRoute>
          }
        />
      </Route>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
