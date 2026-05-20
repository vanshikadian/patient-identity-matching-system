export default function InfoPill({ label, value }) {
  return (
    <span className="rounded-full bg-canvas px-3 py-2 text-sm text-ink/75">
      <span className="font-semibold text-ink">{label}:</span> {value}
    </span>
  );
}
