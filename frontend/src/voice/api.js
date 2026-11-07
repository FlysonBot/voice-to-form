// Tiny API helper. Set VITE_API_URL and VITE_MOCK=true in frontend/.env
const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const MOCK = import.meta.env.VITE_MOCK === "true";

export async function post(path, body, { signal } = {}) {
  const url = `${BASE}${path}${MOCK ? (path.includes("?") ? "&" : "?") + "mock=true" : ""}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data;
}
