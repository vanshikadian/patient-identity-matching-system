export default function MetricCard({ label, value }) {
  return (
    <div className="rounded-3xl bg-canvas p-4">
      <p className="text-xs uppercase tracking-[0.2em] text-ink/50">{label}</p>
      <p className="mt-2 font-display text-3xl">{value}</p>
    </div>
  );
}
