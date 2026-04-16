"""
Metric catalog — loads the quantitative + qualitative metric list from the
Ashland Hill Credit Scoring Methodology workbook.

Each metric becomes a feature in the ML model. Weights come directly from the
Excel "Weight (0-10)" column and seed the rule-based score.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)

SPECS_XLSX = Path(__file__).resolve().parents[2] / "specs" / "AH - Credit Scoring_Rating Methodology.xlsx"
CACHE_JSON = Path(__file__).resolve().parents[2] / "models" / "metric_catalog.json"

COLLATERAL_TYPES = ("pre_sales", "gap_unsold", "tax_credit")
_SHEET_NAMES = {"pre_sales": "Pre-Sales", "gap_unsold": "GapUnsold", "tax_credit": "Tax Credit"}


@dataclass
class Metric:
    key: str                # machine-safe identifier (feat_{collateral}_{idx})
    collateral: str         # pre_sales | gap_unsold | tax_credit
    metric: str             # human readable question
    category: str
    type: str               # Quantitative | Qualitative
    weight: float           # 0-10 from Excel
    row: int                # source row for traceability


def _slug(idx: int, collateral: str) -> str:
    return f"{collateral}_m{idx:02d}"


def _load_from_excel() -> Dict[str, List[Metric]]:
    import openpyxl
    wb = openpyxl.load_workbook(SPECS_XLSX, data_only=True)
    out: Dict[str, List[Metric]] = {}
    for coll_key, sheet in _SHEET_NAMES.items():
        ws = wb[sheet]
        metrics: List[Metric] = []
        idx = 0
        for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
            metric_text = row[1] if len(row) > 1 else None
            if not metric_text or "Valuation" in str(metric_text):
                continue
            type_ = row[4] if len(row) > 4 else None
            weight = row[5] if len(row) > 5 else None
            category = row[6] if len(row) > 6 else None
            if not isinstance(weight, (int, float)) or weight <= 0:
                continue
            metrics.append(Metric(
                key=_slug(idx, coll_key),
                collateral=coll_key,
                metric=str(metric_text).strip(),
                category=str(category or "Unknown").strip(),
                type=str(type_ or "Quantitative").strip(),
                weight=float(weight),
                row=row_idx,
            ))
            idx += 1
        out[coll_key] = metrics
        logger.info("Loaded %d metrics for %s", len(metrics), coll_key)
    return out


def _save_cache(data: Dict[str, List[Metric]]):
    CACHE_JSON.parent.mkdir(parents=True, exist_ok=True)
    serialisable = {k: [asdict(m) for m in v] for k, v in data.items()}
    CACHE_JSON.write_text(json.dumps(serialisable, indent=2))


def _load_cache() -> Dict[str, List[Metric]] | None:
    if not CACHE_JSON.exists():
        return None
    raw = json.loads(CACHE_JSON.read_text())
    return {k: [Metric(**m) for m in v] for k, v in raw.items()}


def load_metrics(refresh: bool = False) -> Dict[str, List[Metric]]:
    """Return metric catalog keyed by collateral type. Caches to JSON."""
    if not refresh:
        cached = _load_cache()
        if cached is not None:
            return cached
    data = _load_from_excel()
    _save_cache(data)
    return data


# --- Rating bands (Option 2 from the workbook) -----------------------------

_BANDS = [
    (0, 20, "CCC"),
    (20, 40, "BB"),
    (40, 60, "BBB"),
    (60, 80, "A"),
    (80, 101, "AA"),
]


def rating_band(score: float) -> str:
    """Map 0-100 score to a letter rating. Sub-notch (+/-) via decile."""
    score = max(0.0, min(100.0, float(score)))
    for lo, hi, label in _BANDS:
        if lo <= score < hi:
            # Sub-notch: lower third -> "-", middle -> "", upper third -> "+"
            span = hi - lo
            pos = (score - lo) / span
            if pos < 0.33:
                suffix = "-"
            elif pos < 0.66:
                suffix = ""
            else:
                suffix = "+"
            if label == "CCC":
                return f"{label}{suffix}" if suffix else label
            return f"{label}{suffix}" if suffix else label
    return "AA+"
