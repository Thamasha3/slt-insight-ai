import { useEffect, useState } from "react";
import api from "../../services/api.js";

const ROLES = ["NORMAL", "REGIONAL", "SUPER"];
const REGIONS = ["WESTERN", "SOUTHERN", "NORTHERN", "EASTERN", "CENTRAL"];

export default function AdminPendingPage() {
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");
  const [decisions, setDecisions] = useState({});

  async function load() {
    try {
      const response = await api.get("/admin/users/pending");
      setUsers(response.data);
    } catch {
      setError("Could not load pending requests.");
    }
  }

  useEffect(() => {
    load();
  }, []);

  function patch(id, field, value) {
    setDecisions((current) => ({
      ...current,
      [id]: { role: "NORMAL", region: "", ...current[id], [field]: value },
    }));
  }

  async function approve(id) {
    const decision = decisions[id] || { role: "NORMAL", region: "" };
    try {
      await api.post(`/admin/users/${id}/approve`, {
        role: decision.role,
        region: decision.role === "REGIONAL" ? decision.region || null : null,
      });
      await load();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Approve failed.");
    }
  }

  async function reject(id) {
    try {
      await api.post(`/admin/users/${id}/reject`);
      await load();
    } catch {
      setError("Reject failed.");
    }
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-xl font-semibold text-slt-blue">Pending account requests</h2>
      <p className="mt-1 text-sm text-slate-500">Assign NORMAL, REGIONAL, or SUPER. ADMIN cannot be granted through this form.</p>
      {error && <p className="mt-3 text-sm text-red-700">{error}</p>}
      {users.length === 0 && <p className="mt-4 text-sm text-slate-500">No pending requests.</p>}
      <ul className="mt-4 space-y-4">
        {users.map((row) => {
          const decision = decisions[row.id] || { role: "NORMAL", region: row.region || "" };
          return (
            <li key={row.id} className="rounded-lg border border-slate-200 p-4">
              <p className="font-medium">
                {row.name} <span className="font-normal text-slate-500">({row.email})</span>
              </p>
              <div className="mt-3 flex flex-wrap items-end gap-3">
                <label className="text-sm">
                  Role
                  <select
                    value={decision.role}
                    onChange={(e) => patch(row.id, "role", e.target.value)}
                    className="ml-2 rounded-md border border-slate-300 px-2 py-1"
                  >
                    {ROLES.map((role) => (
                      <option key={role} value={role}>
                        {role}
                      </option>
                    ))}
                  </select>
                </label>
                {decision.role === "REGIONAL" && (
                  <label className="text-sm">
                    Region
                    <select
                      value={decision.region}
                      onChange={(e) => patch(row.id, "region", e.target.value)}
                      className="ml-2 rounded-md border border-slate-300 px-2 py-1"
                    >
                      <option value="">Select</option>
                      {REGIONS.map((region) => (
                        <option key={region} value={region}>
                          {region}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                <button
                  type="button"
                  onClick={() => approve(row.id)}
                  className="rounded-md bg-slt-blue px-3 py-1.5 text-sm text-white hover:bg-slt-blue-dark"
                >
                  Approve
                </button>
                <button type="button" onClick={() => reject(row.id)} className="rounded-md border px-3 py-1.5 text-sm">
                  Reject
                </button>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
