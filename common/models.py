import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from common.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source: Mapped[str] = mapped_column(String(1), index=True)
    external_id: Mapped[str] = mapped_column(String(64), index=True)
    first_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(1), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    city: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    zip: Mapped[str | None] = mapped_column(String(10), nullable=True)
    ssn_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    record_hash: Mapped[str] = mapped_column(String(64), index=True)
    embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MatchRun(Base):
    __tablename__ = "match_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    total_a_records: Mapped[int] = mapped_column(Integer, default=0)
    total_b_records: Mapped[int] = mapped_column(Integer, default=0)
    candidate_pairs: Mapped[int] = mapped_column(Integer, default=0)
    auto_matches: Mapped[int] = mapped_column(Integer, default=0)
    auto_rejects: Mapped[int] = mapped_column(Integer, default=0)
    llm_resolved: Mapped[int] = mapped_column(Integer, default=0)
    metrics_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    pairs: Mapped[list["CandidatePair"]] = relationship(back_populates="run")


class CandidatePair(Base):
    __tablename__ = "candidate_pairs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id: Mapped[str] = mapped_column(ForeignKey("match_runs.id"), index=True)
    patient_a_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    patient_b_id: Mapped[str] = mapped_column(ForeignKey("patients.id"), index=True)
    embedding_score: Mapped[float] = mapped_column(Float, default=0.0)
    features_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    ml_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    llm_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_match: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    decision_source: Mapped[str | None] = mapped_column(String(16), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    ground_truth: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    run: Mapped["MatchRun"] = relationship(back_populates="pairs")


class GroundTruthMatch(Base):
    __tablename__ = "ground_truth_matches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    record_a_external_id: Mapped[str] = mapped_column(String(64), index=True)
    record_b_external_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
