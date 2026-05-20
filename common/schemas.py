from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class MatchRunRequest(BaseModel):
    top_k: int = 10


class MatchRunStatusResponse(BaseModel):
    run_id: str
    status: str
    total_a_records: int
    total_b_records: int
    candidate_pairs: int
    auto_matches: int
    auto_rejects: int
    llm_resolved: int
    metrics_payload: dict[str, Any] | None


class PairDetailResponse(BaseModel):
    id: str
    patient_a_id: str
    patient_b_id: str
    ml_score: float | None
    llm_score: float | None
    final_match: bool | None
    decision_source: str | None
    explanation: str | None
    features_payload: dict[str, Any]
    ground_truth: bool | None

    model_config = ConfigDict(from_attributes=True)


class MetricsResponse(BaseModel):
    run_id: str
    status: str
    total_a_records: int | None = None
    total_b_records: int | None = None
    metrics_payload: dict[str, Any] | None
    candidate_pairs: int
    auto_matches: int
    auto_rejects: int
    llm_resolved: int

    model_config = ConfigDict(from_attributes=True)


class PatientSummary(BaseModel):
    id: str
    external_id: str
    first_name: str | None
    last_name: str | None
    dob: date | None
    gender: str | None
    address: str | None
    city: str | None
    state: str | None
    zip: str | None


class MatchResultResponse(BaseModel):
    id: str
    patient_a_id: str
    patient_b_id: str
    patient_a: PatientSummary
    patient_b: PatientSummary
    ml_score: float | None
    llm_score: float | None
    final_match: bool | None
    decision_source: str | None
    explanation: str | None
    ground_truth: bool | None


class PatientResponse(BaseModel):
    id: str
    source: str
    external_id: str
    first_name: str | None
    last_name: str | None
    dob: date | None
    gender: str | None
    address: str | None
    city: str | None
    state: str | None
    zip: str | None
    ssn_last4: str | None
    phone: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
