import os
import tempfile
import unittest

import pandas as pd

os.environ["DATABASE_URL"] = "sqlite:///artifacts/test_ingestion.db"

from ingestion.ingest import ingest_ground_truth_csv, normalize_dataframe


class IngestionMappingTests(unittest.TestCase):
    def test_maps_alternate_headers_into_expected_fields(self):
        df = pd.DataFrame(
            [
                {
                    "member_id": "X-001",
                    "patient_name": "Jane Doe",
                    "birth_date": "1988-01-05",
                    "sex": "Female",
                    "address1": "123 Main Street",
                    "address2": "Apt 4B",
                    "town": "Detroit",
                    "province": "MI",
                    "postal_code": "48201",
                    "telephone": "(313) 555-1212",
                    "social_security_number": "123-45-6789",
                }
            ]
        )

        normalized, metadata = normalize_dataframe(df)
        row = normalized.iloc[0]

        self.assertEqual(row["record_id"], "X-001")
        self.assertEqual(row["first_name"], "jane")
        self.assertEqual(row["last_name"], "doe")
        self.assertEqual(row["gender"], "F")
        self.assertEqual(row["city"], "detroit")
        self.assertEqual(row["state"], "MI")
        self.assertEqual(row["zip"], "48201")
        self.assertEqual(row["phone"], "3135551212")
        self.assertEqual(row["ssn_last4"], "6789")
        self.assertIn("member_id", metadata["mapped_columns"]["record_id"])

    def test_generates_record_ids_when_missing(self):
        df = pd.DataFrame([{"name": "Only Name", "date_of_birth": "1999-01-01"}])
        normalized, metadata = normalize_dataframe(df)

        self.assertTrue(str(normalized.iloc[0]["record_id"]).startswith("generated-"))
        self.assertIn("Generated record IDs were assigned.", " ".join(metadata["warnings"]))

    def test_ingests_ground_truth_mapping(self):
        df = pd.DataFrame(
            [
                {"record_a_id": "A-001", "record_b_id": "B-001"},
                {"record_a_id": "A-002", "record_b_id": "B-002"},
            ]
        )
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as handle:
            df.to_csv(handle.name, index=False)
            result = ingest_ground_truth_csv(handle.name)

        self.assertEqual(result["records_ingested"], 2)
        self.assertEqual(result["schema"]["mapped_columns"]["record_a_id"], "record_a_id")
        self.assertEqual(result["schema"]["mapped_columns"]["record_b_id"], "record_b_id")


if __name__ == "__main__":
    unittest.main()
