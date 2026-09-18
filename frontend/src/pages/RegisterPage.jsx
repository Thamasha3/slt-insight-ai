import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../services/api.js";

const REGIONS = ["WESTERN", "SOUTHERN", "NORTHERN", "EASTERN", "CENTRAL"];

export default function RegisterPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    requested_region: "",
  });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function onSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await api.post("/auth/register", {
        name: form.name,
        email: form.email,
        password: form.password,
        requested_region: form.requested_region || null,
      });
      navigate("/pending");
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Registration failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
        <h2 className="text-lg font-medium text-slt-blue">Request an account</h2>
      <p className="text-sm text-slate-500">
        You cannot choose Admin, Super, or Regional yourself. An administrator assigns your role after review.
      </p>
      {error && <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      <label className="block text-sm">
        Full name
        <input
          required
          minLength={2}
          value={form.name}
          onChange={(e) => update("name", e.target.value)}
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
        />
      </label>
      <label className="block text-sm">
        Work email
        <input
          type="email"
          required
          value={form.email}
          onChange={(e) => update("email", e.target.value)}
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
        />
      </label>
      <label className="block text-sm">
        Password (min 8 characters, include a letter and a number)
        <input
          type="password"
          required
          minLength={8}
          value={form.password}
          onChange={(e) => update("password", e.target.value)}
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
        />
      </label>
      <label className="block text-sm">
        Region (optional — used if you are later approved as Regional)
        <select
          value={form.requested_region}
          onChange={(e) => update("requested_region", e.target.value)}
          className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
        >
          <option value="">None</option>
          {REGIONS.map((region) => (
            <option key={region} value={region}>
              {region}
            </option>
          ))}
        </select>
      </label>
      <button
        type="submit"
        disabled={submitting}
        className="w-full rounded-md bg-slt-blue py-2 text-white hover:bg-slt-blue-dark disabled:opacity-60"
      >
        {submitting ? "Submitting…" : "Submit request"}
      </button>
      <p className="text-center text-sm text-slate-600">
        Already registered?{" "}
        <Link to="/login" className="text-slt-blue underline">
          Sign in
        </Link>
      </p>
    </form>
  );
}
