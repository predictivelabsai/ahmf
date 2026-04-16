# Counterparty Risk Methodology

**Source document:** `specs/AH - Credit Scoring_Rating Methodology.xlsx` (v1, Ashland Hill)

This document captures the credit-scoring methodology Ashland Hill Media Finance uses to evaluate collateral underlying a film-finance loan, and describes how Monika operationalises it as an interpretable machine-learning model.

---

## 1. Scope: three collateral types

Ashland Hill loans are secured against three distinct collateral classes, each with its own scoring rubric:

| Collateral | What it is | What we assess |
|------------|-----------|----------------|
| **Pre-Sales** | Minimum-guarantee contracts with foreign distributors | Can the distributor perform and pay on time? |
| **Gap / Unsold** | Projected sales value of unsold territories | Will the sales agent actually hit those estimates? |
| **Tax Credit** | Government rebates / transferable credits | Will the authority and auditor deliver as modelled? |

Each type is scored on a 0–100 scale and mapped to a letter rating (AAA … D).

---

## 2. Rating bands

The workbook proposes three mapping options. The model adopts **Option 2** as the default — it has the widest band coverage and is closest to a standard S&P/Fitch distribution.

| Score | Rating (Option 2) | S&P / Fitch interpretation |
|-------|-------------------|----------------------------|
| 0–20 | CCC+ / CCC / CCC- | Substantial credit risk |
| 20–40 | BB+ / BB / BB- | Speculative |
| 40–60 | BBB+ / BBB / BBB- | Lower medium investment grade |
| 60–80 | A+ / A / A- | Upper medium investment grade |
| 80–100 | AA+ / AA / AA- | High credit quality |

Sub-notches (the `+` / `-` tier) are assigned by the decile within each band.

---

## 3. Metric inventory

The Excel defines **~75 quantitative and qualitative metrics** across the three collateral types. Each metric has a weight (0–10) and category. The full list is loaded directly from the workbook by `agents/tools/scoring_model.py::load_metrics()`.

### Pre-Sales — 38 metrics (selected)

Categories: *Performance & Track Record*, *Cross-Default*, *Collection Risk*, *Market Landscape*, *Stability of Jurisdiction*.

| Weight | Example metric |
|--------|----------------|
| 10 | Cross-default exposure — how many pre-sales contracts is Ashland banking for a given Distributor |
| 10 | Distributor history of DA cancellation (last 18 mo) |
| 9 | Distributor speed of balance payment at NOD (last 18 mo) |
| 9 | Payment-plan requests (last 18 mo) |
| 8 | Average MG size for budget range / genre / talent / producer |
| 7 | Historical DA / NOA completion time |
| 6 | Royalty-statement timeliness |
| 1 | Qualitative: OECD membership, censorship, bankruptcy history |

### Gap / Unsold — 23 metrics (selected)

Categories: *Performance & Track Record*, *Territory Volatility*, *Market Landscape*.

| Weight | Example metric |
|--------|----------------|
| 10 | Sales-accuracy ratio of the agent (last 18 mo) |
| 10 | Ashland's own sales-accuracy ratio (last 18 mo) |
| 8 | Sales-value average for territory × budget / director / producer (last 18 mo) |
| 7 | Territory × budget sales-value variance (coefficient of variation) |
| 6 | Territory × genre sales-value variance |

### Tax Credit — 25 metrics (selected)

Categories: *Performance & Track Record*, *Stability of Jurisdiction*, *FX Risk*, *Execution Risk*, *Concentration Risk*.

| Weight | Example metric |
|--------|----------------|
| 10 | Auditor variance between opinion letter and actual payment (last 18 mo) |
| 10 | Auditor query frequency (last 18 mo) |
| 9 | Policy stability of the jurisdiction for film tax credits |
| 9 | Historical consistency of auditor payment timeframes |
| 8 | Average qualifying-spend ratio the auditor books |
| 1 | FX: is the credit USD, foreign, transferable, hedge-able? |

---

## 4. Translation to features

Every metric is converted to a percentage on [0, 100] using one of three transforms (per the workbook):

1. **Efficiency ratio** — `target_time / actual_time × 100` (lower actual = higher score).
2. **Coefficient-of-variation inversion** — `(1 − CV) × 100` (more consistent = higher score).
3. **Direct percentage** — e.g. deposit percentage, qualifying-spend ratio.

The weighted sum of the translated metrics is the raw collateral score:

```
score = Σ (metric_pct × weight) / Σ weight
```

