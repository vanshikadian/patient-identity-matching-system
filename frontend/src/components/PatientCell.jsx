export default function PatientCell({ patient }) {
  const fullName = [patient.first_name, patient.last_name].filter(Boolean).join(" ");
  const location = [patient.city, patient.state, patient.zip].filter(Boolean).join(", ");
  return (
    <div>
      <div className="font-medium text-ink">{fullName || patient.external_id}</div>
      <div className="text-xs text-ink/65">
        {patient.dob || "DOB unknown"} {patient.gender ? `• ${patient.gender}` : ""}
      </div>
      <div className="text-xs text-ink/55">{patient.address || location || patient.external_id}</div>
    </div>
  );
}
