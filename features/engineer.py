import jellyfish
import pandas as pd


FEATURE_COLUMNS = [
    "first_name_similarity",
    "last_name_similarity",
    "last_name_soundex_match",
    "last_name_metaphone_match",
    "dob_exact_match",
    "dob_year_match",
    "dob_month_day_match",
    "dob_off_by_one",
    "gender_match",
    "address_token_overlap",
    "zip_match",
    "zip_prefix_match",
    "ssn_last4_match",
    "phone_match",
    "embedding_score",
]


def build_features(candidate_df: pd.DataFrame, records_a, records_b) -> pd.DataFrame:
    if candidate_df.empty:
        return pd.DataFrame(columns=["record_a_id", "record_b_id", *FEATURE_COLUMNS])

    lookup_a = {record.id: record for record in records_a}
    lookup_b = {record.id: record for record in records_b}
    rows = []
    for row in candidate_df.to_dict(orient="records"):
        record_a = lookup_a[row["record_a_id"]]
        record_b = lookup_b[row["record_b_id"]]
        rows.append(
            {
                "record_a_id": record_a.id,
                "record_b_id": record_b.id,
                "first_name_a": record_a.first_name,
                "last_name_a": record_a.last_name,
                "dob_a": str(record_a.dob) if record_a.dob else None,
                "gender_a": record_a.gender,
                "address_a": record_a.address,
                "ssn_last4_a": record_a.ssn_last4,
                "first_name_b": record_b.first_name,
                "last_name_b": record_b.last_name,
                "dob_b": str(record_b.dob) if record_b.dob else None,
                "gender_b": record_b.gender,
                "address_b": record_b.address,
                "ssn_last4_b": record_b.ssn_last4,
                "embedding_score": row["embedding_score"],
                "first_name_similarity": _safe_jw(record_a.first_name, record_b.first_name),
                "last_name_similarity": _safe_jw(record_a.last_name, record_b.last_name),
                "last_name_soundex_match": _safe_phonetic(record_a.last_name, record_b.last_name, jellyfish.soundex),
                "last_name_metaphone_match": _safe_phonetic(record_a.last_name, record_b.last_name, jellyfish.metaphone),
                "dob_exact_match": _bool_eq(record_a.dob, record_b.dob),
                "dob_year_match": int(bool(record_a.dob and record_b.dob and record_a.dob.year == record_b.dob.year)),
                "dob_month_day_match": int(
                    bool(
                        record_a.dob
                        and record_b.dob
                        and record_a.dob.month == record_b.dob.month
                        and record_a.dob.day == record_b.dob.day
                    )
                ),
                "dob_off_by_one": int(bool(record_a.dob and record_b.dob and abs((record_a.dob - record_b.dob).days) == 1)),
                "gender_match": _bool_eq(record_a.gender, record_b.gender),
                "address_token_overlap": _token_jaccard(record_a.address, record_b.address),
                "zip_match": _bool_eq(record_a.zip, record_b.zip),
                "zip_prefix_match": int(
                    bool(record_a.zip and record_b.zip and str(record_a.zip)[:3] == str(record_b.zip)[:3])
                ),
                "ssn_last4_match": _bool_eq(record_a.ssn_last4, record_b.ssn_last4),
                "phone_match": _bool_eq(record_a.phone, record_b.phone),
            }
        )

    return pd.DataFrame(rows)


def _safe_jw(left: str | None, right: str | None) -> float:
    if not left or not right:
        return 0.0
    return float(jellyfish.jaro_winkler_similarity(left, right))


def _safe_phonetic(left: str | None, right: str | None, fn) -> int:
    if not left or not right:
        return 0
    return int(fn(left) == fn(right))


def _bool_eq(left, right) -> int:
    return int(bool(left and right and left == right))


def _token_jaccard(left: str | None, right: str | None) -> float:
    if not left or not right:
        return 0.0
    left_tokens = set(left.split())
    right_tokens = set(right.split())
    union = left_tokens | right_tokens
    if not union:
        return 0.0
    return float(len(left_tokens & right_tokens) / len(union))
