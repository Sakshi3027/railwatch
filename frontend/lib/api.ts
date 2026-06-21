const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export async function fetchKPIs() {
  const res = await fetch(`${API_BASE}/api/kpis`);
  return res.json();
}

export async function fetchScorecard() {
  const res = await fetch(`${API_BASE}/api/scorecard`);
  return res.json();
}

export async function fetchRoutes() {
  const res = await fetch(`${API_BASE}/api/routes`);
  return res.json();
}

export async function fetchTrend() {
  const res = await fetch(`${API_BASE}/api/trend`);
  return res.json();
}

export async function fetchFeatureImportance() {
  const res = await fetch(`${API_BASE}/api/feature-importance`);
  return res.json();
}
