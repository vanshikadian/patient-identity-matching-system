import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  CartesianGrid,
  Cell,
  PieChart,
  Pie,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { fetchLatestRun, fetchMetrics, fetchResults, fetchRun, runMatching, uploadCsv } from "./api";
import InfoPill from "./components/InfoPill";
import MetricCard from "./components/MetricCard";
import ResultsTable from "./components/ResultsTable";
import UploadCard from "./components/UploadCard";

export default function App() {
  const [files, setFiles] = useState({ A: null, B: null });
  const [status, setStatus] = useState("Upload two CSVs, then run matching to compute live metrics.");
  const [uploadSummary, setUploadSummary] = useState({ A: null, B: null });
  const [results, setResults] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [runSummary, setRunSummary] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [confidenceBand, setConfidenceBand] = useState("all");

  useEffect(() => {
    refresh();
  }, []);

  useEffect(() => {
    if (!runSummary?.run_id || !["queued", "running"].includes(runSummary.status)) {
      return;
    }

    const intervalId = window.setInterval(async () => {
      try {
        const latest = await fetchRun(runSummary.run_id);
        setRunSummary(latest);
        setMetrics(latest.metrics_payload || null);

        const stageMessage = latest.metrics_payload?.message;
        if (stageMessage) {
          setStatus(stageMessage);
        }

        if (latest.status === "completed") {
          setIsRunning(false);
          setStatus(`Run ${latest.run_id} completed. ${latest.candidate_pairs} candidate pairs were evaluated.`);
          await refresh();
          window.clearInterval(intervalId);
        }

        if (latest.status === "failed") {
          setIsRunning(false);
          setStatus(latest.metrics_payload?.message || "The matching run failed.");
          window.clearInterval(intervalId);
        }
      } catch {
        // Ignore transient polling errors.
      }
    }, 2000);

    return () => window.clearInterval(intervalId);
  }, [runSummary?.run_id, runSummary?.status]);

  async function refresh(nextBand = confidenceBand) {
    try {
      const [resultsPayload, metricsPayload] = await Promise.all([
        fetchResults(nextBand === "all" ? undefined : nextBand),
        fetchMetrics(),
      ]);
      setResults(resultsPayload);
      setMetrics(metricsPayload.metrics_payload || null);
      setRunSummary(metricsPayload);
    } catch {
      try {
        const latestRun = await fetchLatestRun();
        setRunSummary(latestRun);
        setMetrics(latestRun.metrics_payload || null);
      } catch {
        // Ignore empty-state load failures.
      }
    }
  }

  async function handleUpload(source) {
    if (!files[source]) {
      return;
    }
    const response = await uploadCsv(source, files[source]);
    setUploadSummary((prev) => ({ ...prev, [source]: response.schema }));
    setStatus(`${source} upload complete: ${response.records_ingested} records ingested.`);
    await refresh();
  }

  async function handleRun() {
    setIsRunning(true);
    setStatus("Queueing a robust background matching run...");
    try {
      const response = await runMatching();
      setRunSummary(response);
      setMetrics(response.metrics_payload || null);
      setStatus("Run accepted. Processing in the background now.");
    } catch (error) {
      setIsRunning(false);
      const message = error?.response?.data?.detail?.message || "Unable to start a matching run.";
      setStatus(message);
    }
  }

  async function handleBandChange(nextBand) {
    setConfidenceBand(nextBand);
    await refresh(nextBand);
  }

  const chartData = metrics
    ? [
        { name: "Baseline", value: (metrics.baseline_accuracy || 0) * 100 },
        { name: "ML Only", value: (metrics.ml_only_accuracy || 0) * 100 },
        { name: "Hybrid", value: (metrics.hybrid_accuracy || 0) * 100 },
      ]
    : [];

  const pieData = [
    { name: "Auto-match", value: runSummary?.auto_matches || 0, fill: "#7a8f5d" },
    { name: "LLM", value: runSummary?.llm_resolved || 0, fill: "#d97757" },
    { name: "Auto-reject", value: runSummary?.auto_rejects || 0, fill: "#15212c" },
  ];

  const runStage = runSummary?.metrics_payload?.stage || "idle";

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_#fff8ef,_#f5f1e8_55%,_#e7dfcf)] text-ink">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        <header className="mb-8 rounded-[2rem] border border-ink/10 bg-white/80 p-8 shadow-[0_20px_80px_rgba(21,33,44,0.08)] backdrop-blur">
          <h1 className="font-display text-4xl leading-tight sm:text-5xl">Patient identity matching for messy healthcare records</h1>
          <p className="mt-4 max-w-3xl text-base text-ink/75">
            Upload two CSVs, run the pipeline, and compare naive matching against the ML and LLM-assisted approach.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <InfoPill label="Mode" value="Background runs" />
            <InfoPill label="CSV support" value="Flexible header mapping" />
            <InfoPill label="Latest stage" value={runStage} />
          </div>
        </header>

        <section className="mb-6 rounded-[2rem] border border-ink/10 bg-ink px-6 py-5 text-white shadow-sm">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.25em] text-white/60">Run monitor</p>
              <p className="mt-1 text-lg font-semibold">{status}</p>
            </div>
            <div className="flex flex-wrap gap-3 text-sm text-white/80">
              <span className="rounded-full border border-white/15 px-3 py-1">Status: {runSummary?.status || "idle"}</span>
              <span className="rounded-full border border-white/15 px-3 py-1">A: {runSummary?.total_a_records ?? "--"}</span>
              <span className="rounded-full border border-white/15 px-3 py-1">B: {runSummary?.total_b_records ?? "--"}</span>
              <span className="rounded-full border border-white/15 px-3 py-1">Pairs: {runSummary?.candidate_pairs ?? "--"}</span>
            </div>
          </div>
        </section>

        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="rounded-[2rem] border border-ink/10 bg-white/80 p-6 shadow-sm">
            <h2 className="font-display text-2xl">Upload view</h2>
            {runSummary?.status && (
              <p className="mt-2 text-xs uppercase tracking-[0.2em] text-ink/45">
                Run status: {runSummary.status}
              </p>
            )}
            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              {["A", "B"].map((source) => (
                <UploadCard
                  key={source}
                  source={source}
                  summary={uploadSummary[source]}
                  onFileChange={(event) => setFiles((prev) => ({ ...prev, [source]: event.target.files?.[0] || null }))}
                  onUpload={() => handleUpload(source)}
                />
              ))}
            </div>
            <button
              className="mt-6 rounded-full bg-warm px-5 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
              onClick={handleRun}
              disabled={isRunning}
            >
              {isRunning ? "Running..." : "Run matching"}
            </button>
          </section>

          <section className="rounded-[2rem] border border-ink/10 bg-white/80 p-6 shadow-sm">
            <h2 className="font-display text-2xl">Metrics dashboard</h2>
            <div className="mt-4 grid gap-4 sm:grid-cols-3">
              <MetricCard label="Precision" value={formatMetric(metrics?.precision)} />
              <MetricCard label="Recall" value={formatMetric(metrics?.recall)} />
              <MetricCard label="F1" value={formatMetric(metrics?.f1)} />
            </div>
            <div className="mt-4 grid gap-4 sm:grid-cols-3">
              <MetricCard label="Pairs" value={runSummary?.candidate_pairs ?? "--"} />
              <MetricCard label="Evaluated" value={metrics?.evaluated_pairs ?? "--"} />
              <MetricCard label="Positives" value={metrics?.positive_pairs ?? "--"} />
            </div>
            <div className="mt-4 grid gap-4 sm:grid-cols-3">
              <MetricCard label="A records" value={runSummary?.total_a_records ?? "--"} />
              <MetricCard label="B records" value={runSummary?.total_b_records ?? "--"} />
              <MetricCard label="Stage" value={runSummary?.metrics_payload?.stage ?? "--"} />
            </div>
            <div className="mt-6 grid gap-6 lg:grid-cols-2">
              <div className="h-64 rounded-3xl bg-canvas p-4">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis domain={[0, 100]} />
                    <Tooltip />
                    <Bar dataKey="value" radius={[12, 12, 0, 0]}>
                      {chartData.map((entry, index) => (
                        <Cell key={index} fill={["#15212c", "#1f6f78", "#d97757"][index]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="h-64 rounded-3xl bg-canvas p-4">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={pieData} innerRadius={45} outerRadius={80} paddingAngle={4} dataKey="value" />
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
            <p className="mt-4 text-sm text-ink/65">
              Accuracy bars are computed from the active uploaded dataset for the latest completed run.
            </p>
          </section>
        </div>

        <ResultsTable
          results={results}
          confidenceBand={confidenceBand}
          onBandChange={handleBandChange}
          runSummary={runSummary}
        />
      </div>
    </div>
  );
}

function formatMetric(value) {
  return value == null ? "--" : value.toFixed(3);
}
