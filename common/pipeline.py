from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from blocking.block import build_candidate_pairs
from common.models import CandidatePair, MatchRun, Patient
from features.engineer import build_features
from llm.resolver import resolve_ambiguous_pairs
from model.evaluate import calculate_metrics, load_model_artifact
from model.train import bootstrap_training_if_needed


def create_match_run(db: Session) -> MatchRun:
    records_a = db.execute(select(Patient).where(Patient.source == "A")).scalars().all()
    records_b = db.execute(select(Patient).where(Patient.source == "B")).scalars().all()
    run = MatchRun(
        status="queued",
        total_a_records=len(records_a),
        total_b_records=len(records_b),
        started_at=datetime.utcnow(),
        metrics_payload={"stage": "queued", "message": "Waiting for a worker to start the pipeline."},
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def run_matching_pipeline(db: Session, run_id: str, top_k: int = 10) -> MatchRun:
    run = db.get(MatchRun, run_id)
    if run is None:
        raise ValueError(f"Run {run_id} not found.")

    run.status = "running"
    run.started_at = datetime.utcnow()
    run.metrics_payload = {"stage": "bootstrap", "message": "Preparing model artifacts."}
    db.commit()

    records_a = db.execute(select(Patient).where(Patient.source == "A")).scalars().all()
    records_b = db.execute(select(Patient).where(Patient.source == "B")).scalars().all()

    bootstrap_training_if_needed()
    model_bundle = load_model_artifact()
    run.metrics_payload = {"stage": "blocking", "message": "Generating candidate pairs."}
    db.commit()

    candidate_df = build_candidate_pairs(records_a, records_b, top_k=top_k)
    run.candidate_pairs = int(len(candidate_df))
    run.metrics_payload = {
        "stage": "feature_engineering",
        "message": "Computing similarity features.",
        "candidate_pairs": int(len(candidate_df)),
    }
    db.commit()
    feature_df = build_features(candidate_df, records_a, records_b)

    if feature_df.empty:
        run.status = "completed"
        run.candidate_pairs = 0
        run.metrics_payload = {"stage": "completed", "message": "No candidate pairs generated."}
        run.finished_at = datetime.utcnow()
        db.commit()
        return run

    feature_names = model_bundle["feature_names"]
    ml_scores = model_bundle["model"].predict_proba(feature_df[feature_names])[:, 1]
    feature_df["ml_score"] = ml_scores
    run.metrics_payload = {
        "stage": "resolution",
        "message": "Applying ML thresholds and resolving ambiguous pairs.",
        "candidate_pairs": int(len(feature_df)),
    }
    db.commit()

    ambiguous_rows = feature_df[(feature_df["ml_score"] > 0.25) & (feature_df["ml_score"] < 0.75)].copy()
    llm_results = resolve_ambiguous_pairs(ambiguous_rows)
    llm_lookup = {row["pair_key"]: row for row in llm_results}

    patient_lookup = {patient.id: patient for patient in [*records_a, *records_b]}
    truth_lookup = _ground_truth_lookup(patient_lookup)

    for idx, row in enumerate(feature_df.to_dict(orient="records"), start=1):
        pair_key = f'{row["record_a_id"]}:{row["record_b_id"]}'
        llm_row = llm_lookup.get(pair_key)
        decision_source = "ml"
        llm_score = None
        explanation = None

        if row["ml_score"] >= 0.75:
            final_match = True
        elif row["ml_score"] <= 0.25:
            final_match = False
        else:
            decision_source = "llm"
            llm_score = llm_row["confidence"] if llm_row else row["ml_score"]
            final_match = llm_row["match"] if llm_row else row["ml_score"] >= 0.5
            explanation = llm_row["reasoning"] if llm_row else "Fallback heuristic used."

        pair = CandidatePair(
            run_id=run.id,
            patient_a_id=row["record_a_id"],
            patient_b_id=row["record_b_id"],
            embedding_score=row["embedding_score"],
            features_payload={name: row[name] for name in feature_names},
            ml_score=float(row["ml_score"]),
            llm_score=float(llm_score) if llm_score is not None else None,
            final_match=bool(final_match),
            decision_source=decision_source,
            explanation=explanation,
            ground_truth=truth_lookup.get(pair_key),
        )
        db.add(pair)
        if idx % 500 == 0:
            db.flush()

    db.commit()

    persisted_pairs = db.execute(select(CandidatePair).where(CandidatePair.run_id == run.id)).scalars().all()
    metrics = calculate_metrics(persisted_pairs)
    run.status = "completed"
    run.candidate_pairs = len(persisted_pairs)
    run.auto_matches = sum(1 for pair in persisted_pairs if pair.decision_source == "ml" and pair.final_match)
    run.auto_rejects = sum(1 for pair in persisted_pairs if pair.decision_source == "ml" and not pair.final_match)
    run.llm_resolved = sum(1 for pair in persisted_pairs if pair.decision_source == "llm")
    run.metrics_payload = {"stage": "completed", **metrics}
    run.finished_at = datetime.utcnow()
    db.commit()
    db.refresh(run)
    return run


def fail_match_run(db: Session, run_id: str, message: str) -> None:
    run = db.get(MatchRun, run_id)
    if run is None:
        return
    run.status = "failed"
    run.finished_at = datetime.utcnow()
    run.metrics_payload = {"stage": "failed", "message": message}
    db.commit()


def _ground_truth_lookup(patient_lookup: dict[str, Patient]) -> dict[str, bool]:
    path = Path("artifacts/generated/matches.csv")
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    a_by_external = {
        patient.external_id: patient.id
        for patient in patient_lookup.values()
        if patient.source == "A"
    }
    b_by_external = {
        patient.external_id: patient.id
        for patient in patient_lookup.values()
        if patient.source == "B"
    }
    truth = {}
    for row in df.itertuples():
        a_id = a_by_external.get(row.record_a_id)
        b_id = b_by_external.get(row.record_b_id)
        if a_id and b_id:
            truth[f"{a_id}:{b_id}"] = True
    return truth
