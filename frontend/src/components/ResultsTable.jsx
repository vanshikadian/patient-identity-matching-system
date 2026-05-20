import PatientCell from "./PatientCell";

const stageColors = {
  ml: "#1f6f78",
  llm: "#d97757",
};

export default function ResultsTable({ results, confidenceBand, onBandChange, runSummary }) {
  const hasResults = results.length > 0;

  return (
    <section className="mt-6 rounded-[2rem] border border-ink/10 bg-white/80 p-6 shadow-sm">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="font-display text-2xl">Results view</h2>
          <p className="mt-1 text-sm text-ink/65">
            Showing the most recent completed run with readable patient details and model decisions.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="rounded-full bg-canvas px-3 py-2 text-sm text-ink/70">Rows: {results.length}</span>
          <span className="rounded-full bg-canvas px-3 py-2 text-sm text-ink/70">Run: {runSummary?.run_id?.slice(0, 8) || "--"}</span>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {[
          { id: "all", label: "All pairs" },
          { id: "high", label: "High confidence" },
          { id: "mid", label: "Needs review" },
          { id: "low", label: "Rejected" },
        ].map((option) => (
          <button
            key={option.id}
            className={`rounded-full px-4 py-2 text-sm font-semibold ${confidenceBand === option.id ? "bg-ink text-white" : "bg-canvas text-ink"}`}
            onClick={() => onBandChange(option.id)}
          >
            {option.label}
          </button>
        ))}
      </div>

      {hasResults ? (
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b border-ink/10 text-ink/60">
                <th className="py-3 pr-4">Patient A</th>
                <th className="py-3 pr-4">Patient B</th>
                <th className="py-3 pr-4">ML score</th>
                <th className="py-3 pr-4">Decision</th>
                <th className="py-3 pr-4">Stage</th>
                <th className="py-3 pr-4">Ground truth</th>
                <th className="py-3 pr-4">Reasoning</th>
              </tr>
            </thead>
            <tbody>
              {results.map((row) => (
                <tr key={row.id} className="border-b border-ink/5 align-top">
                  <td className="py-3 pr-4">
                    <PatientCell patient={row.patient_a} />
                  </td>
                  <td className="py-3 pr-4">
                    <PatientCell patient={row.patient_b} />
                  </td>
                  <td className="py-3 pr-4 font-medium">{row.ml_score?.toFixed(3)}</td>
                  <td className="py-3 pr-4">
                    <span className={`rounded-full px-3 py-1 text-xs font-semibold ${row.final_match ? "bg-olive/15 text-olive" : "bg-ink/8 text-ink"}`}>
                      {row.final_match ? "Match" : "No match"}
                    </span>
                  </td>
                  <td className="py-3 pr-4">
                    <span className="rounded-full px-3 py-1 text-xs font-semibold text-white" style={{ backgroundColor: stageColors[row.decision_source] || "#15212c" }}>
                      {row.decision_source}
                    </span>
                  </td>
                  <td className="py-3 pr-4">{row.ground_truth == null ? "N/A" : row.ground_truth ? "True" : "False"}</td>
                  <td className="py-3 pr-4 text-ink/70">{row.explanation || "Auto decision from the classifier."}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="mt-6 rounded-3xl bg-canvas p-8 text-center text-ink/65">
          Upload records and run the pipeline to populate live candidate-pair results here.
        </div>
      )}
    </section>
  );
}
