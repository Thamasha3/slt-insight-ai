import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  LogOut,
  MessageSquarePlus,
  Search,
  Shield,
  UserRound,
  X,
} from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";
import { useChat } from "../context/ChatContext.jsx";

function isSameDay(value, day) {
  if (!value) return false;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return false;
  return date.toDateString() === day.toDateString();
}

function groupSessions(sessions) {
  const today = [];
  const previous = [];
  const now = new Date();
  for (const row of sessions) {
    const stamp = row.updated_at || row.created_at;
    if (isSameDay(stamp, now)) today.push(row);
    else previous.push(row);
  }
  return { today, previous };
}

function initials(name) {
  return (name || "U")
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("");
}

const navClass = ({ isActive }) =>
  `flex items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium transition ${
    isActive ? "bg-teal-50 text-[#064e3b]" : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
  }`;

export default function Sidebar({ open, onClose }) {
  const { user, logout } = useAuth();
  const { sessions, sessionId, setSessionId, startNewChat } = useChat();
  const navigate = useNavigate();
  const isAdmin = user?.role === "ADMIN";
  const canManageKnowledge = isAdmin || user?.role === "SUPER";
  const { today, previous } = groupSessions(sessions);

  function goNewChat() {
    startNewChat();
    onClose?.();
  }

  function openConversation(id) {
    setSessionId(id);
    navigate("/chat");
    onClose?.();
  }

  return (
    <>
      {open && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-slate-900/40 md:hidden"
          aria-label="Close sidebar"
          onClick={onClose}
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex h-dvh w-72 shrink-0 flex-col border-r border-slate-200 bg-white transition-transform md:static md:z-0 md:h-auto md:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between px-4 pb-2 pt-5">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#064e3b] text-sm font-bold text-white">
              SLT
            </div>
            <div>
              <p className="text-sm font-semibold tracking-tight text-slate-900">SLT insight.ai</p>
              <p className="text-[11px] text-slate-500">Internal assistant</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 md:hidden"
            aria-label="Close sidebar"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="px-3 pb-3 pt-2">
          <button
            type="button"
            onClick={goNewChat}
            className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#064e3b] px-3 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-800"
          >
            <MessageSquarePlus className="h-4 w-4" />
            + New Chat
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-3">
          <ConversationGroup
            label="Today"
            rows={today}
            sessionId={sessionId}
            onOpen={openConversation}
          />
          <ConversationGroup
            label="Previous"
            rows={previous}
            sessionId={sessionId}
            onOpen={openConversation}
          />
          {sessions.length === 0 && (
            <p className="px-2 py-6 text-center text-xs text-slate-400">No conversations yet.</p>
          )}
        </div>

        <nav className="space-y-0.5 border-t border-slate-100 px-3 py-3">
          <NavLink to="/dashboard" className={navClass} onClick={onClose}>
            <LayoutDashboard className="h-4 w-4" />
            Dashboard
          </NavLink>
          <NavLink to="/search" className={navClass} onClick={onClose}>
            <Search className="h-4 w-4" />
            Search
          </NavLink>
          <NavLink to="/profile" className={navClass} onClick={onClose}>
            <UserRound className="h-4 w-4" />
            Profile
          </NavLink>
          {canManageKnowledge && (
            <NavLink to="/admin/knowledge" className={navClass} onClick={onClose}>
              <Shield className="h-4 w-4" />
              Knowledge
            </NavLink>
          )}
          {isAdmin && (
            <>
              <NavLink to="/admin/users" className={navClass} onClick={onClose}>
                <Shield className="h-4 w-4" />
                Users
              </NavLink>
              <NavLink to="/admin/pending" className={navClass} onClick={onClose}>
                <Shield className="h-4 w-4" />
                Pending requests
              </NavLink>
              <NavLink to="/admin/audit" className={navClass} onClick={onClose}>
                <Shield className="h-4 w-4" />
                Audit logs
              </NavLink>
            </>
          )}
        </nav>

        <div className="border-t border-slate-100 p-3">
          <div className="flex items-center gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-teal-100 text-xs font-semibold text-[#064e3b]">
              {initials(user?.name)}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-slate-900">{user?.name}</p>
              <p className="text-[11px] font-medium uppercase tracking-wide text-teal-800">
                {user?.role || "REGIONAL"}
              </p>
              <p className="text-[11px] text-slate-500">{user?.region || "WESTERN"}</p>
            </div>
            <button
              type="button"
              onClick={logout}
              className="rounded-lg p-1.5 text-slate-400 hover:bg-white hover:text-slate-700"
              aria-label="Logout"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}

function ConversationGroup({ label, rows, sessionId, onOpen }) {
  if (!rows.length) return null;
  return (
    <div className="mb-4">
      <p className="px-2 pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">{label}</p>
      <ul className="space-y-0.5">
        {rows.map((row) => (
          <li key={row.id}>
            <button
              type="button"
              onClick={() => onOpen(row.id)}
              className={`w-full truncate rounded-xl px-3 py-2 text-left text-sm transition ${
                sessionId === row.id
                  ? "bg-teal-50 font-medium text-[#064e3b]"
                  : "text-slate-600 hover:bg-slate-50"
              }`}
            >
              {row.title}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
