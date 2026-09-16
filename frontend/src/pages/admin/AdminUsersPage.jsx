import { useEffect, useState } from "react";
import api from "../../services/api.js";

const ROLES = ["NORMAL", "REGIONAL", "SUPER", "ADMIN"];
const REGIONS = ["WESTERN", "SOUTHERN", "NORTHERN", "EASTERN", "CENTRAL"];

export default function AdminUsersPage() {
  const [users, setUsers] = useState([]);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    role: "NORMAL",
    region: "",
  });

  async function load() {
    try {
      const response = await api.get("/admin/users");
      setUsers(response.data);
    } catch {
      setError("Could not load users. If you are not an Admin, the API correctly returns 403.");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function createUser(event) {
    event.preventDefault();
    setError("");
    try {
      await api.post("/admin/users", {
        name: form.name,
        email: form.email,
        password: form.password,
        role: form.role,
        region: form.role === "REGIONAL" ? form.region || null : null,
      });
      setForm({ name: "", email: "", password: "", role: "NORMAL", region: "" });
      await load();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Could not create user.");
    }
  }

  async function deactivate(id) {
    setBusyId(id);
    try {
      await api.delete(`/admin/users/${id}`);
      await load();
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section className="space-y-6">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-teal-900">Create user</h2>
        <p className="mt-1 text-sm text-slate-500">
          Admin-created accounts become ACTIVE immediately. ADMIN can only be assigned to the two pre-approved emails.
        </p>
        {error && <p className="mt-3 text-sm text-red-700">{error}</p>}
        <form onSubmit={createUser} className="mt-4 grid gap-3 sm:grid-cols-2">
          <input
            required
            placeholder="Name"
            value={form.name}
            onChange={(e) => setForm((current) => ({ ...current, name: e.target.value }))}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <input
            required
            type="email"
            placeholder="Email"
            value={form.email}
            onChange={(e) => setForm((current) => ({ ...current, email: e.target.value }))}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <input
            required
            type="password"
            minLength={8}
            placeholder="Temporary password"
            value={form.password}
            onChange={(e) => setForm((current) => ({ ...current, password: e.target.value }))}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <select
            value={form.role}
            onChange={(e) => setForm((current) => ({ ...current, role: e.target.value, region: "" }))}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            {ROLES.map((role) => (
              <option key={role} value={role}>
                {role}
              </option>
            ))}
          </select>
          {form.role === "REGIONAL" && (
            <select
              required
              value={form.region}
              onChange={(e) => setForm((current) => ({ ...current, region: e.target.value }))}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm"
            >
              <option value="">Select region</option>
              {REGIONS.map((region) => (
                <option key={region} value={region}>
                  {region}
                </option>
              ))}
            </select>
          )}
          <button type="submit" className="rounded-md bg-teal-800 px-4 py-2 text-sm text-white">
            Create
          </button>
        </form>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-xl font-semibold text-teal-900">User management</h2>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="border-b text-slate-500">
            <tr>
              <th className="py-2">Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Region</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {users.map((row) => (
              <tr key={row.id} className="border-b border-slate-100">
                <td className="py-2">{row.name}</td>
                <td>{row.email}</td>
                <td>{row.role}</td>
                <td>{row.region || "—"}</td>
                <td>{row.status}</td>
                <td>
                  {row.status === "ACTIVE" && (
                    <button
                      type="button"
                      disabled={busyId === row.id}
                      onClick={() => deactivate(row.id)}
                      className="text-red-700 hover:underline"
                    >
                      Deactivate
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      </div>
    </section>
  );
}
