import { useState } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import api from "../services/api.js";

export default function ProfilePage() {
  const { user, reload } = useAuth();
  const [name, setName] = useState(user.name);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function onSubmit(event) {
    event.preventDefault();
    setMessage("");
    setError("");
    try {
      await api.put("/users/me", { name });
      await reload();
      setMessage("Profile updated. Your role cannot be changed from this page.");
    } catch {
      setError("Could not update profile.");
    }
  }

  return (
    <section className="max-w-lg rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-xl font-semibold text-teal-900">Your profile</h2>
      <p className="mt-1 text-sm text-slate-500">You may change your display name only. Role and region are set by an administrator.</p>
      {message && <p className="mt-3 rounded-md bg-teal-50 px-3 py-2 text-sm text-teal-800">{message}</p>}
      {error && <p className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      <form onSubmit={onSubmit} className="mt-4 space-y-4">
        <label className="block text-sm">
          Name
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
          />
        </label>
        <label className="block text-sm">
          Email (read-only)
          <input value={user.email} readOnly className="mt-1 w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2" />
        </label>
        <label className="block text-sm">
          Role (read-only)
          <input value={user.role} readOnly className="mt-1 w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2" />
        </label>
        <button type="submit" className="rounded-md bg-teal-800 px-4 py-2 text-white hover:bg-teal-700">
          Save
        </button>
      </form>
    </section>
  );
}
