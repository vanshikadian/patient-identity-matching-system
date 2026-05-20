from collections import defaultdict

import jellyfish
import numpy as np
import pandas as pd

from common.config import get_settings
from common.utils import hashed_embedding

try:
    import faiss
except ImportError:  # pragma: no cover
    faiss = None

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover
    SentenceTransformer = None


def _embedding_for_record(record) -> list[float]:
    if getattr(record, "embedding", None):
        return record.embedding
    text = " ".join(
        filter(None, [getattr(record, "first_name", None), getattr(record, "last_name", None), str(getattr(record, "dob", "") or "")])
    )
    return hashed_embedding(text, dim=get_settings().embedding_dim)


def _load_model():
    if SentenceTransformer is None:
        return None
    try:
        return SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        return None


def build_candidate_pairs(records_a, records_b, top_k: int = 10) -> pd.DataFrame:
    if not records_a or not records_b:
        return pd.DataFrame(columns=["record_a_id", "record_b_id", "embedding_score"])

    model = _load_model()
    texts_a = [_record_text(record) for record in records_a]
    texts_b = [_record_text(record) for record in records_b]

    if model is not None:
        emb_a = model.encode(texts_a, normalize_embeddings=True)
        emb_b = model.encode(texts_b, normalize_embeddings=True)
    else:
        emb_a = np.array([_embedding_for_record(record) for record in records_a], dtype="float32")
        emb_b = np.array([_embedding_for_record(record) for record in records_b], dtype="float32")

    pairs = []
    if faiss is not None:
        index = faiss.IndexFlatIP(emb_b.shape[1])
        index.add(emb_b.astype("float32"))
        scores, indices = index.search(emb_a.astype("float32"), top_k)
        for a_idx, neighbors in enumerate(indices):
            for b_pos, b_idx in enumerate(neighbors):
                if b_idx < 0:
                    continue
                pairs.append(
                    {
                        "record_a_id": records_a[a_idx].id,
                        "record_b_id": records_b[b_idx].id,
                        "embedding_score": float(scores[a_idx][b_pos]),
                    }
                )
    else:
        similarity = emb_a @ emb_b.T
        for a_idx in range(similarity.shape[0]):
            top_indices = np.argsort(similarity[a_idx])[::-1][:top_k]
            for b_idx in top_indices:
                pairs.append(
                    {
                        "record_a_id": records_a[a_idx].id,
                        "record_b_id": records_b[b_idx].id,
                        "embedding_score": float(similarity[a_idx][b_idx]),
                    }
                )

    soundex_groups = defaultdict(list)
    for record in records_b:
        if record.last_name:
            soundex_groups[jellyfish.soundex(record.last_name)].append(record.id)

    seen = {(pair["record_a_id"], pair["record_b_id"]) for pair in pairs}
    for record in records_a:
        if not record.last_name:
            continue
        for b_id in soundex_groups.get(jellyfish.soundex(record.last_name), []):
            if (record.id, b_id) not in seen:
                pairs.append({"record_a_id": record.id, "record_b_id": b_id, "embedding_score": 0.0})
                seen.add((record.id, b_id))

    return pd.DataFrame(pairs).drop_duplicates(subset=["record_a_id", "record_b_id"]).reset_index(drop=True)


def _record_text(record) -> str:
    return " ".join(
        filter(None, [getattr(record, "first_name", None), getattr(record, "last_name", None), str(getattr(record, "dob", "") or "")])
    )
