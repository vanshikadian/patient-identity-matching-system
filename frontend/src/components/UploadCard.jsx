export default function UploadCard({ source, onFileChange, onUpload, summary, title, buttonLabel }) {
  return (
    <div className="rounded-3xl border border-dashed border-ink/20 bg-[linear-gradient(180deg,rgba(255,255,255,0.75),rgba(245,241,232,0.95))] p-4">
      <label className="mb-3 block text-sm font-semibold">{title || `Source ${source}`}</label>
      <input
        className="block w-full text-sm text-ink/70 file:mr-4 file:rounded-full file:border-0 file:bg-ink file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white"
        type="file"
        accept=".csv"
        onChange={onFileChange}
      />
      <button className="mt-4 rounded-full bg-accent px-4 py-2 text-sm font-semibold text-white" onClick={onUpload}>
        {buttonLabel || `Upload source ${source}`}
      </button>
      {summary && (
        <div className="mt-4 rounded-2xl bg-white/70 p-3 text-xs text-ink/70">
          <div className="font-semibold text-ink">Detected columns</div>
          <div className="mt-1">
            {Object.entries(summary.mapped_columns || {})
              .filter(([, value]) => value)
              .slice(0, 6)
              .map(([target, value]) => `${target}: ${value}`)
              .join(" | ")}
          </div>
          {summary.warnings?.length > 0 && <div className="mt-2 text-warm">{summary.warnings.join(" ")}</div>}
        </div>
      )}
    </div>
  );
}
