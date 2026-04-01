# AHMF — Ashland Hill Media Finance AI

Film financing operating system with AI-driven intelligence tools.

## Stack

- **Python 3.13**, virtualenv at `.venv/`
- **FastHTML** 3-pane agentic UI (`app.py`, port 5010)
- **LangGraph** + XAI Grok-3 for AI chat agents
- **PostgreSQL** (`ahmf` schema on finespresso_db)
- **HTMX + WebSocket** for real-time streaming

## Key Directories

| Directory | Purpose |
|-----------|---------|
| `modules/` | Product module routes (deals, contacts, risk, budget, schedule, funding, dataroom, audience, talent, guide) |
| `agents/` | LangGraph agents and tool definitions |
| `agents/tools/` | Structured tool functions for agents |
| `utils/` | Core utilities (db, auth, TMDB, OMDB, PDF extraction) |
| `utils/agui/` | AG-UI chat engine (vendored from alpatrade, adapted) |
| `sql/` | Database migrations (01-13) |
| `config/` | App settings and constants |
| `tests/` | Test suite (30 tests) |
| `test-data/` | Test results and screenshots (generated) |
| `static/guide/` | User guide screenshots (generated via Playwright) |
| `docs/` | Roadmap PDF, presentation markdown, PPTX, generator script |

## Products (from Roadmap)

1. **Film Financing OS** — Deals, Sales & Collections, Credit Rating, Accounting, Contacts, Communications
2. **Sales Estimates Generator** — TMDB/OMDB comp analysis, territory MG projections, box office forecasting
3. **Production Risk Scoring** — AI scores 6 risk dimensions (0-100), risk tier, mitigations
4. **Smart Budgeting Tool** — AI generates low/mid/high budget scenarios with line items
5. **Automated Production Scheduling** — AI generates day-by-day schedules with location clustering
6. **Soft Funding Discovery Engine** — 16 seeded global incentive programs, rebate calculator
7. **Deal Closing & Data Room** — Per-deal 20-item closing checklists, document tracking
8. **Audience & Marketing Intelligence** — AI predicts audience segments, marketing channels, release strategy
9. **Talent Intelligence** — TMDB actor search, AI cast recommendations with heat/fit/ROI scores

## Secrets Policy

**NEVER copy, persist, log, or document actual secret values.** API keys, tokens, passwords, and connection strings from `.env` must only be used transiently during runtime.
- Do not write secret values into source files, docs, markdown, YAML, or memory files
- Do not include secrets in commit messages, comments, or debug output
- Do not hardcode API keys — always read from environment variables
- Reference secrets by variable name only (e.g. `XAI_API_KEY=...`)
- Before committing, verify no secrets appear in `git diff` output

## Required Environment Variables (.env)

```
DB_URL=...                    # PostgreSQL connection string
XAI_API_KEY=...               # XAI Grok LLM
TMDB_API_KEY=...              # TMDB movie database
TMDB_API_READ_TOKEN=...       # TMDB read access token
OMDB_API_KEY=...              # OMDB movie data
TAVILY_API_KEY=...            # Tavily web search
JWT_SECRET=...                # JWT signing secret
ENCRYPTION_KEY=...            # Fernet encryption key
```

## Authentication

- **Email/password** registration + login with bcrypt password hashing
- **JWT tokens** for session management (7-day expiry)
- **Data isolation**: All tables have `created_by` / `user_id` column
- **Auth module**: `utils/auth.py`

## Running

```bash
# Activate venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run SQL migrations
for f in sql/*.sql; do psql $DB_URL -f "$f"; done

# Start the app
python app.py    # port 5010
```

## Testing

```bash
# Run the full test suite (30 tests)
# Covers: DB, auth, JWT, deal/contact tools, TMDB/OMDB APIs,
# incentives, talent search, closing checklists, command interceptor,
# chat store, config, PDF extractor
python tests/test_suite.py

# Results written to test-data/*.json
# test-data/test_summary.json has pass/fail counts
```

When the user says "run tests" or "run regression", execute `python tests/test_suite.py`.

## User Guide Generation

The in-app User Guide (`modules/guide.py`) displays screenshots from `static/guide/`.
To regenerate screenshots after UI changes:

1. Start the app: `python app.py`
2. Use Playwright MCP to navigate to each module and capture screenshots:
   - Login page → `static/guide/00_login.png`
   - Welcome screen → `static/guide/01_welcome.png`
   - Each module page (deals, contacts, estimates, risk, budget, schedule, funding, dataroom, audience, talent)
   - Key sub-pages (new deal form, risk form, checklist detail)
   - Chat responses (help command, portfolio command)
3. Screenshots are served as static files and embedded in the guide via `<img src="/static/guide/...">`

The guide has 13 sections with table of contents, each with a description, screenshot, and caption.

## Slide Deck Generation

```bash
# Generate the management PowerPoint presentation
python docs/generate_pptx.py

# Output: docs/AHMF_Platform_Overview.pptx (16 slides)
# Uses screenshots from static/guide/ for slide visuals
# Upload to Google Slides or open in PowerPoint
```

The markdown version is at `docs/AHMF_Platform_Overview.md` for reference.

To regenerate after changes: update screenshots first (see User Guide Generation above), then run the script. The script reads from `static/guide/` and produces a branded PPTX with Ashland Hill blue theme.

## Chat Commands

```
deal:list                    List all deals
deal:DEAL_ID                 View deal details
contact:search NAME          Search contacts
portfolio                    Portfolio overview
estimate:new                 Generate sales estimate
risk:new                     Production risk assessment
budget:new                   Generate production budget
schedule:new                 Generate shooting schedule
incentives                   Search film incentive programs
talent:search NAME           Search actors/directors
audience:new                 Audience & marketing analysis
help                         Show available commands
```

## Architecture

- **3-pane layout**: Left sidebar (260px nav) | Center (chat + module views) | Right (380px detail canvas)
- **Command interceptor**: Colon-syntax routed to handlers, free-form to LangGraph AI
- **WebSocket streaming**: LangGraph astream_events(v2) for real-time AI responses
- **HTMX module views**: Product pages swapped into center pane via hx-get/hx-swap
- **14 AI agent tools**: deals, contacts, portfolio, TMDB/OMDB, risk, budget, schedule, incentives, closing, audience, talent

## Deployment

```bash
# Docker build & run locally
docker build -t ahmf .
docker run --env-file .env -p 5010:5010 ahmf

# Coolify: auto-deploys on push to main
# docker-compose.yml: service "web", expose 5010, healthcheck on /api/health
# Matches filmfunder.predictivelabs.ai deployment pattern
```
