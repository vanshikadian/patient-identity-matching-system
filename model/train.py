import pickle
from pathlib import Path

import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier

from blocking.block import build_candidate_pairs
from common.config import get_settings
from data.generate import generate_base_records
from data.inject_noise import create_noisy_views
from features.engineer import FEATURE_COLUMNS, build_features
from ingestion.ingest import initialize_database
from common.utils import train_test_splits

try:
    from xgboost import XGBClassifier
except ImportError:  # pragma: no cover
    XGBClassifier = None


def bootstrap_training_if_needed():
    artifact_path = get_settings().models_dir / "xgb_model.pkl"
    if artifact_path.exists():
        return artifact_path

    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    initialize_database()

    base_df = generate_base_records(num_records=1200)
    records_a_df, records_b_df, matches_df = create_noisy_views(base_df)
    records_a = _rows_to_objects(records_a_df, "A")
    records_b = _rows_to_objects(records_b_df, "B")
    candidates = build_candidate_pairs(records_a, records_b, top_k=6)
    feature_df = build_features(candidates, records_a, records_b)
    truth = {(row.record_a_id, row.record_b_id): 1 for row in matches_df.itertuples()}
    feature_df["label"] = [
        truth.get((lookup_a.external_id, lookup_b.external_id), 0)
        for lookup_a, lookup_b in zip(
            [next(record for record in records_a if record.id == record_id) for record_id in feature_df["record_a_id"]],
            [next(record for record in records_b if record.id == record_id) for record_id in feature_df["record_b_id"]],
        )
    ]

    train_df, val_df, test_df = train_test_splits(feature_df)
    model = _fit_model(pd.concat([train_df, val_df], ignore_index=True))
    with artifact_path.open("wb") as handle:
        pickle.dump(
            {
                "model": model,
                "feature_names": FEATURE_COLUMNS,
                "test_frame": test_df,
            },
            handle,
        )
    return artifact_path


def _fit_model(df: pd.DataFrame):
    positives = max(int(df["label"].sum()), 1)
    negatives = max(len(df) - positives, 1)
    if XGBClassifier is not None:
        model = XGBClassifier(
            objective="binary:logistic",
            eval_metric="logloss",
            scale_pos_weight=negatives / positives,
            max_depth=4,
            learning_rate=0.1,
            n_estimators=120,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
        )
    else:
        # Vercel's Python environment is happier with pure sklearn than heavy native ML wheels.
        model = HistGradientBoostingClassifier(
            learning_rate=0.1,
            max_depth=4,
            max_iter=180,
            random_state=42,
        )
    model.fit(df[FEATURE_COLUMNS], df["label"])
    return model


def _rows_to_objects(df: pd.DataFrame, source: str):
    records = []
    for row in df.to_dict(orient="records"):
        record = type("TrainingRecord", (), {})()
        record.id = row["record_id"]
        record.external_id = row["record_id"]
        record.source = source
        record.first_name = str(row.get("first_name", "")).lower() if pd.notna(row.get("first_name")) else None
        record.last_name = str(row.get("last_name", "")).lower() if pd.notna(row.get("last_name")) else None
        record.dob = pd.to_datetime(row.get("dob"), errors="coerce")
        record.gender = row.get("gender")
        record.address = str(row.get("address", "")).lower() if pd.notna(row.get("address")) else None
        record.city = row.get("city")
        record.state = row.get("state")
        record.zip = str(row.get("zip")) if pd.notna(row.get("zip")) else None
        record.ssn_last4 = str(row.get("ssn_last4")) if pd.notna(row.get("ssn_last4")) else None
        record.phone = str(row.get("phone")) if pd.notna(row.get("phone")) else None
        record.embedding = None
        records.append(record)
    return records


def main():
    path = bootstrap_training_if_needed()
    print(f"Model artifact available at {path}")


if __name__ == "__main__":
    main()
