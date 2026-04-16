"""
Train Random Forest + Logistic Regression per collateral type and persist
artefacts to models/<collateral>/.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from .catalog import COLLATERAL_TYPES, Metric
from .dataset import build_dataset

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"


def _metric_table(metrics: list[Metric]) -> list[dict]:
    return [asdict(m) for m in metrics]


def train_one(collateral: str, n_samples: int = 2000, seed: int = 42) -> dict:
    """Train both models for one collateral type; save artefacts; return metrics."""
    X, y, metrics = build_dataset(collateral, n_samples=n_samples, seed=seed)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=seed, stratify=y
    )

    # --- Random Forest (raw features) ---
    rf = RandomForestClassifier(
        n_estimators=200, max_depth=8, min_samples_leaf=5,
        random_state=seed, n_jobs=-1,
    )
    rf.fit(X_train, y_train)
    rf_pred = rf.predict(X_test)
    rf_proba = rf.predict_proba(X_test)[:, 1]
    perm = permutation_importance(rf, X_test, y_test, n_repeats=5, random_state=seed, n_jobs=-1)

    # --- Logistic Regression (scaled features) ---
    scaler = StandardScaler().fit(X_train)
    Xtr_s = scaler.transform(X_train)
    Xte_s = scaler.transform(X_test)
    logit = LogisticRegression(C=1.0, solver="lbfgs", max_iter=1000, random_state=seed)
    logit.fit(Xtr_s, y_train)
    lg_pred = logit.predict(Xte_s)
    lg_proba = logit.predict_proba(Xte_s)[:, 1]

    # Persist
    out_dir = MODELS_DIR / collateral
    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(rf, out_dir / "rf.joblib")
    joblib.dump(logit, out_dir / "logit.joblib")
    joblib.dump(scaler, out_dir / "scaler.joblib")

    # Store feature importances alongside metric metadata
    features_blob = {
        "features": _metric_table(metrics),
        "rf_importance": rf.feature_importances_.tolist(),
        "rf_permutation_mean": perm.importances_mean.tolist(),
        "rf_permutation_std": perm.importances_std.tolist(),
        "logit_coef": logit.coef_[0].tolist(),
        "logit_intercept": float(logit.intercept_[0]),
        "feature_means": scaler.mean_.tolist(),
        "feature_std": scaler.scale_.tolist(),
    }
    (out_dir / "features.json").write_text(json.dumps(features_blob, indent=2))

    metrics_blob = {
        "collateral": collateral,
        "n_samples": n_samples,
        "n_features": X.shape[1],
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
        "default_rate": float(y.mean()),
        "rf": {
            "accuracy": float(accuracy_score(y_test, rf_pred)),
            "auc": float(roc_auc_score(y_test, rf_proba)),
            "classification_report": classification_report(
                y_test, rf_pred, output_dict=True, zero_division=0
            ),
        },
        "logit": {
            "accuracy": float(accuracy_score(y_test, lg_pred)),
            "auc": float(roc_auc_score(y_test, lg_proba)),
            "classification_report": classification_report(
                y_test, lg_pred, output_dict=True, zero_division=0
            ),
        },
    }
    (out_dir / "metrics.json").write_text(json.dumps(metrics_blob, indent=2))
    logger.info(
        "Trained %s: RF acc=%.3f AUC=%.3f | Logit acc=%.3f AUC=%.3f",
        collateral,
        metrics_blob["rf"]["accuracy"], metrics_blob["rf"]["auc"],
        metrics_blob["logit"]["accuracy"], metrics_blob["logit"]["auc"],
    )
    return metrics_blob


def train_all(n_samples: int = 2000, seed: int = 42) -> dict:
    """Train models for every collateral type."""
    summary = {}
    for coll in COLLATERAL_TYPES:
        summary[coll] = train_one(coll, n_samples=n_samples, seed=seed)
    (MODELS_DIR / "training_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = train_all()
    for coll, m in result.items():
        print(f"{coll}: RF AUC={m['rf']['auc']:.3f}  Logit AUC={m['logit']['auc']:.3f}")
