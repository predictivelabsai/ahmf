"""
Credit Scoring Module — Monika

Non-chat ML tab that scores counterparty / collateral risk using trained
Random Forest + Logistic Regression models. Visualises feature importance
and per-deal contributions with Plotly.

Routes:
  GET  /module/scoring                     - landing page (collateral picker)
  GET  /module/scoring/{collateral}        - scoring form for a type
  POST /module/scoring/{collateral}/score  - run inference, render result
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fasthtml.common import *

from utils.scoring import COLLATERAL_TYPES, load_bundle, score_counterparty
from utils.scoring.catalog import load_metrics

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

_COLLATERAL_LABELS = {
    "pre_sales": "Pre-Sales",
    "gap_unsold": "Gap / Unsold",
    "tax_credit": "Tax Credit",
}
_COLLATERAL_BLURB = {
    "pre_sales": "Minimum-guarantee contracts with foreign distributors. Scores distributor performance, concentration, and jurisdiction risk.",
    "gap_unsold": "Projected sales value of unsold territories. Scores sales-agent accuracy and territory volatility.",
    "tax_credit": "Government rebates and transferable credits. Scores jurisdictional stability, auditor performance, and FX/execution risk.",
}


def _rating_color(rating: str) -> str:
    letters = rating.rstrip("+-")
    return {
        "AAA": "#16a34a", "AA": "#16a34a", "A": "#22c55e",
        "BBB": "#3b82f6", "BB": "#f59e0b",
        "B": "#f97316", "CCC": "#dc2626",
    }.get(letters, "#64748b")


def _status_for_score(score: float) -> str:
    if score >= 80: return "High credit quality"
    if score >= 60: return "Investment grade"
    if score >= 40: return "Speculative grade"
    if score >= 20: return "Substantial risk"
    return "Near default"


def _models_ready(collateral: str) -> bool:
    return (MODELS_DIR / collateral / "rf.joblib").exists()


# ---------------------------------------------------------------------------
# Plotly helpers - produce JSON blobs + render div + init script
# ---------------------------------------------------------------------------

def _plotly_div(div_id: str, fig_json: str, height: int = 320) -> "Div":
    return Div(
        Div(id=div_id, style=f"width:100%;height:{height}px;"),
        Script(NotStr(f"""
            (function(){{
                var data = {fig_json};
                Plotly.newPlot('{div_id}', data.data, data.layout, {{responsive:true, displayModeBar:false}});
            }})();
        """)),
    )


def _feature_importance_fig(bundle, top: int = 15) -> str:
    feats = bundle.features
    imp = bundle.rf_importance
    order = imp.argsort()[::-1][:top]
    labels = [f"{feats[i].category[:18]} — {feats[i].metric[:55]}…" if len(feats[i].metric) > 55 else f"{feats[i].category[:18]} — {feats[i].metric}" for i in order][::-1]
    values = [float(imp[i]) for i in order][::-1]

    fig = {
        "data": [{
            "type": "bar",
            "orientation": "h",
            "x": values,
            "y": labels,
            "marker": {"color": "#0066cc"},
            "hovertemplate": "%{y}<br>importance: %{x:.3f}<extra></extra>",
        }],
        "layout": {
            "margin": {"l": 320, "r": 20, "t": 10, "b": 40},
            "xaxis": {"title": "Random Forest feature importance"},
            "yaxis": {"tickfont": {"size": 10}},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "#f8fafc",
            "height": 380,
        },
    }
    return json.dumps(fig)


def _contribution_fig(result: dict, top: int = 12) -> str:
    contribs = result["top_contributions"][:top][::-1]
    labels = [c["metric"][:55] + ("…" if len(c["metric"]) > 55 else "") for c in contribs]
    values = [c["logit_contribution"] for c in contribs]
    colors = ["#dc2626" if v > 0 else "#16a34a" for v in values]

    fig = {
        "data": [{
            "type": "bar",
            "orientation": "h",
            "x": values,
            "y": labels,
            "marker": {"color": colors},
            "hovertemplate": "%{y}<br>push: %{x:+.3f}<extra></extra>",
        }],
        "layout": {
            "margin": {"l": 320, "r": 20, "t": 10, "b": 40},
            "xaxis": {"title": "Logit contribution (positive = toward default, negative = toward performance)"},
            "yaxis": {"tickfont": {"size": 10}},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "#f8fafc",
            "height": 340,
        },
    }
    return json.dumps(fig)


def _gauge_fig(score: float, rating: str) -> str:
    color = _rating_color(rating)
    fig = {
        "data": [{
            "type": "indicator",
            "mode": "gauge+number",
            "value": round(score, 1),
            "number": {"suffix": " / 100", "font": {"size": 28}},
            "gauge": {
                "axis": {"range": [0, 100], "tickvals": [0, 20, 40, 60, 80, 100]},
                "bar": {"color": color},
                "steps": [
                    {"range": [0, 20], "color": "#fee2e2"},
                    {"range": [20, 40], "color": "#fed7aa"},
                    {"range": [40, 60], "color": "#fde68a"},
                    {"range": [60, 80], "color": "#bbf7d0"},
                    {"range": [80, 100], "color": "#86efac"},
                ],
                "threshold": {"line": {"color": "#1e293b", "width": 3}, "value": score},
            },
        }],
        "layout": {
            "margin": {"l": 20, "r": 20, "t": 10, "b": 10},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "height": 220,
        },
    }
    return json.dumps(fig)


# ---------------------------------------------------------------------------
# Input form helpers
# ---------------------------------------------------------------------------

def _group_metrics_by_category(metrics):
    groups: dict[str, list] = {}
    for m in metrics:
        groups.setdefault(m.category, []).append(m)
    return groups


def _build_input_form(collateral: str, metrics) -> "Form":
    """Compact form grouping metrics by category - sliders 0-100."""
    groups = _group_metrics_by_category(metrics)
    blocks = []
    for category, items in groups.items():
        rows = []
        for m in items:
            rows.append(
                Div(
                    Div(
                        Span(m.metric, style="flex:1;font-size:0.78rem;color:#1e293b;"),
                        Span(f"w={m.weight:.0f}", style="font-size:0.7rem;color:#94a3b8;margin-left:0.4rem;"),
                        style="display:flex;align-items:center;margin-bottom:0.25rem;",
                    ),
                    Div(
                        Input(type="range", name=m.key, min="0", max="100", step="1",
                              value="60", cls="score-slider",
                              oninput=f"document.getElementById('val-{m.key}').textContent=this.value"),
                        Span("60", id=f"val-{m.key}",
                             style="display:inline-block;width:34px;text-align:right;font-variant-numeric:tabular-nums;color:#0066cc;font-weight:600;font-size:0.8rem;"),
                        style="display:flex;align-items:center;gap:0.5rem;",
                    ),
                    style="margin-bottom:0.75rem;padding:0.5rem 0.75rem;border-left:2px solid #e2e8f0;",
                )
            )
        blocks.append(
            Div(
                H3(category, style="font-size:0.9rem;margin:1rem 0 0.5rem;color:#475569;text-transform:uppercase;letter-spacing:0.05em;"),
                *rows,
                style="margin-bottom:1rem;",
            )
        )

    return Form(
        *blocks,
        Div(
            Button("Score counterparty", type="submit", cls="auth-btn"),
            Button("Reset to neutral", type="reset", cls="header-btn",
                   style="margin-left:0.5rem;",
                   onclick="setTimeout(function(){document.querySelectorAll('.score-slider').forEach(function(s){var d=document.getElementById('val-'+s.name);if(d)d.textContent=s.value;});},50);"),
            style="margin-top:1rem;position:sticky;bottom:0;background:#ffffff;padding:0.5rem 0;",
        ),
        hx_post=f"/module/scoring/{collateral}/score",
        hx_target="#scoring-result",
        hx_swap="innerHTML",
    )


# ---------------------------------------------------------------------------
# Page renderers
# ---------------------------------------------------------------------------

SCORING_CSS = """
.score-slider { flex:1; -webkit-appearance:none; appearance:none; height:4px; background:#e2e8f0; border-radius:2px; outline:none; }
.score-slider::-webkit-slider-thumb { -webkit-appearance:none; appearance:none; width:16px; height:16px; border-radius:50%; background:#0066cc; cursor:pointer; border:2px solid #ffffff; box-shadow:0 1px 3px rgba(0,0,0,0.2); }
.score-slider::-moz-range-thumb { width:16px; height:16px; border-radius:50%; background:#0066cc; cursor:pointer; border:2px solid #ffffff; }
.collateral-card { cursor:pointer; transition:all 0.2s; }
.collateral-card:hover { border-color:#0066cc; transform:translateY(-2px); box-shadow:0 4px 12px rgba(0,102,204,0.12); }
"""


def _landing_page():
    cards = []
    for coll in COLLATERAL_TYPES:
        ready = _models_ready(coll)
        status = ("✓ Model trained" if ready else "✗ Not trained - run `python -m utils.scoring.train`")
        status_color = "#16a34a" if ready else "#dc2626"
        cards.append(Div(
            H2(_COLLATERAL_LABELS[coll], style="font-size:1.05rem;margin-bottom:0.35rem;"),
            P(_COLLATERAL_BLURB[coll], style="font-size:0.8rem;color:#64748b;margin-bottom:0.5rem;"),
            Div(status, style=f"font-size:0.75rem;color:{status_color};font-weight:600;"),
            Div("Open →", style="margin-top:0.75rem;color:#0066cc;font-size:0.8rem;font-weight:600;"),
            cls="stat-card collateral-card",
            onclick=f"loadModule('/module/scoring/{coll}', 'Credit Scoring — {_COLLATERAL_LABELS[coll]}')",
        ))

    # Training summary if present
    summary_blob = None
    summary_path = MODELS_DIR / "training_summary.json"
    if summary_path.exists():
        try:
            summary_blob = json.loads(summary_path.read_text())
        except Exception:
            summary_blob = None

    summary_table = ""
    if summary_blob:
        rows = [Tr(
            Th("Collateral"), Th("Features"), Th("Default rate"),
            Th("RF acc"), Th("RF AUC"), Th("Logit acc"), Th("Logit AUC"),
        )]
        for coll, m in summary_blob.items():
            rows.append(Tr(
                Td(_COLLATERAL_LABELS.get(coll, coll)),
                Td(str(m["n_features"])),
                Td(f"{m['default_rate']*100:.0f}%"),
                Td(f"{m['rf']['accuracy']:.2f}"),
                Td(f"{m['rf']['auc']:.2f}"),
                Td(f"{m['logit']['accuracy']:.2f}"),
                Td(f"{m['logit']['auc']:.2f}"),
            ))
        summary_table = Div(
            H2("Trained models", style="margin-top:2rem;"),
            Table(*rows, style="width:100%;border-collapse:collapse;font-size:0.85rem;"),
            style="margin-top:1rem;",
        )

    return Div(
        Style(SCORING_CSS),
        H1("Credit Scoring"),
        P("Counterparty risk scoring driven by Random Forest + Logistic Regression trained on the Ashland Hill methodology rubric.",
          style="color:#64748b;margin-bottom:1.5rem;max-width:800px;"),
        Div(*cards, cls="stats-grid"),
        summary_table,
        P(A("Methodology →", href="/static/docs/counterparty_risk_methodology.md",
            style="color:#0066cc;font-size:0.85rem;"),
          style="margin-top:1.5rem;"),
        cls="module-content",
    )


def _collateral_page(collateral: str):
    if not _models_ready(collateral):
        return Div(
            Style(SCORING_CSS),
            H1(f"Credit Scoring — {_COLLATERAL_LABELS[collateral]}"),
            Div(
                P("Models for this collateral type have not been trained yet.",
                  style="color:#dc2626;margin-bottom:0.5rem;"),
                P("Run: ", Code("python -m utils.scoring.train"),
                  style="color:#64748b;"),
                style="padding:2rem;background:#fef2f2;border-radius:12px;border:1px solid #fecaca;",
            ),
            Button("Back", cls="auth-btn",
                   style="margin-top:1rem;",
                   onclick="loadModule('/module/scoring', 'Credit Scoring')"),
            cls="module-content",
        )

    bundle = load_bundle(collateral)
    metrics = bundle.features
    importance_fig = _feature_importance_fig(bundle)

    return Div(
        Style(SCORING_CSS),
        Div(
            H1(f"Credit Scoring — {_COLLATERAL_LABELS[collateral]}"),
            Button("← All collateral", cls="header-btn",
                   onclick="loadModule('/module/scoring', 'Credit Scoring')"),
            style="display:flex;justify-content:space-between;align-items:center;",
        ),
        P(_COLLATERAL_BLURB[collateral], style="color:#64748b;margin-bottom:1rem;max-width:800px;"),

        Div(
            Div(
                Div("Features", cls="stat-label"), Div(str(len(metrics)), cls="stat-value"),
                cls="stat-card"),
            Div(
                Div("RF AUC", cls="stat-label"),
                Div(f"{bundle.metrics['rf']['auc']:.2f}", cls="stat-value", style="color:#0066cc;"),
                cls="stat-card"),
            Div(
                Div("Logit AUC", cls="stat-label"),
                Div(f"{bundle.metrics['logit']['auc']:.2f}", cls="stat-value", style="color:#0066cc;"),
                cls="stat-card"),
            Div(
                Div("Default rate (train)", cls="stat-label"),
                Div(f"{bundle.metrics['default_rate']*100:.0f}%", cls="stat-value"),
                cls="stat-card"),
            cls="stats-grid",
        ),

        H2("Global feature importance"),
        P("Ranks the Random Forest's permutation importance across the rubric. "
          "Use this to see which metrics the model relies on most.",
          style="font-size:0.85rem;color:#64748b;margin-bottom:0.5rem;"),
        Div(
            _plotly_div("fi-chart", importance_fig),
            style="background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;padding:1rem;margin-bottom:1.5rem;",
        ),

        Div(
            Div(
                H2("Score a counterparty"),
                P("Move each slider to reflect the counterparty. Values are "
                  "already normalised to 0–100 (higher = better). "
                  "Default is 60 (neutral good).",
                  style="font-size:0.85rem;color:#64748b;margin-bottom:1rem;"),
                _build_input_form(collateral, metrics),
                style="padding-right:1rem;max-height:1200px;overflow-y:auto;",
            ),
            Div(
                H2("Result"),
                Div(
                    P("Fill in the form and click Score.",
                      style="color:#94a3b8;text-align:center;padding:2rem 0;"),
                    id="scoring-result",
                ),
                style="padding-left:1rem;border-left:1px solid #e2e8f0;",
            ),
            style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-top:1rem;",
        ),
        cls="module-content",
    )


def _result_panel(collateral: str, feature_values: dict[str, float]):
    bundle = load_bundle(collateral)
    result = score_counterparty(bundle, feature_values)
    rating = result["rating"]
    color = _rating_color(rating)

    gauge = _plotly_div(f"gauge-{collateral}", _gauge_fig(result["blended_score"], rating), height=220)
    contrib = _plotly_div(f"contrib-{collateral}", _contribution_fig(result), height=380)

    # Top-driver table
    driver_rows = [Tr(Th("Feature"), Th("Weight"), Th("Value"), Th("Logit push"), Th("RF importance"))]
    for c in result["top_contributions"][:8]:
        push = c["logit_contribution"]
        arrow = "↑ risk" if push > 0 else "↓ risk"
        arrow_color = "#dc2626" if push > 0 else "#16a34a"
        driver_rows.append(Tr(
            Td(c["metric"][:70] + ("…" if len(c["metric"]) > 70 else ""),
               style="font-size:0.75rem;"),
            Td(f"{c['weight']:.0f}", style="font-variant-numeric:tabular-nums;"),
            Td(f"{c['value']:.0f}", style="font-variant-numeric:tabular-nums;"),
            Td(Span(arrow, style=f"color:{arrow_color};font-size:0.75rem;"),
               f" {push:+.2f}",
               style="font-variant-numeric:tabular-nums;"),
            Td(f"{c['rf_importance']:.3f}", style="font-variant-numeric:tabular-nums;"),
        ))

    return Div(
        Div(
            Div(
                Div("Score", cls="stat-label"),
                Div(f"{result['blended_score']:.1f}", cls="stat-value", style=f"color:{color};"),
                cls="stat-card"),
            Div(
                Div("Rating", cls="stat-label"),
                Div(rating, cls="stat-value", style=f"color:{color};"),
                cls="stat-card"),
            Div(
                Div("Rule score", cls="stat-label"),
                Div(f"{result['rule_score']:.1f}", cls="stat-value"),
                cls="stat-card"),
            cls="stats-grid",
        ),
        Div(
            Div(f"{_status_for_score(result['blended_score'])}  •  "
                f"RF P(default) = {result['rf_proba']:.1%}  •  "
                f"Logit P(default) = {result['logit_proba']:.1%}",
                style="font-size:0.8rem;color:#475569;"),
            style="padding:0.75rem 1rem;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:1rem;",
        ),
        H3("Score gauge", style="font-size:0.9rem;margin:1rem 0 0.5rem;"),
        Div(gauge, style="background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;padding:0.5rem;"),

        H3("Top drivers for this counterparty",
           style="font-size:0.9rem;margin:1rem 0 0.5rem;"),
        P("Logit contributions show how each feature — at the value you entered — "
          "pushed the score. Red = toward default, green = toward performance.",
          style="font-size:0.78rem;color:#64748b;margin-bottom:0.5rem;"),
        Div(contrib, style="background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;padding:0.5rem;"),

        H3("Driver detail", style="font-size:0.9rem;margin:1rem 0 0.5rem;"),
        Table(*driver_rows,
              style="width:100%;border-collapse:collapse;font-size:0.8rem;"),
    )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_routes(rt):

    @rt("/module/scoring")
    def module_scoring(session):
        return _landing_page()

    @rt("/module/scoring/{collateral}")
    def collateral_page(collateral: str, session):
        if collateral not in COLLATERAL_TYPES:
            return Div(H1("Unknown collateral type"), cls="module-content")
        return _collateral_page(collateral)

    @rt("/module/scoring/{collateral}/score", methods=["POST"])
    async def collateral_score(collateral: str, session, request):
        if collateral not in COLLATERAL_TYPES:
            return Div(P("Unknown collateral type."), style="color:#dc2626;")
        form = await request.form()
        feature_values = {}
        for k, v in form.items():
            if k.startswith(f"{collateral}_m"):
                try:
                    feature_values[k] = float(v)
                except (TypeError, ValueError):
                    continue
        return _result_panel(collateral, feature_values)
