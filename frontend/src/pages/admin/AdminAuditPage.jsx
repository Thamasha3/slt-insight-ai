import { useEffect, useState } from "react";
import api from "../../services/api.js";

export default function AdminAuditPage() {
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState("");
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    api
      .get("/admin/audit-logs")
      .then((response) => setLogs(response.data))
      .catch(() => setError("Could not load audit logs."));
  }, []);

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
          <h2 className="text-xl font-semibold text-teal-900">Audit logs</h2>
          <p className="mt-1 text-sm text-slate-500">Actions only — no confidential document text is stored here.</p>
        </div>
        <button
          type="button"
          onClick={exportCsv}
          disabled={exporting}
          className="rounded-md bg-teal-800 px-3 py-2 text-sm text-white hover:bg-teal-700 disabled:opacity-60"
        >
          {exporting ? "Exporting…" : "Export CSV"}
        </button>
      </div>
      {error && <p className="mt-3 text-sm text-red-700">{error}</p>}
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-left text-sm">
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
      </div>
    </section>
  );
}
