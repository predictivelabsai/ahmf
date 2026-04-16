"""
Dataset generator for the credit-scoring models.

Each collateral type gets its own training matrix. We blend:

1. **Real-film features** — when TMDB / OMDB are reachable, we pull a handful
   of public films and use budget, revenue, vote_average, popularity, year to
   anchor realistic distributions (e.g. vote_average proxies for "performance
   track record", revenue-over-budget proxies for "sales accuracy").

2. **Synthetic metric rows** — we sample each metric on [0, 100] using a
   distribution that reflects its intent (efficiency ratios lognormal around
   100, coefficient-of-variation inversions beta-shaped, Bernoulli for
   qualitative flags). Low scores mean "bad" counterparty.

Label generation follows the rubric: `default = 1` when the weighted rule
score falls below a threshold plus Gaussian noise. This makes the ML models
learn an approximation of the Excel rubric while still exposing feature
importances.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from .catalog import Metric, load_metrics

logger = logging.getLogger(__name__)

_RNG = np.random.default_rng(20260101)
N_SAMPLES_DEFAULT = 2000


def _sample_metric_column(m: Metric, n: int, rng: np.random.Generator) -> np.ndarray:
    """Sample an n-length column for a single metric on the [0, 100] scale."""
    category = m.category.lower()
    metric_text = m.metric.lower()

    if m.type.startswith("Qual"):
        # Qualitative: mostly mid/high (60-90), a few outliers below
        return np.clip(rng.beta(5, 2, n) * 100, 0, 100)

    # Quantitative — shape depends on what the metric captures
    if "variance" in metric_text or "coefficient" in metric_text or "accuracy" in metric_text:
        # Variance / accuracy (higher = more stable)
        return np.clip(rng.beta(4, 3, n) * 100, 0, 100)
    if "time" in metric_text or "takes to" in metric_text or "delay" in metric_text:
        # Time-based efficiency ratio — centered around 70 with heavy left tail
        raw = rng.lognormal(mean=np.log(70), sigma=0.35, size=n)
        return np.clip(raw, 0, 100)
    if "how many times" in metric_text or "cancelation" in metric_text or "payment plan" in metric_text:
        # Incident counts - mostly high (few incidents), long left tail
        return np.clip(rng.beta(6, 2, n) * 100, 0, 100)
    if "average mg" in metric_text or "sales value" in metric_text or "qualifying spend" in metric_text:
        # Percentage vs portfolio - near normal around 60
        return np.clip(rng.normal(loc=62, scale=18, size=n), 0, 100)
    if "banking" in metric_text or "concentration" in metric_text:
        # Concentration risk - lower is better for score
        return np.clip(100 - rng.exponential(scale=20, size=n), 0, 100)
    # Default: broad beta
    return np.clip(rng.beta(3, 2, n) * 100, 0, 100)


def _rule_based_score(matrix: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Weighted mean across features -> 0-100 score per row."""
    return (matrix * weights).sum(axis=1) / weights.sum()


def _try_tmdb_anchor(rng: np.random.Generator, n: int) -> np.ndarray | None:
    """Return an n-length array of a 'performance anchor' feature seeded from
    real TMDB data if the API key is set; else None."""
    api_key = os.getenv("TMDB_API_KEY")
    if not api_key:
        return None
    try:
        import httpx
        rows = []
        # Pull two pages of popular films - ~40 titles
        for page in (1, 2):
            resp = httpx.get(
                "https://api.themoviedb.org/3/movie/popular",
                params={"api_key": api_key, "language": "en-US", "page": page},
                timeout=10,
            )
            resp.raise_for_status()
            rows.extend(resp.json().get("results", []))
        if not rows:
            return None
        votes = np.array([float(r.get("vote_average") or 0) for r in rows])
        # Normalise 0-10 -> 0-100 (vote_average is 0-10)
        anchor_pool = np.clip(votes * 10, 0, 100)
        # Expand to n samples with small jitter
        idx = rng.integers(0, len(anchor_pool), size=n)
        return np.clip(anchor_pool[idx] + rng.normal(0, 4, size=n), 0, 100)
    except Exception as e:
        logger.info("TMDB anchor unavailable: %s", e)
        return None


def build_dataset(
    collateral: str,
    n_samples: int = N_SAMPLES_DEFAULT,
    default_threshold: float | None = None,
    noise_sigma: float = 6.0,
    seed: int | None = None,
) -> Tuple[pd.DataFrame, pd.Series, List[Metric]]:
    """
    Generate a training dataset for the given collateral type.

    Returns
    -------
    X : DataFrame, columns = metric keys, values in [0, 100]
    y : Series of {0, 1} (1 = default)
    metrics : ordered list of Metric objects matching X columns
    """
    metrics = load_metrics()[collateral]
    if not metrics:
        raise ValueError(f"No metrics loaded for collateral={collateral}")

    rng = np.random.default_rng(seed) if seed is not None else _RNG
    n_feat = len(metrics)
    matrix = np.zeros((n_samples, n_feat), dtype=float)
    for j, m in enumerate(metrics):
        matrix[:, j] = _sample_metric_column(m, n_samples, rng)

    # Overlay a TMDB-seeded anchor on the first 'performance' metric (if any)
    anchor = _try_tmdb_anchor(rng, n_samples)
    if anchor is not None:
        for j, m in enumerate(metrics):
            if "track record" in m.category.lower() or "performance" in m.category.lower():
                # Blend 70% anchor, 30% original
                matrix[:, j] = 0.7 * anchor + 0.3 * matrix[:, j]
                break

    weights = np.array([m.weight for m in metrics])
    rule_score = _rule_based_score(matrix, weights)
    noisy = rule_score + rng.normal(0, noise_sigma, size=n_samples)
    # Auto-set threshold to the 35th percentile so ~35% of rows default -
    # gives the classifiers a meaningful minority class to learn.
    if default_threshold is None:
        default_threshold = float(np.percentile(noisy, 35))
    y = (noisy < default_threshold).astype(int)

    cols = [m.key for m in metrics]
    X = pd.DataFrame(matrix, columns=cols)
    return X, pd.Series(y, name="default"), metrics
