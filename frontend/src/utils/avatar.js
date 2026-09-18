export function userInitials(name) {
  const parts = String(name || "")
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2);
  if (!parts.length) return "U";
  return parts.map((part) => part[0].toUpperCase()).join("");
}

export function avatarSrc(avatarUrl) {
  if (!avatarUrl) return null;
  if (/^(https?:|blob:|data:)/i.test(avatarUrl)) return avatarUrl;
  const base = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
  return `${base}${avatarUrl.startsWith("/") ? "" : "/"}${avatarUrl}`;
}
