from pathlib import Path

import pandas as pd
from sqlalchemy import delete

from common.database import Base, SessionLocal, engine
from common.models import CandidatePair, GroundTruthMatch, MatchRun, Patient
from common.utils import hashed_embedding, normalize_phone, normalize_text, normalize_zip, parse_date, sha256_record


EXPECTED_COLUMNS = [
    "record_id",
    "first_name",
    "last_name",
    "dob",
    "gender",
    "address",
    "city",
    "state",
    "zip",
    "ssn_last4",
    "phone",
]

COLUMN_ALIASES = {
    "record_id": [
        "record_id",
        "id",
        "patient_id",
        "member_id",
        "person_id",
        "empi",
        "mrn",
        "medical_record_number",
    ],
    "first_name": ["first_name", "firstname", "first", "given_name", "forename", "fname"],
    "last_name": ["last_name", "lastname", "last", "surname", "family_name", "lname"],
    "dob": ["dob", "date_of_birth", "birth_date", "birthdate", "date birth"],
    "gender": ["gender", "sex"],
    "address": ["address", "street_address", "address_line_1", "address1", "street"],
    "city": ["city", "town"],
    "state": ["state", "province", "region", "state_code"],
    "zip": ["zip", "zipcode", "zip_code", "postal_code", "postcode"],
    "ssn_last4": ["ssn_last4", "ssn", "social_security_number", "social_security", "last4_ssn"],
    "phone": ["phone", "phone_number", "mobile", "telephone", "cell"],
}

FULL_NAME_ALIASES = ["full_name", "name", "patient_name", "member_name"]
ADDRESS_LINE_2_ALIASES = ["address_line_2", "address2", "street_2", "apt", "apartment", "unit"]


def initialize_database():
    Base.metadata.create_all(bind=engine)


