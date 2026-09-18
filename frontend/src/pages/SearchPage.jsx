import { useState } from "react";
import api from "../services/api.js";
import { useAuth } from "../context/AuthContext.jsx";

function citation(match) {
  const parts = [match.filename];
  if (match.source_page) parts.push(`Page ${match.source_page}`);
  if (match.sheet_name) parts.push(`Sheet ${match.sheet_name}`);
  if (match.source_row) parts.push(`Row ${match.source_row}`);
  return parts.join(" · ");
}

export default function SearchPage() {
  const { user } = useAuth();
  const [query, setQuery] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function onSearch(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const response = await api.post("/retrieval/search", { query });
      setResult(response.data);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Search failed.");
      setResult(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-6">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-slt-blue">Search approved knowledge</h2>
        <p className="mt-1 max-w-2xl text-sm text-slate-500">
          This is retrieval only — not the chatbot. The API uses your role ({user.role}
          {user.region ? `, ${user.region}` : ""}) and returns <strong>approved</strong> snippets you
          are allowed to see. Gemini is not called yet.
        </p>
        {user.role === "ADMIN" && (
          <p className="mt-3 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900">
            Admin is a system role. Until SLT decides otherwise, Admin search returns no employee
            knowledge (see docs/ambiguities.md).
          </p>
        )}
        {error && <p className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        <form onSubmit={onSearch} className="mt-4 flex flex-col gap-3 sm:flex-row">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            required
            placeholder="Ask about approved sample information…"
            className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-slt-blue px-4 py-2 text-sm text-white hover:bg-slt-blue-dark disabled:opacity-60"
          >
            {busy ? "Searching…" : "Search"}
          </button>
        </form>
      </div>

      {result && (
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <p className="text-xs text-slate-500">
            Allowed categories: {result.allowed_categories.join(", ") || "none"}
            {result.region_filter ? ` · Region filter: ${result.region_filter}` : ""}
          </p>
          {result.insufficient_evidence ? (
            <p className="mt-4 rounded-md bg-slate-50 px-3 py-3 text-sm text-slate-700">
              Insufficient Evidence — no approved snippets matching this question were found in
              knowledge you may access.
            </p>
          ) : (
            <ul className="mt-4 space-y-3">
              {result.matches.map((match, index) => (
                <li key={`${match.document_id}-${index}`} className="rounded-md bg-slate-50 p-3 text-sm">
                  <p className="text-xs text-slate-500">
                    {citation(match)} · {match.category}
                    {match.region ? ` · ${match.region}` : ""}
                  </p>
                  <p className="mt-1 whitespace-pre-wrap text-slate-800">{match.content}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}
