import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext.jsx";
import api from "../services/api.js";
import Avatar from "../components/Avatar.jsx";

export default function ProfilePage() {
  const { user, reload } = useAuth();
  const [name, setName] = useState(user.name);
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(user.avatar_url || null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setName(user.name);
    if (!file) setPreview(user.avatar_url || null);
  }, [user, file]);

  useEffect(() => {
    return () => {
      if (preview && preview.startsWith("blob:")) URL.revokeObjectURL(preview);
    };
  }, [preview]);

  function onPickFile(event) {
    const next = event.target.files?.[0];
    if (!next) return;
    if (preview && preview.startsWith("blob:")) URL.revokeObjectURL(preview);
    setFile(next);
    setPreview(URL.createObjectURL(next));
  }

  async function onSubmit(event) {
    event.preventDefault();
    setMessage("");
    setError("");
    setSaving(true);
    try {
      await api.put("/users/me", { name });
      if (file) {
        const data = new FormData();
        data.append("file", file);
        await api.post("/users/me/avatar", data);
        setFile(null);
      }
      await reload();
      setMessage("Profile updated. Your role cannot be changed from this page.");
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Could not update profile.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="max-w-lg rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-xl font-semibold text-slt-blue">Your profile</h2>
      <p className="mt-1 text-sm text-slate-500">You may change your display name and profile picture. Role and region are set by an administrator.</p>
      {message && <p className="mt-3 rounded-md bg-mobitel/10 px-3 py-2 text-sm text-mobitel-dark">{message}</p>}
      {error && <p className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
      <form onSubmit={onSubmit} className="mt-4 space-y-4">
        <div className="flex flex-col items-center gap-3 rounded-xl border border-slate-200 bg-page px-4 py-5">
          <Avatar name={name || user.name} src={preview} size="lg" />
          <label className="cursor-pointer text-sm font-medium text-slt-blue hover:underline">
            Upload profile picture
            <input type="file" accept="image/png,image/jpeg,image/webp,image/gif" className="sr-only" onChange={onPickFile} />
          </label>
          <p className="text-center text-xs text-slate-500">JPEG, PNG, WebP, or GIF. Preview updates before you click Save.</p>
        </div>
        <label className="block text-sm text-ink">
          Name
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-ink"
          />
        </label>
        <label className="block text-sm text-ink">
          Email (read-only)
          <input value={user.email} readOnly className="mt-1 w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2" />
        </label>
        <label className="block text-sm text-ink">
          Role (read-only)
          <input value={user.role} readOnly className="mt-1 w-full rounded-md border border-slate-200 bg-slate-50 px-3 py-2" />
        </label>
        <button
          type="submit"
          disabled={saving}
          className="rounded-md bg-mobitel px-4 py-2 text-white hover:bg-mobitel-dark disabled:opacity-60"
        >
          {saving ? "Saving…" : "Save"}
        </button>
      </form>
    </section>
  );
}
