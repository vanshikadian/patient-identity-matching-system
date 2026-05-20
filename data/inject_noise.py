import random
from pathlib import Path

import pandas as pd

from common.utils import normalize_phone


NICKNAMES = {
    "william": "bill",
    "robert": "bob",
    "james": "jim",
    "elizabeth": "liz",
    "katherine": "kate",
    "margaret": "maggie",
    "michael": "mike",
}


def _swap_chars(value: str) -> str:
    if not value or len(value) < 2:
        return value
    idx = random.randint(0, len(value) - 2)
    chars = list(value)
    chars[idx], chars[idx + 1] = chars[idx + 1], chars[idx]
    return "".join(chars)


def _abbreviate_address(value: str) -> str:
    return (
        value.replace("Street", "St")
        .replace("Avenue", "Ave")
        .replace("Road", "Rd")
        .replace("Apartment", "Apt")
    )


def apply_noise(record: dict) -> dict:
    noisy = dict(record)
    if random.random() < 0.25:
        noisy["first_name"] = _swap_chars(noisy["first_name"])
    if random.random() < 0.15:
        noisy["first_name"], noisy["last_name"] = noisy["last_name"], noisy["first_name"]
    if random.random() < 0.2:
        key = noisy["first_name"].lower()
        noisy["first_name"] = NICKNAMES.get(key, noisy["first_name"])
    if random.random() < 0.2:
        dob = pd.to_datetime(noisy["dob"])
        noisy["dob"] = (dob + pd.Timedelta(days=random.choice([-1, 1]))).strftime("%m/%d/%Y")
    if random.random() < 0.25:
        noisy["address"] = _abbreviate_address(noisy["address"])
    if random.random() < 0.15:
        noisy["zip"] = str(noisy["zip"])[:3]
    if random.random() < 0.15:
        noisy["phone"] = normalize_phone(noisy["phone"])
    if random.random() < 0.15:
        missing_fields = random.sample(
            ["address", "phone", "ssn_last4", "zip", "dob"],
            k=random.randint(1, 3),
        )
        for field in missing_fields:
            noisy[field] = None
    return noisy


def create_noisy_views(base_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    records_a = []
    records_b = []
    matches = []

    for row in base_df.to_dict(orient="records"):
        record_a = dict(row)
        record_a["record_id"] = f"A-{row['patient_id']}"
        records_a.append(record_a)

        copies = random.randint(1, 2)
        for copy_idx in range(copies):
            noisy = apply_noise(row)
            noisy["record_id"] = f"B-{row['patient_id']}-{copy_idx}"
            records_b.append(noisy)
            matches.append({"record_a_id": record_a["record_id"], "record_b_id": noisy["record_id"]})

    distractors = base_df.sample(frac=0.2, random_state=42).to_dict(orient="records")
    for idx, row in enumerate(distractors):
        noisy = apply_noise(row)
        noisy["record_id"] = f"B-distractor-{idx:05d}"
        records_b.append(noisy)

    return pd.DataFrame(records_a), pd.DataFrame(records_b), pd.DataFrame(matches)


def main():
    output_dir = Path("artifacts/generated")
    base_path = output_dir / "base_records.csv"
    if not base_path.exists():
        raise FileNotFoundError("Run data/generate.py first.")

    base_df = pd.read_csv(base_path)
    records_a, records_b, matches = create_noisy_views(base_df)
    records_a.to_csv(output_dir / "records_A.csv", index=False)
    records_b.to_csv(output_dir / "records_B.csv", index=False)
    matches.to_csv(output_dir / "matches.csv", index=False)
    print(f"Wrote {len(records_a)} A-side records, {len(records_b)} B-side records, {len(matches)} matches")


if __name__ == "__main__":
    main()
