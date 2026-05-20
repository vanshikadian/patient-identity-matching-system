from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from api.deps import require_api_key
from common.database import get_db
from common.models import MatchRun
from common.schemas import MetricsResponse


router = APIRouter(prefix="", tags=["metrics"], dependencies=[Depends(require_api_key)])


@router.get("/metrics", response_model=MetricsResponse)
def metrics(db: Session = Depends(get_db)):
    run = db.execute(select(MatchRun).order_by(desc(MatchRun.started_at)).limit(1)).scalar_one_or_none()
    if run is None:
        return {
            "run_id": None,
            "status": "idle",
            "total_a_records": 0,
            "total_b_records": 0,
            "metrics_payload": {"stage": "idle", "message": "Upload two CSVs, then run matching."},
            "candidate_pairs": 0,
            "auto_matches": 0,
            "auto_rejects": 0,
            "llm_resolved": 0,
        }
    return {
        "run_id": run.id,
        "status": run.status,
        "total_a_records": run.total_a_records,
        "total_b_records": run.total_b_records,
        "metrics_payload": run.metrics_payload,
        "candidate_pairs": run.candidate_pairs,
        "auto_matches": run.auto_matches,
        "auto_rejects": run.auto_rejects,
        "llm_resolved": run.llm_resolved,
    }