This is the **rule-based score** — deterministic, fully interpretable, and what the Excel natively computes.

---

## 5. Qualitative overlay

Beyond the quantitative rubric, the workbook's *Qualitative Metrics (AI)* sheet captures 28 structured questions covering:

- **Geopolitical Stability** — government stability, legal system, corruption, social unrest, FX.
- **Cultural Overview** — content fit, market saturation, critical reception, censorship, demographics.
- **Company / Shareholders Background** — reputation, leadership track record, ownership concentration, legal disputes, industry relationships.

These are intended to be LLM-scored from open sources (news, company filings, TMDB/OMDB) and fed in as auxiliary features. In the current build they are *captured* as input fields but default to neutral (50%) unless the user overrides.

---

## 6. Machine-learning layer

The rule-based score answers "how do we aggregate the signal?" It does **not** answer "which signals actually predict default?" — that requires labelled outcomes. Monika's ML layer solves this.

### Training data

- **Real films** pulled from TMDB/OMDB when `.env` has `TMDB_API_KEY` / `OMDB_API_KEY`, using the existing `utils/tmdb.py` / `utils/omdb.py` wrappers. Fields used: budget, revenue, vote_average, popularity, genre, release year.
- **Synthetic metric rows** generated per collateral type using the weight structure from the Excel, with plausible distributions (efficiency ratios lognormal, percentages beta, binary qualitative flags Bernoulli).
- **Label generation** — a film is labelled *default* (1) or *performing* (0) using a noisy rule: `default = rule_score < threshold + ε`, so the ML model has to *rediscover* the rubric and reveal feature importances.

### Models

Two models are trained in parallel:

- **Logistic Regression** (L2, standardised features) — gives interpretable coefficients and calibrated probabilities.
- **Random Forest** (200 trees, depth 8) — captures non-linear interactions and yields permutation / impurity-based feature importance.

Both are fit on an 80/20 split with accuracy, ROC-AUC, and a classification report stored next to the model artefacts.

### Artefacts

`models/` contains one subdirectory per collateral type:

```
models/
  pre_sales/
    rf.joblib            # Random Forest model
    logit.joblib         # Logistic Regression model
    scaler.joblib        # StandardScaler for logit
    features.json        # Ordered feature names + weights
    metrics.json         # Train/test accuracy, AUC, classification report
  gap_unsold/...
  tax_credit/...
```

---

## 7. Interpretable score

For a new counterparty, the module produces:

1. **Raw weighted score** (0–100) from the rubric.
2. **RF default probability** and **Logit default probability**.
3. **Blended score** — `100 × (1 − 0.5·P_rf − 0.5·P_logit)`, clipped to [0, 100].
4. **Letter rating** from the Option 2 band.
5. **Top-N contributing features** — for Logit: `coef × z-score`; for RF: `permutation_importance × (feature − mean) / std`. Positive = pushes toward default, negative = toward performance.

These are rendered as three Plotly charts on the `Credit Scoring` module:

- **Feature Importance** (horizontal bar) — global importance from the trained model.
- **Per-deal Contribution** (diverging bar) — local contribution of each feature *for the counterparty being scored*.
- **Score Gauge** — blended 0–100 with rating band colouring.

---

## 8. Open questions (from the workbook `Notes` sheet)

| # | Question | Resolution in current build |
|---|----------|------------------------------|
| 1 | Is `1 − CV` the right standardisation for variance metrics? | **OK** (confirmed in Notes) |
| 2 | How to define target time for Distributor NOAs? | Use **average across all distributors** (per Notes) |
| 3 | How to normalise MG value for budget / talent averages? | Use **average across all distributors** |
| 4 | Market-landscape metric — what base? | **Average distributor count across territories** |
| 5 | Tax-credit payment time — what reference? | **Average time across all programmes** |
| 6 | Auditor timeliness — what reference? | **Average for same-territory auditors** |

The **average across all** approach makes every metric relative to the Ashland portfolio — which has the side-effect of making the models chase *portfolio-relative* rather than *absolute* risk. When the portfolio is small this is noisy; once >50 deals exist the normalisation is robust.

---

## 9. What's *not* in the current model (future work)

- **Probability-of-default calibration** against realised outcomes (Ashland has no default history yet).
- **Correlation between collateral types** on the same deal (Pre-Sales + Gap + Tax Credit default together if the sales agent collapses).
- **Macro-factor overlay** (FX, interest-rate regime).
- **Dynamic re-scoring** as new metric data arrives mid-loan.

These are captured as backlog items but not built in this iteration.
