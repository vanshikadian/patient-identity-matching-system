from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from api.deps import require_api_key
from common.config import get_settings
from common.database import get_db
from common.models import Patient
from common.schemas import PatientResponse
from ingestion.ingest import ingest_csv, ingest_ground_truth_csv


router = APIRouter(prefix="/records", tags=["records"], dependencies=[Depends(require_api_key)])


@router.post("/upload")
async def upload_records(source: str = Query(..., pattern="^[AB]$"), file: UploadFile = File(...)):
    settings = get_settings()
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV uploads are supported.")
    destination = settings.uploads_dir / f"{source}_{file.filename}"
    destination.write_bytes(await file.read())
    result = ingest_csv(destination, source=source)
    return {
        "message": "Upload processed",
        "source": source,
        "records_ingested": result["records_ingested"],
        "schema": result["schema"],
    }


@router.post("/upload-ground-truth")
async def upload_ground_truth(file: UploadFile = File(...)):
    settings = get_settings()
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV uploads are supported.")
    destination = settings.uploads_dir / f"ground_truth_{file.filename}"
    destination.write_bytes(await file.read())
    try:
        result = ingest_ground_truth_csv(destination)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "message": "Ground truth uploaded",
        "records_ingested": result["records_ingested"],
        "schema": result["schema"],
    }


@router.get("/search", response_model=list[PatientResponse])
def search_records(
    q: str | None = Query(default=None),
    dob: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = select(Patient)
    if q:
        term = f"%{q.lower()}%"
        stmt = stmt.where(or_(Patient.first_name.ilike(term), Patient.last_name.ilike(term)))
    if dob:
        stmt = stmt.where(Patient.dob == dob)
    return db.execute(stmt.limit(25)).scalars().all()
