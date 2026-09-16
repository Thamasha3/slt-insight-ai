import { Outlet } from "react-router-dom";

export default function AuthLayout() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 px-4">
      <div className="w-full max-w-md rounded-xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-center text-2xl font-semibold text-teal-900">SLT insight.ai</h1>
        <p className="mb-6 mt-1 text-center text-sm text-slate-500">Authorized SLT employees only</p>
        <Outlet />
      </div>
    </div>
  );
}
