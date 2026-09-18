import { useEffect, useState } from "react";
import api from "../../services/api.js";
import { useAuth } from "../../context/AuthContext.jsx";

const CATEGORIES = ["GENERAL", "REGIONAL", "CONFIDENTIAL_INTERNAL"];
const REGIONS = ["WESTERN", "SOUTHERN", "NORTHERN", "EASTERN", "CENTRAL"];

export default function AdminKnowledgePage() {
  const { user } = useAuth();
  const isSuperUser = user?.role === "SUPER";
  const canStewardDocuments = isSuperUser;
  const [documents, setDocuments] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState(null);
  const [form, setForm] = useState({
    file: null,
    category: "GENERAL",
    region: "",
    description: "",
  });

  async function load() {
    try {
      const response = await api.get("/admin/knowledge");
      setDocuments(response.data);
    } catch {
      setError("Could not load knowledge sources. Admin or Super User role is required.");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function onUpload(event) {
    event.preventDefault();
    setError("");
    if (!form.file) {
      setError("Choose a PDF, Word, CSV, or Excel file.");
      return;
    }
    if (form.category === "REGIONAL" && !form.region) {
      setError("Regional knowledge requires a region.");
      return;
    }
    const data = new FormData();
    data.append("file", form.file);
    data.append("category", form.category);
    data.append("description", form.description);
    if (form.category === "REGIONAL" || form.category === "CONFIDENTIAL_INTERNAL") {
      if (form.region) data.append("region", form.region);
    }
    setBusy(true);
    try {
      await api.post("/admin/knowledge/upload", data);
      setForm({ file: null, category: "GENERAL", region: "", description: "" });
      event.target.reset();
      await load();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  async function act(path) {
    setError("");
    try {
      await api.post(path);
      await load();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Action failed.");
    }
  }

  async function remove(id) {
    if (!window.confirm("Delete this document and its extracted chunks?")) return;
    try {
      await api.delete(`/admin/knowledge/${id}`);
      setPreview(null);
      await load();
    } catch {
      setError("Delete failed.");
    }
  }

  async function showChunks(id) {
    try {
      const response = await api.get(`/admin/knowledge/${id}/chunks`);
      setPreview({ id, chunks: response.data });
      
      // Automatically scroll to the bottom of the page where the preview renders
      setTimeout(() => {
        window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
      }, 100);
      
    } catch {
      setError("Could not load chunks.");
    }
  }

  return (
    <section className="space-y-6">
      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-slt-blue">Upload knowledge source</h2>
        <p className="mt-1 text-sm text-slate-500">
          Upload <strong>PDF</strong>, <strong>Word (.docx)</strong>, <strong>CSV</strong>, or{" "}
          <strong>Excel (.xlsx)</strong>. Tables are stored as labeled rows (column names kept). Documents stay{" "}
          <strong>PENDING</strong> until a Super User approves them. Search only returns APPROVED chunks. Admin can
          upload and preview, but Delete and Approve/Reject are Super User only.
        </p>
        {error && <p className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
        <form onSubmit={onUpload} className="mt-4 grid gap-4 sm:grid-cols-2">
          <label className="block text-sm sm:col-span-2">
            File (PDF, Word, CSV, or Excel)
            <input
              type="file"
              accept=".pdf,.docx,.csv,.xlsx,.xls"
              required
              onChange={(e) => setForm((current) => ({ ...current, file: e.target.files[0] }))}
              className="mt-1 block w-full text-sm"
            />
          </label>
          <label className="block text-sm">
            Category
            <select
              value={form.category}
              onChange={(e) => setForm((current) => ({ ...current, category: e.target.value, region: "" }))}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            >
              {CATEGORIES.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            Region {form.category === "REGIONAL" ? "(required)" : "(leave empty for GENERAL)"}
            <select
              value={form.region}
              disabled={form.category === "GENERAL"}
              onChange={(e) => setForm((current) => ({ ...current, region: e.target.value }))}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 disabled:bg-slate-100"
            >
              <option value="">None</option>
              {REGIONS.map((region) => (
                <option key={region} value={region}>
                  {region}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm sm:col-span-2">
            Description
            <textarea
              value={form.description}
              onChange={(e) => setForm((current) => ({ ...current, description: e.target.value }))}
              rows={2}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
            />
          </label>
          <button
            type="submit"
            disabled={busy}
            className="rounded-md bg-slt-blue px-4 py-2 text-sm text-white hover:bg-slt-blue-dark disabled:opacity-60"
          >
            {busy ? "Processing…" : "Upload and extract"}
          </button>
        </form>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-slt-blue">Document management</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b text-slate-500">
              <tr>
                <th className="py-2">File</th>
                <th>Category</th>
                <th>Region</th>
                <th>Status</th>
                <th>Chunks</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {documents.map((row) => (
                <tr key={row.id} className="border-b border-slate-100 align-top">
                  <td className="py-2">
                    <div className="font-medium">{row.filename}</div>
                    <div className="text-xs text-slate-500">{row.description || "—"}</div>
                    {row.error_message && <div className="text-xs text-red-700">{row.error_message}</div>}
                  </td>
                  <td>{row.category}</td>
                  <td>{row.region || "—"}</td>
                  <td>{row.status}</td>
                  <td>{row.chunk_count}</td>
                  <td className="space-x-2 whitespace-nowrap py-2">
                    <button type="button" className="text-slt-blue hover:underline" onClick={() => showChunks(row.id)}>
                      Preview
                    </button>
                    {canStewardDocuments && (row.status === "PENDING" || row.status === "REJECTED") && (
                      <button
                        type="button"
                        className="text-mobitel-dark hover:underline"
                        onClick={() => act(`/admin/knowledge/${row.id}/approve`)}
                      >
                        Approve
                      </button>
                    )}
                    {canStewardDocuments && (row.status === "PENDING" || row.status === "APPROVED") && (
                      <button
                        type="button"
                        className="text-amber-800 hover:underline"
                        onClick={() => act(`/admin/knowledge/${row.id}/reject`)}
                      >
                        Reject
                      </button>
                    )}
                    {canStewardDocuments && (
                      <button type="button" className="text-red-700 hover:underline" onClick={() => remove(row.id)}>
                        Delete
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {documents.length === 0 && <p className="mt-4 text-sm text-slate-500">No documents uploaded yet.</p>}
        </div>
      </div>

      {preview && (
        <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-slt-blue">Extracted chunks (preview)</h3>
            <button type="button" className="text-sm text-slate-500" onClick={() => setPreview(null)}>
              Close
            </button>
          </div>
          <ul className="mt-3 space-y-3">
            {preview.chunks.map((chunk) => (
              <li key={chunk.id} className="rounded-md bg-slate-50 p-3 text-sm">
                <p className="text-xs text-slate-500">
                  {chunk.filename}
                  {chunk.source_page ? ` · Page ${chunk.source_page}` : ""}
                  {chunk.sheet_name ? ` · Sheet ${chunk.sheet_name}` : ""}
                  {chunk.source_row ? ` · Row ${chunk.source_row}` : ""} · {chunk.status}
                </p>
                <p className="mt-1 whitespace-pre-wrap text-slate-800">{chunk.content}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}