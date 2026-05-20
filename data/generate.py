from pathlib import Path

import pandas as pd
from faker import Faker

from common.utils import random_choice_or_none


fake = Faker()


def generate_base_records(num_records: int = 10000) -> pd.DataFrame:
    rows = []
    genders = ["F", "M"]
    for idx in range(num_records):
        profile = fake.simple_profile()
        address = fake.street_address()
        rows.append(
            {
                "patient_id": f"base-{idx:05d}",
                "first_name": profile["name"].split()[0],
                "last_name": profile["name"].split()[-1],
                "dob": profile["birthdate"].isoformat(),
                "gender": random_choice_or_none(genders) or "F",
                "address": address,
                "city": fake.city(),
                "state": fake.state_abbr(),
                "zip": fake.postcode()[:5],
                "ssn_last4": fake.ssn()[-4:],
                "phone": fake.phone_number(),
            }
        )
    return pd.DataFrame(rows)


def main():
    output_dir = Path("artifacts/generated")
    output_dir.mkdir(parents=True, exist_ok=True)
    df = generate_base_records()
    df.to_csv(output_dir / "base_records.csv", index=False)
    print(f"Wrote {len(df)} base records to {output_dir / 'base_records.csv'}")


if __name__ == "__main__":
    main()
