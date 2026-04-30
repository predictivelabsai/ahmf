# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Film financing operating system with AI-driven intelligence tools. Product name: **Monika**. Company: Ashland Hill Media Finance. The `ahmf` database schema is legacy and remains unchanged.

**Stack**: Python 3.13 (venv at `.venv/`), FastHTML, LangGraph + XAI Grok-3-Mini, PostgreSQL (`ahmf` schema), HTMX + WebSocket.

## Commands

```bash
source .venv/bin/activate          # or use .venv/bin/python directly
python app.py                      # start app on port 5010

python tests/test_suite.py         # 30-test unit suite (DB, auth, tools, APIs)
python tests/test_copilot.py       # copilot text-to-SQL tests (all shortcut buttons)
python tests/regression_suite.py --start-app  # 76 Python + Playwright tests

python data/seed_db.py             # seed sample data (idempotent)
python change_log.py               # patch bump changelog before push
python tests/capture_guide.py --start-app     # regenerate guide screenshots
python docs/generate_pptx.py       # regenerate slide deck
python -m utils.scoring.train      # retrain credit scoring ML models
```

Test results go to `test-data/*.json`. Regression screenshots go to `screenshots/`.

## Secrets Policy

**NEVER copy, persist, log, or document actual secret values.** Reference by variable name only (e.g. `XAI_API_KEY=...`). Verify no secrets in `git diff` before committing. Required env vars: `DB_URL`, `XAI_API_KEY`, `TMDB_API_KEY`, `TMDB_API_READ_TOKEN`, `OMDB_API_KEY`, `TAVILY_API_KEY`, `JWT_SECRET`, `ENCRYPTION_KEY`. Optional for Clerk SSO: `CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`.

## Architecture

### app.py (~2,500 lines, structured monolith)

The main application file contains most routes and the agent setup. Major sections in order:

1. **Agent setup** — LangGraph `create_react_agent` with 18 tool functions defined inline
2. **Command interceptor** — Pre-filters colon-syntax commands (e.g. `deal:list`, `contact:search`); returns markdown string or `None` to fall through to AI agent
3. **AG-UI initialization** — `setup_agui(app, agent, command_interceptor)` wires the WebSocket chat
4. **API endpoints** — `/api/health`, `/api/copilot/*`, `/api/export/*`, `/api/import/*`
5. **Auth routes** — Login, register, Clerk SSO bridge, password reset
6. **Module pages** — Deals, contacts, home dashboard, reporting (~40 routes)
7. **Module registration** — 13 modules imported and registered via `register_routes(rt)` at bottom
8. **Index route** — Main page with 3-pane layout
9. **`serve()`** — Starts uvicorn on port 5010

### Two chat systems

**Main Chat (center pane)** — Full LangGraph agent with 18 tools, persistent conversation threads, WebSocket streaming via `astream_events(v2)`. Messages stored in `utils/agui/chat_store.py`. Command interceptor runs first; if no match, query goes to AI.

**AI Copilot (right pane)** — Stateless text-to-SQL assistant in `agents/copilot.py`. Module-aware: `COPILOT_SHORTCUTS` maps each module to suggested queries. Three-step pipeline: LLM generates SQL → execute against DB → LLM formats results. Uses schema from `sql/db_schema.json`. Endpoint: `POST /api/copilot/query`.

### Module pattern

Each module in `modules/` exports `register_routes(rt)` to mount its routes on the FastHTML router. Some modules also export tool functions used by the LangGraph agent (dual role: page routes + agent tools). The landing page is an exception — imported inline in the index route.

### AG-UI chat engine (utils/agui/)

Vendored chat framework with three classes: `UI` (renders messages/input), `AGUIThread` (per-thread state, handles message flow and AI streaming), `AGUISetup` (thread container, registers WebSocket routes). WebSocket at `/agui/ws/{thread_id}` handles real-time streaming. Events flow as: user message → command interceptor → LangGraph `astream_events(v2)` → token-by-token broadcast to subscribers → marked.js renders markdown client-side.

### Database layer

`utils/db.py` provides `DatabasePool` singleton. Usage: `get_pool().get_session()` returns a context-managed session that auto-commits on success, rolls back on exception. Pool size 5, max overflow 10, with `pool_pre_ping=True`. All queries use the `ahmf.` schema prefix.

### Authentication

Dual auth: Clerk SSO (if `CLERK_SECRET_KEY` configured) or local email/password fallback. Clerk bridge in `_check_clerk_session()` validates `__session` cookie JWT via JWKS, fetches user from Clerk API, auto-creates local DB user on first login, and syncs to FastHTML session. Local auth uses bcrypt + JWT tokens (7-day expiry) in `utils/auth.py`.

### Frontend

Custom CSS in `static/app.css` (no framework). 3-pane grid: left nav (240px) | center (1fr) | right copilot (360px). JS in `static/chat.js` handles module switching (`loadModule()`), right pane toggling, CSV export, table sorting. Charts use Plotly 2.32.0. Markdown rendered by marked.js. Clerk SDK loaded conditionally from CDN.

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `modules/` | Product module routes (13 modules with `register_routes(rt)` pattern) |
| `agents/` | LangGraph agent config and copilot text-to-SQL |
| `agents/tools/` | Structured tool functions for agents |
| `utils/` | Core utilities (db, auth, clerk, TMDB, OMDB, PDF extraction) |
| `utils/agui/` | AG-UI WebSocket chat engine |
| `utils/scoring/` | Credit-scoring ML package (catalog, dataset, training, inference) |
| `sql/` | Database migrations (01-13) and `db_schema.json` |
| `config/` | App settings and constants |
| `data/` | Seed CSVs and `seed_db.py` |
| `models/` | Trained ML model artefacts per collateral type |

## Products

1. **Film Financing OS** — Deals, Sales & Collections, Credit Rating, Accounting, Contacts, Communications
2. **Sales Estimates Generator** — TMDB/OMDB comp analysis, territory MG projections
3. **Production Risk Scoring** — AI scores 6 risk dimensions (0-100)
4. **Smart Budgeting Tool** — AI generates low/mid/high budget scenarios
5. **Automated Production Scheduling** — AI generates day-by-day schedules
6. **Soft Funding Discovery Engine** — 16 global incentive programs, rebate calculator
7. **Deal Closing & Data Room** — Per-deal 20-item closing checklists
8. **Audience & Marketing Intelligence** — AI predicts audience segments, marketing channels
9. **Talent Intelligence** — TMDB actor search, AI cast recommendations
10. **Credit Scoring (ML)** — RF + Logistic Regression per collateral type. Methodology in `docs/counterparty_risk_methodology.md`

## Chat Commands

```
deal:list / deal:DEAL_ID         List deals / view deal details
contact:search NAME              Search contacts
portfolio                        Portfolio overview
estimate:new / risk:new          Sales estimate / risk assessment
budget:new / schedule:new        Budget / shooting schedule
incentives / talent:search NAME  Incentives / actor search
audience:new                     Audience & marketing analysis
sales:list / credit:CONTACT      Sales contracts / credit rating
transactions / messages          Transaction ledger / messages & tasks
help                             Show available commands
```

## Deployment

```bash
docker build -t ahmf . && docker run --env-file .env -p 5010:5010 ahmf
# Coolify: auto-deploys on push to main via docker-compose.yml
```
