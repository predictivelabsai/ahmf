# Change Log

All notable changes to Monika are recorded here. Version format: `x.y.z (YYYY-MM-DD)`.

Bumps are managed by `change_log.py`:

```bash
python change_log.py              # patch bump (default)
python change_log.py --bump minor
python change_log.py --bump major
python change_log.py --message "Release notes..."
```

---

## v0.2.1 (2026-04-19)

Reskin landing to Ashland Hill palette: white body, deep teal-navy hero, gold accent, twilight horizon — drop pinks/magentas

## v0.2.0 (2026-04-19)

Add Monika landing page with Santa Monica/sunset palette, real Ashland Hill slate and team, and links back to ashland-hill.com

## v0.1.0 (2026-04-16)

### Added
- **Credit Scoring (ML) module** — new left-sidebar tab, non-chat. Random Forest + Logistic Regression trained per collateral type (Pre-Sales, Gap / Unsold, Tax Credit). Global feature-importance bar chart, per-deal contribution diverging bar, score gauge, and driver detail table — all Plotly.
- **Scoring pipeline** (`utils/scoring/`): Excel metric catalog loader, synthetic dataset generator with optional TMDB anchor, training script, inference bundle.
- **Methodology doc** — `docs/counterparty_risk_methodology.md` captures the three collateral types, rating bands (Option 2), metric inventory, transformation rules, qualitative overlay, and ML layer.
- **Specs folder** — wireframes (FINANCE - Sample UX-UIs) and credit-scoring methodology Excel from the older Monica designs archive.
- **Change-log workflow** — `docs/change_log.md` + `change_log.py` bumper script (patch / minor / major, optional tag, dry-run, --message override).
- **Regression suite** — `tests/regression_suite.py` with 76 tests (44 Python-level + 32 Playwright UI) covering DB, auth, agent tools, TMDB/OMDB, command interceptor, chat store, config, credit-scoring ML, and every module page. Screenshots land in `screenshots/`.

### Changed
- **Rebrand to Monika** — product name is now **Monika** with subtitle *Ashland Hill Media Finance*. Sidebar logo, page titles, login/register pages, system prompt, and README updated. DB schema `ahmf` left unchanged (legacy namespace).
- **README clone URL** updated to `predictivelabsai/monika`.
- **Demo video regenerated** with the new sidebar (Credit Scoring entry + Monika brand).

### Infra
- Added `scikit-learn`, `joblib`, `pandas`, `numpy`, `openpyxl` to `requirements.txt`.
- New `models/` directory for trained artefacts (one subdirectory per collateral type).
- `.gitignore` updated to exclude `.playwright-mcp/`, `screenshots/`, regression-suite outputs, source archives in `specs/`, and the 26MB SOW PDF.
