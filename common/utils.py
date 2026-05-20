import hashlib
import math
import random
import re
from datetime import datetime

import numpy as np
import pandas as pd


PUNCT_RE = re.compile(r"[^a-zA-Z0-9\s]")
SPACE_RE = re.compile(r"\s+")


def normalize_text(value: str | None) -> str | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text = str(value).strip().lower()
    text = PUNCT_RE.sub(" ", text)
    return SPACE_RE.sub(" ", text).strip() or None


def normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return digits or None


def normalize_zip(value: str | None) -> str | None:
    if not value:
        return None
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    return digits[:5] or None


def parse_date(value) -> pd.Timestamp | None:
    if value is None or value == "":
        return None
    parsed = pd.to_datetime(value, errors="coerce", dayfirst=False)
    if pd.isna(parsed):
        return None
    if parsed.year < 1900 or parsed.year > 2100:
        return None
    return parsed


def iso_date(value) -> str | None:
    parsed = parse_date(value)
    return parsed.strftime("%Y-%m-%d") if parsed is not None else None


def sha256_record(record: dict) -> str:
    serialized = "|".join("" if v is None else str(v) for v in record.values())
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def embedding_text(record: dict) -> str:
    parts = [
        record.get("first_name") or "",
        record.get("last_name") or "",
        iso_date(record.get("dob")) or "",
    ]
    return " ".join(part for part in parts if part).strip()


def hashed_embedding(text: str, dim: int = 384) -> list[float]:
    vector = np.zeros(dim, dtype=float)
    for token in text.split():
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        for idx, byte in enumerate(digest):
            position = (idx * 13 + byte) % dim
            vector[position] += 1.0 if byte % 2 == 0 else -1.0
    norm = np.linalg.norm(vector)
    if norm == 0:
        return vector.tolist()
    return (vector / norm).tolist()


def train_test_splits(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train = df.sample(frac=0.7, random_state=42)
    remaining = df.drop(train.index)
    val = remaining.sample(frac=0.5, random_state=42)
    test = remaining.drop(val.index)
    return train.reset_index(drop=True), val.reset_index(drop=True), test.reset_index(drop=True)


def random_choice_or_none(options: list[str], blank_probability: float = 0.0) -> str | None:
    if random.random() < blank_probability:
        return None
    return random.choice(options)


def utcnow_iso() -> str:
    return datetime.utcnow().isoformat()