def normalize_dataframe(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    working_df = df.copy()
    original_columns = list(working_df.columns)
    normalized_header_lookup = {_normalize_header(column): column for column in working_df.columns}
    mapping = {}
    warnings = []

    for target, aliases in COLUMN_ALIASES.items():
        source = _find_source_column(normalized_header_lookup, aliases)
        mapping[target] = source
        if source and source != target:
            working_df[target] = working_df[source]

    full_name_col = _find_source_column(normalized_header_lookup, FULL_NAME_ALIASES)
    if full_name_col and ("first_name" not in working_df.columns or "last_name" not in working_df.columns):
        split_names = working_df[full_name_col].map(_split_full_name)
        if "first_name" not in working_df.columns:
            working_df["first_name"] = split_names.map(lambda value: value[0])
            mapping["first_name"] = full_name_col
        if "last_name" not in working_df.columns:
            working_df["last_name"] = split_names.map(lambda value: value[1])
            mapping["last_name"] = full_name_col

    if "address" not in working_df.columns:
        line1 = _find_source_column(normalized_header_lookup, COLUMN_ALIASES["address"])
        line2 = _find_source_column(normalized_header_lookup, ADDRESS_LINE_2_ALIASES)
        if line1 or line2:
            working_df["address"] = [
                " ".join(part for part in [str(a).strip() if pd.notna(a) else "", str(b).strip() if pd.notna(b) else ""] if part).strip() or None
                for a, b in zip(
                    working_df[line1] if line1 else [None] * len(working_df),
                    working_df[line2] if line2 else [None] * len(working_df),
                )
            ]
            mapping["address"] = ", ".join(part for part in [line1, line2] if part)

    for column in EXPECTED_COLUMNS:
        if column not in working_df.columns:
            working_df[column] = None
            mapping.setdefault(column, None)

    if working_df["record_id"].isna().all():
        working_df["record_id"] = [f"generated-{idx:07d}" for idx in range(len(working_df))]
        warnings.append("No record ID column was found. Generated record IDs were assigned.")
        mapping["record_id"] = "(generated)"

    if working_df["first_name"].isna().all() and working_df["last_name"].isna().all():
        warnings.append("No recognizable name columns were found. Matching quality will be reduced.")

    if working_df["dob"].isna().all():
        warnings.append("No recognizable DOB column was found. Matching quality will be reduced.")

    working_df["first_name"] = working_df["first_name"].map(normalize_text)
    working_df["last_name"] = working_df["last_name"].map(normalize_text)
    working_df["address"] = working_df["address"].map(normalize_text)
    working_df["city"] = working_df["city"].map(normalize_text)
    working_df["state"] = working_df["state"].map(lambda value: normalize_text(value).upper() if normalize_text(value) else None)
    working_df["phone"] = working_df["phone"].map(normalize_phone)
    working_df["zip"] = working_df["zip"].map(normalize_zip)
    working_df["dob"] = working_df["dob"].map(parse_date)
    working_df["ssn_last4"] = working_df["ssn_last4"].map(_normalize_ssn_last4)
    working_df["gender"] = working_df["gender"].map(_normalize_gender)

    metadata = {
        "original_columns": original_columns,
        "mapped_columns": mapping,
        "warnings": warnings,
    }
    return working_df, metadata


def _json_safe_row(row: dict) -> dict:
    safe = {}
    for key, value in row.items():
        if isinstance(value, pd.Timestamp):
            safe[key] = value.strftime("%Y-%m-%d")
        elif pd.isna(value):
            safe[key] = None
        else:
            safe[key] = value
    return safe


def ingest_csv(path: str | Path, source: str, replace_existing: bool = True) -> dict:
    initialize_database()
    df = pd.read_csv(path)
    df, metadata = normalize_dataframe(df)

    with SessionLocal() as db:
        if replace_existing:
            db.execute(delete(CandidatePair))
            db.execute(delete(MatchRun))
            db.execute(delete(GroundTruthMatch))
            db.execute(delete(Patient).where(Patient.source == source))
            db.commit()

        for idx, row in enumerate(df.to_dict(orient="records"), start=1):
            normalized = {
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "dob": row["dob"].date() if pd.notna(row["dob"]) else None,
                "gender": row["gender"],
                "address": row["address"],
                "city": row["city"],
                "state": row["state"],
                "zip": row["zip"],
                "ssn_last4": row["ssn_last4"],
                "phone": row["phone"],
            }
            patient = Patient(
                source=source,
                external_id=str(row["record_id"]),
                record_hash=sha256_record(normalized),
                embedding=hashed_embedding(
                    " ".join(filter(None, [normalized["first_name"], normalized["last_name"], str(normalized["dob"] or "")]))
                ),
                raw_payload=_json_safe_row(row),
                **normalized,
            )
            db.add(patient)
            db.flush()
            if idx % 500 == 0:
                db.commit()
        db.commit()
    return {
        "records_ingested": len(df),
        "schema": metadata,
    }


def ingest_ground_truth_csv(path: str | Path, replace_existing: bool = True) -> dict:
    initialize_database()
    df = pd.read_csv(path)
    normalized_columns = {_normalize_header(column): column for column in df.columns}
    record_a_col = normalized_columns.get("record_a_id")
    record_b_col = normalized_columns.get("record_b_id")
    if not record_a_col or not record_b_col:
        raise ValueError("Ground truth CSV must include record_a_id and record_b_id columns.")

    trimmed = df[[record_a_col, record_b_col]].copy()
    trimmed.columns = ["record_a_id", "record_b_id"]
    trimmed = trimmed.dropna().drop_duplicates()

    with SessionLocal() as db:
        if replace_existing:
            db.execute(delete(CandidatePair))
            db.execute(delete(MatchRun))
            db.execute(delete(GroundTruthMatch))
            db.commit()

        for idx, row in enumerate(trimmed.to_dict(orient="records"), start=1):
            db.add(
                GroundTruthMatch(
                    record_a_external_id=str(row["record_a_id"]),
                    record_b_external_id=str(row["record_b_id"]),
                )
            )
            if idx % 500 == 0:
                db.flush()
        db.commit()

    return {
        "records_ingested": len(trimmed),
        "schema": {
            "original_columns": list(df.columns),
            "mapped_columns": {"record_a_id": record_a_col, "record_b_id": record_b_col},
            "warnings": [],
        },
    }


def main():
    artifacts = Path("artifacts/generated")
    initialize_database()
    count_a = ingest_csv(artifacts / "records_A.csv", "A")
    count_b = ingest_csv(artifacts / "records_B.csv", "B")
    print(f"Ingested {count_a['records_ingested']} A-side records and {count_b['records_ingested']} B-side records")


def _normalize_header(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in str(value)).strip("_")


def _find_source_column(normalized_header_lookup: dict[str, str], aliases: list[str]) -> str | None:
    for alias in aliases:
        direct = normalized_header_lookup.get(_normalize_header(alias))
        if direct:
            return direct
    for normalized, original in normalized_header_lookup.items():
        if any(_normalize_header(alias) in normalized for alias in aliases):
            return original
    return None


def _split_full_name(value) -> tuple[str | None, str | None]:
    if value is None or pd.isna(value):
        return None, None
    parts = str(value).strip().split()
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], " ".join(parts[1:])


def _normalize_gender(value) -> str | None:
    if pd.isna(value) or value is None or value == "":
        return None
    text = str(value).strip().lower()
    if text.startswith("f"):
        return "F"
    if text.startswith("m"):
        return "M"
    if text in {"female", "woman", "girl"}:
        return "F"
    if text in {"male", "man", "boy"}:
        return "M"
    return str(value).upper()[0]


def _normalize_ssn_last4(value) -> str | None:
    if pd.isna(value) or value is None or value == "":
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return digits[-4:] if digits else None


if __name__ == "__main__":
    main()
