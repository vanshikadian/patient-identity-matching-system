import json
import pickle
from pathlib import Path

from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score


def load_model_artifact():
    with Path("artifacts/models/xgb_model.pkl").open("rb") as handle:
        return pickle.load(handle)


def calculate_metrics(candidate_pairs) -> dict:
    truth = [pair.ground_truth for pair in candidate_pairs if pair.ground_truth is not None]
    hybrid_pred = [pair.final_match for pair in candidate_pairs if pair.ground_truth is not None]
    if not truth:
        return {
            "message": "Ground truth unavailable for the active run.",
        }

    baseline_pred = [_baseline_prediction(pair) for pair in candidate_pairs if pair.ground_truth is not None]
    ml_pred = [_ml_prediction(pair) for pair in candidate_pairs if pair.ground_truth is not None]
    precision = precision_score(truth, hybrid_pred, zero_division=0)
    recall = recall_score(truth, hybrid_pred, zero_division=0)
    f1 = f1_score(truth, hybrid_pred, zero_division=0)
    conf = confusion_matrix(truth, hybrid_pred).tolist()
    metrics = {
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "roc_auc": round(float(roc_auc_score(truth, hybrid_pred)), 4) if len(set(truth)) > 1 else None,
        "confusion_matrix": conf,
        "baseline_accuracy": round(float(accuracy_score(truth, baseline_pred)), 4),
        "ml_only_accuracy": round(float(accuracy_score(truth, ml_pred)), 4),
        "hybrid_accuracy": round(float(accuracy_score(truth, hybrid_pred)), 4),
        "evaluated_pairs": len(truth),
        "positive_pairs": int(sum(truth)),
    }
    Path("artifacts/models").mkdir(parents=True, exist_ok=True)
    Path("artifacts/models/eval_report.json").write_text(json.dumps(metrics, indent=2))
    return metrics


def _baseline_prediction(pair) -> bool:
    features = pair.features_payload or {}
    return bool(
        features.get("first_name_similarity", 0) >= 0.98
        and features.get("last_name_similarity", 0) >= 0.98
        and features.get("dob_exact_match", 0) == 1
    )


def _ml_prediction(pair) -> bool:
    score = pair.ml_score or 0.0
    return bool(score >= 0.5)


def evaluate_saved_model():
    from features.engineer import FEATURE_COLUMNS

    bundle = load_model_artifact()
    test_df = bundle["test_frame"]
    predictions = bundle["model"].predict(test_df[FEATURE_COLUMNS])
    truth = test_df["label"]
    metrics = {
        "precision": float(precision_score(truth, predictions, zero_division=0)),
        "recall": float(recall_score(truth, predictions, zero_division=0)),
        "f1": float(f1_score(truth, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(truth, predictions)),
        "confusion_matrix": confusion_matrix(truth, predictions).tolist(),
    }
    Path("artifacts/models/eval_report.json").write_text(json.dumps(metrics, indent=2))
    return metrics


if __name__ == "__main__":
    print(json.dumps(evaluate_saved_model(), indent=2))
