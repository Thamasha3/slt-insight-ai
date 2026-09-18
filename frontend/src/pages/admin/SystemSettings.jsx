import { useEffect, useState } from "react";
import api from "../../services/api.js";

export default function SystemSettings() {
  const [retentionDays, setRetentionDays] = useState(90);
  const [adminChatEnabled, setAdminChatEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/admin/settings")
      .then((response) => {
        setRetentionDays(response.data.chat_history_retention_days);
        setAdminChatEnabled(Boolean(response.data.admin_chat_enabled));
      })
      .catch(() => setError("Could not load system settings."))
      .finally(() => setLoading(false));
  }, []);

  async function persist(next = {}) {
    const payload = {
      chat_history_retention_days: Number(next.retentionDays ?? retentionDays),
      admin_chat_enabled: next.adminChatEnabled ?? adminChatEnabled,
    };
    const response = await api.put("/admin/settings", payload);
    setRetentionDays(response.data.chat_history_retention_days);
    setAdminChatEnabled(Boolean(response.data.admin_chat_enabled));
    return response.data;
  }

  async function onSave(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setSaving(true);
    try {
      await persist();
      setMessage("Settings saved and applied system-wide.");
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Could not save settings.");
    } finally {
      setSaving(false);
    }
  }

  async function onToggleAdminChat() {
    const nextEnabled = !adminChatEnabled;
    setAdminChatEnabled(nextEnabled);
    setError("");
    setMessage("");
    try {
      await persist({ adminChatEnabled: nextEnabled });
      setMessage("Settings saved and applied system-wide.");
    } catch (err) {
      setAdminChatEnabled(!nextEnabled);
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Could not save settings.");
    }
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-xl font-semibold text-slt-blue">System settings</h2>
      <p className="mt-1 text-sm text-slate-500">
        Admin-only configuration for chat history retention and Admin chatbot access.
      </p>
      {loading && <p className="mt-4 text-sm text-slate-500">Loading…</p>}
      {error && <p className="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      {message && <p className="mt-4 rounded-md bg-mobitel/10 px-3 py-2 text-sm text-mobitel-dark">{message}</p>}
      {!loading && (
        <form onSubmit={onSave} className="mt-6 max-w-lg space-y-6">
          <label className="block text-sm font-medium text-ink">
            Chat History Retention (Days)
            <input
              type="number"
              min={1}
              max={3650}
              required
              value={retentionDays}
              onChange={(e) => setRetentionDays(e.target.value)}
              onBlur={() => persist().catch(() => setError("Could not save settings."))}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-ink"
            />
          </label>
          <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-page px-4 py-3">
            <div>
              <p className="text-sm font-medium text-ink">Enable Admin Chatbot</p>
              <p className="text-xs text-slate-500">When off, Admin accounts cannot submit chat queries.</p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={adminChatEnabled}
              onClick={onToggleAdminChat}
              className={`relative h-7 w-12 rounded-full transition ${
                adminChatEnabled ? "bg-mobitel" : "bg-slate-300"
              }`}
            >
              <span
                className="absolute top-0.5 h-6 w-6 rounded-full bg-white shadow transition"
                style={{ left: adminChatEnabled ? "1.35rem" : "0.125rem" }}
              />
            </button>
          </div>
          <button
            type="submit"
            disabled={saving}
            className="rounded-md bg-mobitel px-4 py-2 text-sm text-white hover:bg-mobitel-dark disabled:opacity-60"
          >
            {saving ? "Saving…" : "Save settings"}
          </button>
        </form>
      )}
    </section>
  );
}
