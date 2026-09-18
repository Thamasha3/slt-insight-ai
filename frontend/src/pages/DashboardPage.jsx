import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BadgeCheck, CalendarDays, Clock3, MapPin, Network, Shield, Siren } from "lucide-react";
import api from "../services/api.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useChat } from "../context/ChatContext.jsx";

const COPY = {
  ADMIN: {
    title: "Admin dashboard",
    body: "Manage users, approve registrations, and control the single knowledge base (GENERAL, REGIONAL, CONFIDENTIAL_INTERNAL). Admin does not retrieve employee knowledge until SLT defines that policy.",
    access:
      "You administer the knowledge base. Employee Q&A remains with Super, Regional, and Normal accounts.",
  },
  SUPER: {
    title: "Super User dashboard",
    body: "Ask about approved General, Regional, and Confidential/Internal sources. You can also upload and validate knowledge. User administration remains Admin-only.",
    access: "You can ask about approved General, Regional, and Confidential/Internal documents, and you can approve or reject knowledge sources.",
  },
  REGIONAL: {
    title: "Regional dashboard",
    body: "Ask the assistant about approved General information plus regional documents for your assigned region only.",
    access: null,
  },
  NORMAL: {
    title: "Employee dashboard",
    body: "Ask the assistant about approved General information only — not regional or confidential sources.",
    access: "You can ask about approved General documents only.",
  },
};

const QUICK_ACTIONS = [
  { title: "Check 2026 Annual Leave Policy", icon: CalendarDays },
  { title: "Regional Fiber Rollout Progress", icon: Network },
  { title: "Reported Network Escalations", icon: Siren },
  { title: "Customer Service Center Operating Hours", icon: Clock3 },
];

function statusTone(status) {
  if (status === "ACTIVE") return "bg-emerald-50 text-emerald-800 ring-emerald-100";
  if (status === "PENDING") return "bg-amber-50 text-amber-800 ring-amber-100";
  return "bg-slate-100 text-slate-700 ring-slate-200";
}

