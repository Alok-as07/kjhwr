async function get(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path} failed (${res.status})`);
  return res.json();
}

export const api = {
  meta: () => get("/api/meta"),
  summary: (cutoff) => get(`/api/summary?cutoff=${cutoff}`),
  horizon: () => get("/api/horizon"),
  series: (start, end, cutoff) => get(`/api/series?start=${start}&end=${end}&cutoff=${cutoff}`),
};
