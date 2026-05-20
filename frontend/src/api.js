import axios from "axios";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api",
  headers: {
    "x-api-key": import.meta.env.VITE_API_KEY || "demo-key",
  },
});

export async function uploadCsv(source, file) {
  const form = new FormData();
  form.append("file", file);
  const response = await client.post(`/records/upload?source=${source}`, form);
  return response.data;
}

export async function runMatching() {
  const response = await client.post("/match/run", { top_k: 10 });
  return response.data;
}

export async function fetchLatestRun() {
  const response = await client.get("/match/runs/latest");
  return response.data;
}

export async function fetchRun(runId) {
  const response = await client.get(`/match/runs/${runId}`);
  return response.data;
}

export async function fetchResults(confidenceBand) {
  const params = confidenceBand ? { confidence_band: confidenceBand } : undefined;
  const response = await client.get("/match/results", { params });
  return response.data;
}

export async function fetchMetrics() {
  const response = await client.get("/metrics");
  return response.data;
}
