"""
Load trained models and score a single counterparty.

Produces an interpretable score with:
- rule_score: weighted-rubric 0-100 (no ML)
- rf_proba, logit_proba: default probabilities
- blended_score: 0-100 health score (higher = better)
- rating: letter band
- top_contributions: per-feature contribution to *this* counterparty's score
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import joblib
import numpy as np
import pandas as pd

from .catalog import Metric, rating_band

MODELS_DIR = Path(__file__).resolve().parents[2] / "models"


@dataclass
class Bundle:
    collateral: str
    rf: Any
    logit: Any
    scaler: Any
    features: List[Metric]
    rf_importance: np.ndarray
    rf_permutation: np.ndarray
    logit_coef: np.ndarray
    feature_means: np.ndarray
    feature_std: np.ndarray
    metrics: dict          # training metrics

    @property
    def feature_keys(self) -> List[str]:
        return [f.key for f in self.features]

    @property
    def weights(self) -> np.ndarray:
        return np.array([f.weight for f in self.features])


def load_bundle(collateral: str) -> Bundle:
    """Load a trained bundle for the given collateral type."""
    d = MODELS_DIR / collateral
    if not d.exists():
        raise FileNotFoundError(
            f"No trained models for {collateral}. Run `python -m utils.scoring.train` first."
        )
    feats_blob = json.loads((d / "features.json").read_text())
    metrics_blob = json.loads((d / "metrics.json").read_text())
    feats = [Metric(**m) for m in feats_blob["features"]]
    return Bundle(
        collateral=collateral,
        rf=joblib.load(d / "rf.joblib"),
        logit=joblib.load(d / "logit.joblib"),
        scaler=joblib.load(d / "scaler.joblib"),
        features=feats,
        rf_importance=np.array(feats_blob["rf_importance"]),
        rf_permutation=np.array(feats_blob["rf_permutation_mean"]),
        logit_coef=np.array(feats_blob["logit_coef"]),
        feature_means=np.array(feats_blob["feature_means"]),
        feature_std=np.array(feats_blob["feature_std"]),
        metrics=metrics_blob,
    )


def score_counterparty(
    bundle: Bundle,
    feature_values: Dict[str, float] | None = None,
) -> Dict[str, Any]:
    """
    Score a counterparty. Missing feature values default to 60 (neutral good).

    Returns a dict with:
      rule_score, rf_proba, logit_proba, blended_score, rating,
      top_contributions (list of {key, metric, category, weight, value,
      logit_contribution, rf_importance})
    """
    feature_values = feature_values or {}
    keys = bundle.feature_keys
    vals = np.array([float(feature_values.get(k, 60.0)) for k in keys])
    # Clamp
    vals = np.clip(vals, 0.0, 100.0)

    # Rule score
    rule_score = float((vals * bundle.weights).sum() / bundle.weights.sum())

    # RF default probability (tree models use raw features)
    X_row = pd.DataFrame([dict(zip(keys, vals))])
    rf_proba = float(bundle.rf.predict_proba(X_row)[0, 1])

    # Logit default probability (on scaled features)
    z = (vals - bundle.feature_means) / np.where(bundle.feature_std == 0, 1.0, bundle.feature_std)
    logit_proba = float(bundle.logit.predict_proba(z.reshape(1, -1))[0, 1])

    blended = float(np.clip(100.0 * (1.0 - 0.5 * rf_proba - 0.5 * logit_proba), 0.0, 100.0))
    rating = rating_band(blended)

    # Per-feature contribution for *this* counterparty
    # Logit: coef_j * z_j -> signed push on log-odds (positive = toward default)
    logit_push = bundle.logit_coef * z
    # RF: global permutation importance scaled by how far this value is from mean
    rf_push = bundle.rf_permutation * z

    contribs = []
    for i, m in enumerate(bundle.features):
        contribs.append({
            "key": m.key,
            "metric": m.metric,
            "category": m.category,
            "weight": m.weight,
            "value": float(vals[i]),
            "logit_contribution": float(logit_push[i]),
            "rf_importance": float(bundle.rf_importance[i]),
            "rf_permutation": float(bundle.rf_permutation[i]),
            "rf_local_push": float(rf_push[i]),
        })
    # Top by absolute logit contribution
    contribs.sort(key=lambda c: abs(c["logit_contribution"]), reverse=True)

    return {
        "collateral": bundle.collateral,
        "rule_score": rule_score,
        "rf_proba": rf_proba,
        "logit_proba": logit_proba,
        "blended_score": blended,
        "rating": rating,
        "feature_values": {k: float(v) for k, v in zip(keys, vals)},
        "top_contributions": contribs,
    }
