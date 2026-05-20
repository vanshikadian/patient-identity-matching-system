from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, aliased

from api.deps import require_api_key
from common.database import get_db
from common.models import CandidatePair, MatchRun, Patient
from common.pipeline import create_match_run
from common.run_manager import run_manager
from common.schemas import MatchResultResponse, MatchRunRequest, MatchRunStatusResponse, PairDetailResponse


router = APIRouter(prefix="/match", tags=["match"], dependencies=[Depends(require_api_key)])


@router.post("/run")
def run_match(request: MatchRunRequest, db: Session = Depends(get_db)):
    if run_manager.has_active_run():
        active_run_id = run_manager.active_run_id()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "A matching run is already in progress.", "run_id": active_run_id},
        )

    run = create_match_run(db)
    run_manager.enqueue(run.id, request.top_k)
    return {
        "run_id": run.id,
        "status": run.status,
        "candidate_pairs": run.candidate_pairs,
        "auto_matches": run.auto_matches,
        "auto_rejects": run.auto_rejects,
        "llm_resolved": run.llm_resolved,
        "metrics_payload": run.metrics_payload,
    }


@router.get("/runs/latest", response_model=MatchRunStatusResponse)
def latest_run_status(db: Session = Depends(get_db)):
    run = db.execute(select(MatchRun).order_by(desc(MatchRun.started_at)).limit(1)).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="No runs found.")
    return _serialize_run(run)


@router.get("/runs/{run_id}", response_model=MatchRunStatusResponse)
def run_status(run_id: str, db: Session = Depends(get_db)):
    run = db.get(MatchRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found.")
    return _serialize_run(run)


@router.get("/results", response_model=list[MatchResultResponse])
def results(
    confidence_band: str | None = Query(default=None),
    limit: int = Query(default=50, le=250),
    db: Session = Depends(get_db),
):
    latest_completed_run = db.execute(
        select(MatchRun).where(MatchRun.status == "completed").order_by(desc(MatchRun.started_at)).limit(1)
    ).scalar_one_or_none()
    latest_run = latest_completed_run or db.execute(
        select(MatchRun).order_by(desc(MatchRun.started_at)).limit(1)
    ).scalar_one_or_none()
    if latest_run is None:
        raise HTTPException(status_code=404, detail="No runs found.")

    patient_a = aliased(Patient)
    patient_b = aliased(Patient)
    stmt = (
        select(CandidatePair, patient_a, patient_b)
        .join(patient_a, CandidatePair.patient_a_id == patient_a.id)
        .join(patient_b, CandidatePair.patient_b_id == patient_b.id)
        .where(CandidatePair.run_id == latest_run.id)
        .order_by(desc(CandidatePair.ml_score))
    )
    if confidence_band == "high":
        stmt = stmt.where(CandidatePair.ml_score >= 0.75)
    elif confidence_band == "low":
        stmt = stmt.where(CandidatePair.ml_score <= 0.25)
    elif confidence_band == "mid":
        stmt = stmt.where(CandidatePair.ml_score > 0.25, CandidatePair.ml_score < 0.75)
    rows = db.execute(stmt.limit(limit)).all()
    return [
        {
            "id": pair.id,
            "patient_a_id": pair.patient_a_id,
            "patient_b_id": pair.patient_b_id,
            "patient_a": {
                "id": record_a.id,
                "external_id": record_a.external_id,
                "first_name": record_a.first_name,
                "last_name": record_a.last_name,
                "dob": record_a.dob,
                "gender": record_a.gender,
                "address": record_a.address,
                "city": record_a.city,
                "state": record_a.state,
                "zip": record_a.zip,
            },
            "patient_b": {
                "id": record_b.id,
                "external_id": record_b.external_id,
                "first_name": record_b.first_name,
                "last_name": record_b.last_name,
                "dob": record_b.dob,
                "gender": record_b.gender,
                "address": record_b.address,
                "city": record_b.city,
                "state": record_b.state,
                "zip": record_b.zip,
            },
            "ml_score": pair.ml_score,
            "llm_score": pair.llm_score,
            "final_match": pair.final_match,
            "decision_source": pair.decision_source,
            "explanation": pair.explanation,
            "ground_truth": pair.ground_truth,
        }
        for pair, record_a, record_b in rows
    ]


@router.get("/{pair_id}", response_model=PairDetailResponse)
def pair_detail(pair_id: str, db: Session = Depends(get_db)):
    pair = db.get(CandidatePair, pair_id)
    if pair is None:
        raise HTTPException(status_code=404, detail="Pair not found.")
    return pair


def _serialize_run(run: MatchRun) -> dict:
    return {
        "run_id": run.id,
        "status": run.status,
        "total_a_records": run.total_a_records,
        "total_b_records": run.total_b_records,
        "candidate_pairs": run.candidate_pairs,
        "auto_matches": run.auto_matches,
        "auto_rejects": run.auto_rejects,
        "llm_resolved": run.llm_resolved,
        "metrics_payload": run.metrics_payload,
    }