export default function DashboardPage() {
  const { user } = useAuth();
  const { queuePrompt } = useChat();
  const content = COPY[user.role] || COPY.NORMAL;
  const [stats, setStats] = useState(null);
  const [statsError, setStatsError] = useState("");
  const region = user.region || "WESTERN";

  useEffect(() => {
    if (user.role !== "ADMIN") return;
    api
      .get("/admin/stats")
      .then((response) => setStats(response.data))
      .catch(() => setStatsError("Could not load dashboard stats."));
  }, [user.role]);

  function askChat(prompt) {
    queuePrompt(prompt);
  }

  const accessBody =
    content.access ||
    `You have access to General + ${region} region documents. Other regions and confidential/internal files stay out of scope.`;

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight text-slt-blue">{content.title}</h2>
        <p className="mt-1 max-w-2xl text-sm text-slate-500">{content.body}</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard icon={Shield} label="Assigned Role" value={user.role}>
          <span className="mt-3 inline-flex rounded-full bg-slt-blue/10 px-2.5 py-1 text-xs font-semibold text-slt-blue ring-1 ring-slt-blue/20">
            {user.role}
          </span>
        </StatCard>
        <StatCard icon={MapPin} label="Current Region Scope" value={user.region || "—"}>
          <span className="mt-3 inline-flex rounded-full bg-sky-50 px-2.5 py-1 text-xs font-semibold text-sky-800 ring-1 ring-sky-100">
            {user.region || "Not assigned"}
          </span>
        </StatCard>
        <StatCard icon={BadgeCheck} label="Account Status" value={user.status}>
          <span className={`mt-3 inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${statusTone(user.status)}`}>
            {user.status}
          </span>
        </StatCard>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-base font-semibold text-slt-blue">What you have access to</h3>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-600">{accessBody}</p>
        {user.role === "REGIONAL" && (
          <div className="mt-4 flex flex-wrap gap-2">
            <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">General</span>
            <span className="rounded-full bg-mobitel/10 px-3 py-1 text-xs font-medium text-mobitel-dark">{region}</span>
          </div>
        )}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-base font-semibold text-slt-blue">Quick actions</h3>
        <p className="mt-1 text-sm text-slate-500">Jump into Chat with a suggested question.</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {QUICK_ACTIONS.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.title}
                type="button"
                onClick={() => askChat(item.title)}
                className="flex items-start gap-3 rounded-xl border border-slate-200 bg-page px-4 py-3 text-left text-sm font-medium text-ink transition hover:border-mobitel hover:bg-mobitel/10"
              >
                <Icon className="mt-0.5 h-4 w-4 shrink-0 text-mobitel" />
                {item.title}
              </button>
            );
          })}
        </div>
      </div>

      {user.role === "ADMIN" && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slt-blue">Operations snapshot</h3>
          {statsError && <p className="mt-3 text-sm text-red-700">{statsError}</p>}
          {stats && (
            <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
              <Stat label="Pending registrations" value={stats.users_pending} to="/admin/pending" />
              <Stat label="Active users" value={stats.users_active} to="/admin/users" />
              <Stat label="Pending documents" value={stats.documents_pending} to="/admin/knowledge" />
              <Stat label="Approved documents" value={stats.documents_approved} to="/admin/knowledge" />
              <Stat label="Approved chunks" value={stats.chunks_approved} />
              <Stat label="Failed ingestions" value={stats.documents_failed} to="/admin/knowledge" />
            </dl>
          )}
          {stats && (
            <p className="mt-4 text-sm text-slate-500">
              Knowledge by category — GENERAL {stats.knowledge_by_category.GENERAL || 0}, REGIONAL{" "}
              {stats.knowledge_by_category.REGIONAL || 0}, CONFIDENTIAL_INTERNAL{" "}
              {stats.knowledge_by_category.CONFIDENTIAL_INTERNAL || 0}
            </p>
          )}
          <div className="mt-4 flex flex-wrap gap-3 text-sm">
            <Link className="rounded-md bg-slt-blue px-3 py-2 text-white hover:bg-slt-blue-dark" to="/admin/knowledge">
              Knowledge base
            </Link>
            <Link className="rounded-md border border-slate-300 px-3 py-2" to="/admin/pending">
              Pending requests
            </Link>
            <Link className="rounded-md border border-slate-300 px-3 py-2" to="/admin/users">
              Users
            </Link>
            <Link className="rounded-md border border-slate-300 px-3 py-2" to="/admin/audit">
              Audit logs
            </Link>
            <Link className="rounded-md border border-slate-300 px-3 py-2" to="/admin/settings">
              System settings
            </Link>
          </div>
        </div>
      )}

      {user.role === "SUPER" && (
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slt-blue">Knowledge validation</h3>
          <p className="mt-2 text-sm text-slate-600">
            Review PENDING documents, approve or reject them, and upload PDF, Word, CSV, or Excel sources.
            User accounts and audit export stay with Admin.
          </p>
          <div className="mt-4">
            <Link className="rounded-md bg-slt-blue px-3 py-2 text-sm text-white hover:bg-slt-blue-dark" to="/admin/knowledge">
              Open knowledge
            </Link>
          </div>
        </div>
      )}
    </section>
  );
}

function StatCard({ icon: Icon, label, value, children }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
        <span className="rounded-lg bg-mobitel/10 p-2 text-mobitel">
          <Icon className="h-4 w-4" />
        </span>
      </div>
      <p className="mt-3 text-xl font-semibold text-ink">{value}</p>
      {children}
    </div>
  );
}

function Stat({ label, value, to }) {
  const inner = (
    <>
      <dt className="text-slate-500">{label}</dt>
      <dd className="text-2xl font-semibold text-slt-blue">{value}</dd>
    </>
  );
  if (to) {
    return (
      <Link to={to} className="rounded-md bg-slate-50 p-3 hover:bg-slate-100">
        {inner}
      </Link>
    );
  }
  return <div className="rounded-md bg-slate-50 p-3">{inner}</div>;
}
