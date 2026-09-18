import { useEffect, useState } from "react";
import api from "../../services/api.js";

const ACTION_TYPES = [
  "LOGIN",
  "LOGOUT",
  "REGISTER",
  "ACCOUNT_APPROVED",
  "ACCOUNT_REJECTED",
  "USER_UPDATED",
  "USER_DEACTIVATED",
  "USER_DELETED",
  "ROLE_CHANGED",
  "SETTINGS_UPDATED",
  "DOCUMENT_UPLOADED",
  "DOCUMENT_APPROVED",
  "DOCUMENT_REJECTED",
  "DOCUMENT_DELETED",
  "DOCUMENT_UPDATED",
  "CHAT_QUERY",
  "DATA_ACCESS",
  "AUDIT_EXPORTED",
];

function toStartIso(date) {
  if (!date) return undefined;
  return `${date}T00:00:00.000Z`;
}

function toEndIso(date) {
  if (!date) return undefined;
  return `${date}T23:59:59.999Z`;
}

export default function AdminAuditPage() {
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState("");
  const [exporting, setExporting] = useState(false);
  const [userId, setUserId] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [actionType, setActionType] = useState("");

  useEffect(() => {
    const params = {};
    if (userId.trim()) params.user_id = userId.trim();
    if (startDate) params.start_date = toStartIso(startDate);
    if (endDate) params.end_date = toEndIso(endDate);
    if (actionType) params.action_type = actionType;

    api
      .get("/admin/audit-logs", { params })
      .then((response) => setLogs(response.data))
      .catch(() => setError("Could not load audit logs."));
  }, [userId, startDate, endDate, actionType]);

  async function exportCsv() {
    setError("");
    setExporting(true);
    try {
      const response = await api.get("/admin/audit-logs/export", { responseType: "blob" });
      const blob = new Blob([response.data], { type: "text/csv;charset=utf-8" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "audit-logs.csv";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      setError("Could not export audit logs.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-slt-blue">Audit logs</h2>
          <p className="mt-1 text-sm text-slate-500">Actions only — no confidential document text is stored here.</p>
        </div>
        <button
          type="button"
          onClick={exportCsv}
          disabled={exporting}
          className="rounded-md bg-slt-blue px-3 py-2 text-sm text-white hover:bg-slt-blue-dark disabled:opacity-60"
        >
          {exporting ? "Exporting…" : "Export CSV"}
        </button>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <label className="text-sm text-ink">
          User ID
          <input
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            placeholder="Filter by user id"
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
        <fieldset className="sm:col-span-2 grid gap-3 sm:grid-cols-2">
          <legend className="text-sm text-ink">Date Range</legend>
          <label className="text-sm text-ink">
            Start date
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </label>
          <label className="text-sm text-ink">
            End date
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
            />
          </label>
        </fieldset>
        <label className="text-sm text-ink">
          Action Type
          <select
            value={actionType}
            onChange={(e) => setActionType(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">All actions</option>
            {ACTION_TYPES.map((action) => (
              <option key={action} value={action}>
                {action}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error && <p className="mt-3 text-sm text-red-700">{error}</p>}
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-left text-sm text-ink">
          <thead className="border-b text-slate-500">
            <tr>
              <th className="py-2">Time</th>
              <th>Action</th>
              <th>Resource</th>
              <th>Status</th>
              <th>User id</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((row) => (
              <tr key={row.id} className="border-b border-slate-100">
                <td className="py-2">{row.timestamp}</td>
                <td>{row.action}</td>
                <td>{row.resource}</td>
                <td>{row.status}</td>
                <td className="font-mono text-xs">{row.user_id}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {logs.length === 0 && <p className="mt-4 text-sm text-slate-500">No audit entries match these filters.</p>}
      </div>
    </section>
  );
}
