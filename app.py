"""
AHMF — Ashland Hill Media Finance AI

3-pane agentic UI for film financing intelligence.

Left pane:  Navigation sidebar (9 products, auth, settings)
Center:     Chat (WebSocket streaming) + module content views
Right:      AI thinking trace / detail canvas (toggled)

Launch:  python app.py          # port 5010
         uvicorn app:app --port 5010 --reload
"""

import os
import sys
import uuid as _uuid
import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from fasthtml.common import *

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LangGraph Agent
# ---------------------------------------------------------------------------

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

SYSTEM_PROMPT = (
    "You are AHMF, an AI assistant for Ashland Hill Media Finance — a film financing company. "
    "You help underwriters, investment committees, and production teams with: "
    "deal management, sales estimates, production risk assessment, budgeting, and market intelligence. "
    "You have access to TMDB and OMDB for movie/film data. "
    "Be concise and use markdown formatting with tables where appropriate. "
    "When users ask about deals, use the deal lookup tools. "
    "When users ask about contacts or distributors, use contact tools. "
    "For film comparisons or revenue estimates, use market research tools. "
    "Users can also type structured commands: deal:list, contact:search NAME, estimate:TITLE, portfolio, help."
)

llm = ChatOpenAI(
    api_key=os.getenv("XAI_API_KEY"),
    base_url="https://api.x.ai/v1",
    model="grok-3-mini",
    streaming=True,
)


# ---------------------------------------------------------------------------
# Agent Tools
# ---------------------------------------------------------------------------

def search_deals(query: str = "") -> str:
    """Search deals by title, borrower, or status. Returns a markdown table of matching deals."""
    from sqlalchemy import text
    from utils.db import get_pool
    try:
        pool = get_pool()
        with pool.get_session() as session:
            if query:
                rows = session.execute(text("""
                    SELECT deal_id, title, status, loan_amount, borrower_name, genre
                    FROM ahmf.deals
                    WHERE title ILIKE :q OR borrower_name ILIKE :q OR status ILIKE :q
                    ORDER BY created_at DESC LIMIT 20
                """), {"q": f"%{query}%"}).fetchall()
            else:
                rows = session.execute(text("""
                    SELECT deal_id, title, status, loan_amount, borrower_name, genre
                    FROM ahmf.deals ORDER BY created_at DESC LIMIT 20
                """)).fetchall()
        if not rows:
            return "No deals found."
        header = "| Title | Status | Amount | Borrower | Genre |\n|-------|--------|--------|----------|-------|\n"
        lines = []
        for r in rows:
            amt = f"${r[3]:,.0f}" if r[3] else "—"
            lines.append(f"| {r[1]} | {r[2]} | {amt} | {r[4] or '—'} | {r[5] or '—'} |")
        return f"## Deals\n\n{header}" + "\n".join(lines)
    except Exception as e:
        return f"Error searching deals: {e}"


def get_deal_detail(deal_id: str) -> str:
    """Get detailed information about a specific deal by its ID."""
    from sqlalchemy import text
    from utils.db import get_pool
    try:
        pool = get_pool()
        with pool.get_session() as session:
            row = session.execute(text("""
                SELECT deal_id, title, project_type, genre, status, loan_amount,
                       currency, interest_rate, term_months, borrower_name,
                       producer, director, cast_summary, budget, territory,
                       origination_date, maturity_date
                FROM ahmf.deals WHERE deal_id = :did
            """), {"did": deal_id}).fetchone()
        if not row:
            return f"Deal {deal_id} not found."
        return (
            f"## {row[1]}\n\n"
            f"**Status:** {row[4]}  \n"
            f"**Type:** {row[2]} | **Genre:** {row[3]}  \n"
            f"**Loan:** {row[6]} {row[5]:,.0f} at {row[7]}% for {row[8]} months  \n"
            f"**Borrower:** {row[9]}  \n"
            f"**Producer:** {row[10]} | **Director:** {row[11]}  \n"
            f"**Cast:** {row[12] or '—'}  \n"
            f"**Budget:** ${row[13]:,.0f}  \n"
            f"**Territory:** {row[14]}  \n"
            f"**Origination:** {row[15]} | **Maturity:** {row[16]}"
        )
    except Exception as e:
        return f"Error fetching deal: {e}"


def get_portfolio_overview() -> str:
    """Get aggregate portfolio statistics — total deals, loan amounts, status breakdown."""
    from sqlalchemy import text
    from utils.db import get_pool
    try:
        pool = get_pool()
        with pool.get_session() as session:
            stats = session.execute(text("""
                SELECT status, COUNT(*), COALESCE(SUM(loan_amount), 0)
                FROM ahmf.deals GROUP BY status ORDER BY status
            """)).fetchall()
            total = session.execute(text("""
                SELECT COUNT(*), COALESCE(SUM(loan_amount), 0) FROM ahmf.deals
            """)).fetchone()
        if not total or total[0] == 0:
            return "No deals in portfolio yet."
        lines = [
            f"## Portfolio Overview\n",
            f"**Total Deals:** {total[0]} | **Total Committed:** ${total[1]:,.0f}\n",
            "| Status | Count | Amount |",
            "|--------|-------|--------|",
        ]
        for s in stats:
            lines.append(f"| {s[0]} | {s[1]} | ${s[2]:,.0f} |")
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching portfolio: {e}"


def search_contacts(query: str = "") -> str:
    """Search contacts by name, company, or type."""
    from sqlalchemy import text
    from utils.db import get_pool
    try:
        pool = get_pool()
        with pool.get_session() as session:
            if query:
                rows = session.execute(text("""
                    SELECT contact_id, name, company, contact_type, email
                    FROM ahmf.contacts
                    WHERE name ILIKE :q OR company ILIKE :q OR contact_type ILIKE :q
                    ORDER BY name LIMIT 20
                """), {"q": f"%{query}%"}).fetchall()
            else:
                rows = session.execute(text("""
                    SELECT contact_id, name, company, contact_type, email
                    FROM ahmf.contacts ORDER BY name LIMIT 20
                """)).fetchall()
        if not rows:
            return "No contacts found."
        header = "| Name | Company | Type | Email |\n|------|---------|------|-------|\n"
        lines = []
        for r in rows:
            lines.append(f"| {r[1]} | {r[2] or '—'} | {r[3]} | {r[4] or '—'} |")
        return f"## Contacts\n\n{header}" + "\n".join(lines)
    except Exception as e:
        return f"Error searching contacts: {e}"


def search_movies(query: str) -> str:
    """Search for movies using TMDB API for comp analysis."""
    import httpx
    try:
        api_key = os.getenv("TMDB_API_KEY")
        resp = httpx.get(
            "https://api.themoviedb.org/3/search/movie",
            params={"api_key": api_key, "query": query, "language": "en-US"},
            timeout=10,
        )
        data = resp.json()
        results = data.get("results", [])[:5]
        if not results:
            return f"No movies found for '{query}'."
        lines = ["## TMDB Results\n", "| Title | Year | Rating | Popularity |", "|-------|------|--------|------------|"]
        for m in results:
            year = m.get("release_date", "")[:4]
            lines.append(f"| {m['title']} | {year} | {m.get('vote_average', 0):.1f} | {m.get('popularity', 0):.0f} |")
        return "\n".join(lines)
    except Exception as e:
        return f"Error searching TMDB: {e}"


def get_movie_details(tmdb_id: int) -> str:
    """Get detailed movie info from TMDB including budget and revenue."""
    import httpx
    try:
        api_key = os.getenv("TMDB_API_KEY")
        resp = httpx.get(
            f"https://api.themoviedb.org/3/movie/{tmdb_id}",
            params={"api_key": api_key, "language": "en-US"},
            timeout=10,
        )
        m = resp.json()
        genres = ", ".join(g["name"] for g in m.get("genres", []))
        return (
            f"## {m.get('title')}\n\n"
            f"**Release:** {m.get('release_date')} | **Runtime:** {m.get('runtime')} min  \n"
            f"**Genres:** {genres}  \n"
            f"**Budget:** ${m.get('budget', 0):,} | **Revenue:** ${m.get('revenue', 0):,}  \n"
            f"**Rating:** {m.get('vote_average', 0):.1f}/10 ({m.get('vote_count', 0):,} votes)  \n"
            f"**Popularity:** {m.get('popularity', 0):.0f}  \n\n"
            f"{m.get('overview', '')}"
        )
    except Exception as e:
        return f"Error fetching movie details: {e}"


# Import module tools
from modules.risk import analyze_production_risk
from modules.budget import generate_budget_tool
from modules.schedule import generate_schedule_tool
from modules.funding import search_incentives_tool
from modules.dataroom import generate_closing_checklist_tool
from modules.audience import analyze_audience_tool
from modules.talent import search_talent_tool, analyze_talent_tool

TOOLS = [
    search_deals, get_deal_detail, get_portfolio_overview, search_contacts,
    search_movies, get_movie_details,
    analyze_production_risk, generate_budget_tool, generate_schedule_tool,
    search_incentives_tool, generate_closing_checklist_tool,
    analyze_audience_tool, search_talent_tool, analyze_talent_tool,
]

langgraph_agent = create_react_agent(model=llm, tools=TOOLS, prompt=SYSTEM_PROMPT)


# ---------------------------------------------------------------------------
# Command Interceptor
# ---------------------------------------------------------------------------

async def _command_interceptor(msg: str, session) -> str | None:
    """Route structured commands. Return result string or None to fall through to AI."""
    cmd = msg.strip().lower()
    parts = cmd.split(None, 1)
    first = parts[0] if parts else ""
    rest = parts[1] if len(parts) > 1 else ""

    if first == "deal:list" or first == "deals":
        return search_deals(rest)
    if first.startswith("deal:") and len(first) > 5:
        deal_id = first[5:]
        return get_deal_detail(deal_id)
    if first == "contact:search" or first == "contacts":
        return search_contacts(rest)
    if first == "portfolio":
        return get_portfolio_overview()
    if first == "help":
        return (
            "## Available Commands\n\n"
            "| Command | Description |\n"
            "|---------|-------------|\n"
            "| `deal:list` | List all deals |\n"
            "| `deal:DEAL_ID` | View deal details |\n"
            "| `contact:search NAME` | Search contacts |\n"
            "| `portfolio` | Portfolio overview |\n"
            "| `estimate:new` | Generate sales estimate |\n"
            "| `risk:new` | Production risk assessment |\n"
            "| `budget:new` | Generate production budget |\n"
            "| `schedule:new` | Generate shooting schedule |\n"
            "| `incentives` | Search film incentive programs |\n"
            "| `talent:search NAME` | Search actors/directors |\n"
            "| `audience:new` | Audience & marketing analysis |\n"
            "| `help` | Show this help |\n\n"
            "Or ask any question in natural language."
        )
    if first == "estimate:new" or first.startswith("estimate:"):
        return (
            "## Sales Estimate Generator\n\n"
            "To generate a sales estimate, provide:\n"
            "- **Title** of the project\n"
            "- **Genre** (e.g., Action, Drama, Horror)\n"
            "- **Budget range** (e.g., $5M-$15M)\n"
            "- **Cast** (known actors attached)\n"
            "- **Director**\n\n"
            "Ask me: *'Estimate revenue for [Title], a [genre] film with [cast] directed by [director] at $[budget]'*"
        )
    if first == "risk:new":
        return "Navigate to **Risk Scoring** in the sidebar, or ask me to analyze risk for a specific project.\n\nExample: *'Analyze production risk for a $20M action film shooting in Georgia with heavy VFX'*"
    if first == "budget:new":
        return "Navigate to **Smart Budget** in the sidebar, or ask me to generate a budget.\n\nExample: *'Generate a budget for a $15M drama with A-list cast shooting 35 days in NYC'*"
    if first == "schedule:new":
        return "Navigate to **Scheduling** in the sidebar, or ask me to create a schedule.\n\nExample: *'Create a 25-day shooting schedule for a thriller at 3 locations'*"
    if first == "incentives" or first == "incentive:search":
        return search_incentives_tool(rest)
    if first == "talent:search":
        return search_talent_tool(rest) if rest else "Usage: `talent:search ACTOR_NAME`"
    if first == "audience:new":
        return "Navigate to **Audience Intel** in the sidebar, or ask me to analyze audience for a project.\n\nExample: *'Analyze target audience for a $30M sci-fi film starring Chris Hemsworth'*"

    return None


# ---------------------------------------------------------------------------
# FastHTML App
# ---------------------------------------------------------------------------

app, rt = fast_app(
    exts="ws",
    secret_key=os.getenv("JWT_SECRET", "ahmf-dev-secret"),
    hdrs=(
        Script(src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"),
        Script(src="https://cdn.plot.ly/plotly-2.32.0.min.js"),
    ),
)

from utils.agui import setup_agui, get_chat_styles, StreamingCommand, list_conversations

agui = setup_agui(app, langgraph_agent, command_interceptor=_command_interceptor)


# ---------------------------------------------------------------------------
# Layout CSS
# ---------------------------------------------------------------------------

APP_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body { height: 100vh; overflow: hidden; }

/* === 3-Pane Grid === */
.app-layout {
  display: grid;
  grid-template-columns: 260px 1fr;
  height: 100vh;
  transition: grid-template-columns 0.3s ease;
}

.app-layout .right-pane { display: none; }

.app-layout.right-open {
  grid-template-columns: 260px 1fr 380px;
}

.app-layout.right-open .right-pane { display: flex; }

/* === Left Pane (Sidebar) === */
.left-pane {
  background: #f8fafc;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  height: 100vh;
}

.sidebar-logo {
  padding: 1.25rem 1rem;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.sidebar-logo-icon {
  width: 36px; height: 36px;
  background: linear-gradient(135deg, #0066cc, #004d99);
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  color: white; font-weight: 700; font-size: 0.9rem;
}

.sidebar-logo-text {
  font-size: 0.9rem; font-weight: 700; color: #1e293b;
}

.sidebar-logo-sub {
  font-size: 0.65rem; color: #64748b; margin-top: 0.1rem;
}

.sidebar-section {
  padding: 0.75rem 0;
}

.sidebar-section-title {
  padding: 0 1rem 0.5rem;
  font-size: 0.65rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #94a3b8;
}

.sidebar-item {
  display: flex; align-items: center; gap: 0.5rem;
  padding: 0.5rem 1rem;
  font-size: 0.8rem;
  color: #475569;
  cursor: pointer;
  transition: all 0.15s;
  text-decoration: none;
  border: none;
  background: none;
  width: 100%;
  text-align: left;
}

.sidebar-item:hover { background: #e2e8f0; color: #1e293b; }
.sidebar-item.active { background: #dbeafe; color: #0066cc; font-weight: 600; }

.sidebar-item-icon {
  width: 18px; height: 18px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}

.sidebar-badge {
  margin-left: auto;
  background: #0066cc;
  color: white;
  font-size: 0.6rem;
  padding: 0.1rem 0.4rem;
  border-radius: 1rem;
  font-weight: 600;
}

.sidebar-badge.coming { background: #94a3b8; }

.sidebar-footer {
  margin-top: auto;
  padding: 1rem;
  border-top: 1px solid #e2e8f0;
}

/* === Center Pane === */
.center-pane {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.center-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #e2e8f0;
  background: #ffffff;
  min-height: 50px;
}

.center-header h2 {
  font-size: 0.9rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

.center-chat { flex: 1; overflow: hidden; }

.header-btn {
  padding: 0.4rem 0.6rem;
  background: none; border: 1px solid #e2e8f0;
  border-radius: 6px; cursor: pointer; font-size: 0.75rem; color: #64748b;
  transition: all 0.15s;
}
.header-btn:hover { background: #f1f5f9; color: #1e293b; }

/* === Right Pane === */
.right-pane {
  background: #ffffff;
  border-left: 1px solid #e2e8f0;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.right-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #e2e8f0;
  min-height: 50px;
}

.right-header h3 {
  font-size: 0.85rem; font-weight: 600; color: #1e293b; margin: 0;
}

.right-tabs {
  display: flex; gap: 0.5rem; padding: 0.5rem 1rem;
  border-bottom: 1px solid #e2e8f0;
}

.right-tab {
  padding: 0.35rem 0.75rem; font-size: 0.75rem;
  border: 1px solid transparent; border-radius: 6px;
  cursor: pointer; background: none; color: #64748b;
  transition: all 0.15s;
}
.right-tab:hover { background: #f1f5f9; }
.right-tab.active { background: #dbeafe; color: #0066cc; border-color: #93c5fd; }

.right-content {
  flex: 1; overflow-y: auto; padding: 1rem;
}

#trace-content, #detail-content {
  font-size: 0.8rem; color: #475569;
}

.trace-entry {
  padding: 0.4rem 0.5rem;
  border-left: 3px solid #e2e8f0;
  margin-bottom: 0.4rem;
  font-size: 0.75rem;
}
.trace-label { font-weight: 600; color: #1e293b; }
.trace-detail { color: #64748b; margin-left: 0.5rem; }
.trace-run-start { border-color: #0066cc; }
.trace-run-end { border-color: #16a34a; }
.trace-tool-active { border-color: #f59e0b; }
.trace-tool-done { border-color: #16a34a; }
.trace-error { border-color: #dc2626; }

/* === Auth Forms === */
.auth-container {
  max-width: 400px; margin: 3rem auto; padding: 2rem;
}

.auth-form {
  display: flex; flex-direction: column; gap: 1rem;
}

.auth-form input {
  padding: 0.6rem 0.75rem;
  border: 1px solid #e2e8f0; border-radius: 8px;
  font-size: 0.875rem; font-family: inherit;
  background: #f8fafc;
}
.auth-form input:focus { outline: none; border-color: #0066cc; box-shadow: 0 0 0 3px rgba(0,102,204,0.1); }

.auth-btn {
  padding: 0.6rem 1rem;
  background: #0066cc; color: white; border: none; border-radius: 8px;
  font-size: 0.875rem; font-weight: 600; cursor: pointer;
  transition: background 0.15s;
}
.auth-btn:hover { background: #0052a3; }

.auth-link { font-size: 0.8rem; color: #0066cc; text-align: center; }

/* === Module Content === */
.module-content {
  padding: 1.5rem;
  overflow-y: auto;
  height: 100%;
}

.module-content h1 { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin-bottom: 1rem; }
.module-content h2 { font-size: 1.125rem; font-weight: 600; color: #1e293b; margin-bottom: 0.75rem; }

.stats-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem; margin-bottom: 1.5rem;
}

.stat-card {
  background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px;
  padding: 1.25rem; transition: all 0.2s;
}
.stat-card:hover { border-color: #93c5fd; box-shadow: 0 2px 8px rgba(0,102,204,0.08); }
.stat-label { font-size: 0.7rem; text-transform: uppercase; color: #64748b; letter-spacing: 0.05em; }
.stat-value { font-size: 1.75rem; font-weight: 700; color: #1e293b; margin-top: 0.25rem; }

.deal-card {
  background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px;
  padding: 1rem; margin-bottom: 0.75rem; cursor: pointer; transition: all 0.2s;
}
.deal-card:hover { border-color: #93c5fd; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,102,204,0.08); }

.deal-card-title { font-size: 0.9rem; font-weight: 600; color: #1e293b; }
.deal-card-meta { font-size: 0.75rem; color: #64748b; margin-top: 0.25rem; }

.status-pill {
  display: inline-block; padding: 0.15rem 0.5rem; border-radius: 1rem;
  font-size: 0.7rem; font-weight: 600;
}
.status-pipeline { background: #fef3c7; color: #92400e; }
.status-active { background: #dcfce7; color: #166534; }
.status-closed { background: #f1f5f9; color: #475569; }
.status-declined { background: #fef2f2; color: #991b1b; }

/* === Coming Soon === */
.coming-soon {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 3rem; text-align: center; height: 100%;
}
.coming-soon-icon {
  width: 64px; height: 64px; background: #f1f5f9; border-radius: 16px;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 1rem; font-size: 1.5rem;
}
.coming-soon h2 { font-size: 1.25rem; font-weight: 700; color: #1e293b; margin-bottom: 0.5rem; }
.coming-soon p { font-size: 0.875rem; color: #64748b; max-width: 400px; }
.coming-soon-features {
  margin-top: 1.5rem; text-align: left;
}
.coming-soon-features li {
  font-size: 0.8rem; color: #475569; padding: 0.25rem 0;
}

/* === Responsive === */
@media (max-width: 768px) {
  .app-layout { grid-template-columns: 1fr !important; }
  .left-pane { display: none; }
  .right-pane { display: none; }
}
"""

LAYOUT_JS = """
function toggleRightPane() {
    var layout = document.querySelector('.app-layout');
    layout.classList.toggle('right-open');
}

function showTab(tabName) {
    document.querySelectorAll('.right-tab').forEach(function(t) { t.classList.remove('active'); });
    document.querySelectorAll('[data-tab]').forEach(function(c) { c.style.display = 'none'; });
    var tab = document.querySelector('[data-tab-btn="'+tabName+'"]');
    var content = document.querySelector('[data-tab="'+tabName+'"]');
    if (tab) tab.classList.add('active');
    if (content) content.style.display = 'block';
}

function loadModule(path, title) {
    // Load a module page into the center content area
    var container = document.getElementById('center-content');
    var chatContainer = document.getElementById('center-chat');
    if (container && chatContainer) {
        chatContainer.style.display = 'none';
        container.style.display = 'block';
        htmx.ajax('GET', path, {target: '#center-content', swap: 'innerHTML'});
    }
    // Update header
    var h = document.getElementById('center-title');
    if (h) h.textContent = title;
    // Update active sidebar
    document.querySelectorAll('.sidebar-item').forEach(function(i) { i.classList.remove('active'); });
    event.currentTarget.classList.add('active');
}

function showChat() {
    var container = document.getElementById('center-content');
    var chatContainer = document.getElementById('center-chat');
    if (container) container.style.display = 'none';
    if (chatContainer) chatContainer.style.display = 'block';
    var h = document.getElementById('center-title');
    if (h) h.textContent = 'AI Chat';
    document.querySelectorAll('.sidebar-item').forEach(function(i) { i.classList.remove('active'); });
    var chatBtn = document.getElementById('nav-chat');
    if (chatBtn) chatBtn.classList.add('active');
}
"""


# ---------------------------------------------------------------------------
# Sidebar icons (SVG)
# ---------------------------------------------------------------------------

_ICONS = {
    "chat": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>',
    "deals": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 00-2-2h-4a2 2 0 00-2 2v16"/></svg>',
    "contacts": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    "sales": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/></svg>',
    "credit": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>',
    "accounting": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="4" width="22" height="16" rx="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>',
    "comms": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>',
    "estimate": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 20V10M12 20V4M6 20v-6"/></svg>',
    "risk": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    "budget": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>',
    "schedule": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>',
    "funding": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/></svg>',
    "dataroom": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>',
    "audience": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>',
    "talent": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>',
    "logout": '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>',
}


def _icon(name):
    return NotStr(_ICONS.get(name, ""))


# ---------------------------------------------------------------------------
# Layout Components
# ---------------------------------------------------------------------------

def _sidebar_item(icon_name, label, onclick="", badge=None, item_id="", active=False):
    badge_el = Span(badge, cls=f"sidebar-badge {'coming' if badge == 'Soon' else ''}") if badge else ""
    return Button(
        Span(_icon(icon_name), cls="sidebar-item-icon"),
        label,
        badge_el,
        cls=f"sidebar-item {'active' if active else ''}",
        onclick=onclick,
        id=item_id,
    )


def _left_pane(user=None):
    return Div(
        Div(
            Div("AH", cls="sidebar-logo-icon"),
            Div(
                Div("Ashland Hill", cls="sidebar-logo-text"),
                Div("Media Finance", cls="sidebar-logo-sub"),
            ),
            cls="sidebar-logo",
        ),
        # Main navigation
        Div(
            Div("Intelligence", cls="sidebar-section-title"),
            _sidebar_item("chat", "AI Chat", "showChat()", item_id="nav-chat", active=True),
            cls="sidebar-section",
        ),
        Div(
            Div("Film Financing OS", cls="sidebar-section-title"),
            _sidebar_item("deals", "Deals", "loadModule('/module/deals', 'Deals')", item_id="nav-deals"),
            _sidebar_item("contacts", "Contacts", "loadModule('/module/contacts', 'Contacts')", item_id="nav-contacts"),
            _sidebar_item("sales", "Sales & Collections", "loadModule('/module/sales', 'Sales & Collections')", item_id="nav-sales"),
            _sidebar_item("credit", "Credit Rating", "loadModule('/module/credit', 'Credit Rating')", item_id="nav-credit"),
            _sidebar_item("accounting", "Accounting", "loadModule('/module/accounting', 'Accounting')", item_id="nav-accounting"),
            _sidebar_item("comms", "Communications", "loadModule('/module/comms', 'Communications')", item_id="nav-comms"),
            cls="sidebar-section",
        ),
        Div(
            Div("AI Tools", cls="sidebar-section-title"),
            _sidebar_item("estimate", "Sales Estimates", "loadModule('/module/estimates', 'Sales Estimates')", item_id="nav-estimates"),
            _sidebar_item("risk", "Risk Scoring", "loadModule('/module/risk', 'Risk Scoring')", item_id="nav-risk"),
            _sidebar_item("budget", "Smart Budget", "loadModule('/module/budget', 'Smart Budget')", item_id="nav-budget"),
            _sidebar_item("schedule", "Scheduling", "loadModule('/module/schedule', 'Scheduling')", item_id="nav-schedule"),
            _sidebar_item("funding", "Soft Funding", "loadModule('/module/funding', 'Soft Funding')", item_id="nav-funding"),
            _sidebar_item("dataroom", "Data Room", "loadModule('/module/dataroom', 'Data Room')", item_id="nav-dataroom"),
            _sidebar_item("audience", "Audience Intel", "loadModule('/module/audience', 'Audience Intel')", item_id="nav-audience"),
            _sidebar_item("talent", "Talent Intel", "loadModule('/module/talent', 'Talent Intel')", item_id="nav-talent"),
            cls="sidebar-section",
        ),
        # Footer with user info
        Div(
            _sidebar_item("logout", user.get("display_name", "User") if user else "Login",
                           f"window.location.href='/logout'" if user else "window.location.href='/login'"),
            cls="sidebar-footer",
        ),
        cls="left-pane",
    )


def _right_pane():
    return Div(
        Div(
            H3("Inspector"),
            Button("X", cls="header-btn", onclick="toggleRightPane()"),
            cls="right-header",
        ),
        Div(
            Button("Trace", cls="right-tab active", onclick="showTab('trace')", **{"data-tab-btn": "trace"}),
            Button("Detail", cls="right-tab", onclick="showTab('detail')", **{"data-tab-btn": "detail"}),
            cls="right-tabs",
        ),
        Div(
            Div(id="trace-content", style="display:block", **{"data-tab": "trace"}),
            Div(id="detail-content", style="display:none", **{"data-tab": "detail"}),
            cls="right-content",
        ),
        cls="right-pane",
    )


# ---------------------------------------------------------------------------
# Auth Routes
# ---------------------------------------------------------------------------

@rt("/login")
def login_page(session):
    if session.get("user_id"):
        return RedirectResponse("/", status_code=303)
    return Titled(
        "AHMF — Login",
        Style(APP_CSS),
        Div(
            H2("Sign In", style="text-align:center; margin-bottom:1.5rem;"),
            Form(
                Input(type="email", name="email", placeholder="Email", required=True),
                Input(type="password", name="password", placeholder="Password", required=True),
                Button("Sign In", type="submit", cls="auth-btn"),
                Div(A("Create account", href="/register"), cls="auth-link"),
                cls="auth-form",
                method="post",
                action="/login",
            ),
            Div(id="auth-error", style="color:#dc2626;text-align:center;font-size:0.8rem;margin-top:0.5rem;"),
            cls="auth-container",
        ),
    )


@rt("/login", methods=["POST"])
def login_submit(email: str, password: str, session):
    from utils.auth import authenticate, create_jwt_token
    user = authenticate(email, password)
    if not user:
        return Titled(
            "AHMF — Login",
            Style(APP_CSS),
            Div(
                H2("Sign In", style="text-align:center; margin-bottom:1.5rem;"),
                Form(
                    Input(type="email", name="email", placeholder="Email", value=email, required=True),
                    Input(type="password", name="password", placeholder="Password", required=True),
                    Button("Sign In", type="submit", cls="auth-btn"),
                    Div(A("Create account", href="/register"), cls="auth-link"),
                    cls="auth-form",
                    method="post",
                    action="/login",
                ),
                Div("Invalid email or password.", style="color:#dc2626;text-align:center;font-size:0.8rem;margin-top:0.5rem;"),
                cls="auth-container",
            ),
        )
    session["user_id"] = user["user_id"]
    session["email"] = user["email"]
    session["display_name"] = user.get("display_name", "")
    return RedirectResponse("/", status_code=303)


@rt("/register")
def register_page(session):
    if session.get("user_id"):
        return RedirectResponse("/", status_code=303)
    return Titled(
        "AHMF — Register",
        Style(APP_CSS),
        Div(
            H2("Create Account", style="text-align:center; margin-bottom:1.5rem;"),
            Form(
                Input(type="text", name="display_name", placeholder="Name", required=True),
                Input(type="email", name="email", placeholder="Email", required=True),
                Input(type="password", name="password", placeholder="Password", required=True, minlength="6"),
                Button("Create Account", type="submit", cls="auth-btn"),
                Div(A("Already have an account? Sign in", href="/login"), cls="auth-link"),
                cls="auth-form",
                method="post",
                action="/register",
            ),
            cls="auth-container",
        ),
    )


@rt("/register", methods=["POST"])
def register_submit(email: str, password: str, display_name: str, session):
    from utils.auth import create_user
    user = create_user(email, password, display_name=display_name)
    if not user:
        return Titled(
            "AHMF — Register",
            Style(APP_CSS),
            Div(
                H2("Create Account", style="text-align:center; margin-bottom:1.5rem;"),
                Form(
                    Input(type="text", name="display_name", placeholder="Name", value=display_name, required=True),
                    Input(type="email", name="email", placeholder="Email", value=email, required=True),
                    Input(type="password", name="password", placeholder="Password", required=True, minlength="6"),
                    Button("Create Account", type="submit", cls="auth-btn"),
                    cls="auth-form",
                    method="post",
                    action="/register",
                ),
                Div("Email already registered.", style="color:#dc2626;text-align:center;font-size:0.8rem;margin-top:0.5rem;"),
                cls="auth-container",
            ),
        )
    session["user_id"] = user["user_id"]
    session["email"] = user["email"]
    session["display_name"] = user.get("display_name", "")
    return RedirectResponse("/", status_code=303)


@rt("/logout")
def logout(session):
    session.clear()
    return RedirectResponse("/login", status_code=303)


# ---------------------------------------------------------------------------
# Module Routes (HTMX partials loaded into center pane)
# ---------------------------------------------------------------------------

@rt("/module/deals")
def module_deals(session):
    from sqlalchemy import text
    from utils.db import get_pool
    try:
        pool = get_pool()
        with pool.get_session() as s:
            stats = s.execute(text("""
                SELECT status, COUNT(*), COALESCE(SUM(loan_amount), 0)
                FROM ahmf.deals GROUP BY status
            """)).fetchall()
            recent = s.execute(text("""
                SELECT deal_id, title, status, loan_amount, borrower_name, genre, created_at
                FROM ahmf.deals ORDER BY created_at DESC LIMIT 10
            """)).fetchall()
        stat_map = {r[0]: (r[1], r[2]) for r in stats}
        total_count = sum(r[1] for r in stats)
        total_amount = sum(r[2] for r in stats)
    except Exception:
        stat_map, total_count, total_amount, recent = {}, 0, 0, []

    deal_cards = []
    for r in recent:
        status_cls = f"status-{r[2]}" if r[2] in ("pipeline", "active", "closed", "declined") else "status-pipeline"
        amt = f"${r[3]:,.0f}" if r[3] else "—"
        deal_cards.append(Div(
            Div(
                Span(r[1], cls="deal-card-title"),
                Span(r[2].title(), cls=f"status-pill {status_cls}"),
                style="display:flex;justify-content:space-between;align-items:center;",
            ),
            Div(f"{r[4] or '—'} | {r[5] or '—'} | {amt}", cls="deal-card-meta"),
            cls="deal-card",
            hx_get=f"/module/deal/{r[0]}",
            hx_target="#center-content",
            hx_swap="innerHTML",
        ))

    return Div(
        H1("Deal Pipeline"),
        Div(
            Div(Div("Total Deals", cls="stat-label"), Div(str(total_count), cls="stat-value"), cls="stat-card"),
            Div(Div("Total Committed", cls="stat-label"), Div(f"${total_amount:,.0f}", cls="stat-value"), cls="stat-card"),
            Div(Div("Pipeline", cls="stat-label"), Div(str(stat_map.get("pipeline", (0,))[0]), cls="stat-value"), cls="stat-card"),
            Div(Div("Active", cls="stat-label"), Div(str(stat_map.get("active", (0,))[0]), cls="stat-value"), cls="stat-card"),
            cls="stats-grid",
        ),
        H2("Recent Deals"),
        Div(*deal_cards) if deal_cards else Div(
            P("No deals yet. Use the chat to create your first deal, or click the button below."),
            Button("+ New Deal", cls="auth-btn", hx_get="/module/deal/new", hx_target="#center-content", hx_swap="innerHTML"),
            style="text-align:center;padding:2rem;",
        ),
        cls="module-content",
    )


@rt("/module/deal/new")
def deal_new_form(session):
    from config.settings import GENRES, PROJECT_TYPES, DEAL_STATUSES, TERRITORIES
    genre_opts = [Option(g, value=g) for g in GENRES]
    type_opts = [Option(t.replace("_", " ").title(), value=t) for t in PROJECT_TYPES]

    return Div(
        H1("New Deal"),
        Form(
            Div(
                Div(Label("Title", Input(type="text", name="title", required=True, placeholder="Project title")), style="flex:1"),
                Div(Label("Status", Select(*[Option(s.title(), value=s) for s in DEAL_STATUSES], name="status")), style="flex:1"),
                style="display:flex;gap:1rem;",
            ),
            Div(
                Div(Label("Project Type", Select(*type_opts, name="project_type")), style="flex:1"),
                Div(Label("Genre", Select(*genre_opts, name="genre")), style="flex:1"),
                style="display:flex;gap:1rem;",
            ),
            Div(
                Div(Label("Loan Amount ($)", Input(type="number", name="loan_amount", placeholder="0")), style="flex:1"),
                Div(Label("Interest Rate (%)", Input(type="number", name="interest_rate", step="0.01", placeholder="0")), style="flex:1"),
                Div(Label("Term (months)", Input(type="number", name="term_months", placeholder="12")), style="flex:1"),
                style="display:flex;gap:1rem;",
            ),
            Div(
                Div(Label("Borrower", Input(type="text", name="borrower_name", placeholder="Borrower name")), style="flex:1"),
                Div(Label("Budget ($)", Input(type="number", name="budget", placeholder="0")), style="flex:1"),
                style="display:flex;gap:1rem;",
            ),
            Div(
                Div(Label("Producer", Input(type="text", name="producer", placeholder="Producer name")), style="flex:1"),
                Div(Label("Director", Input(type="text", name="director", placeholder="Director name")), style="flex:1"),
                style="display:flex;gap:1rem;",
            ),
            Label("Cast", Input(type="text", name="cast_summary", placeholder="Key cast members")),
            Label("Territory", Input(type="text", name="territory", placeholder="e.g. Domestic, International")),
            Div(
                Button("Create Deal", type="submit", cls="auth-btn"),
                A("Cancel", href="#", onclick="loadModule('/module/deals', 'Deals')", style="margin-left:1rem;color:#64748b;"),
                style="margin-top:1rem;",
            ),
            cls="auth-form",
            method="post",
            hx_post="/module/deal/create",
            hx_target="#center-content",
            hx_swap="innerHTML",
        ),
        cls="module-content",
    )


@rt("/module/deal/create", methods=["POST"])
def deal_create(session, title: str, status: str = "pipeline", project_type: str = "feature_film",
                genre: str = "", loan_amount: float = 0, interest_rate: float = 0,
                term_months: int = 12, borrower_name: str = "", budget: float = 0,
                producer: str = "", director: str = "", cast_summary: str = "", territory: str = ""):
    from sqlalchemy import text
    from utils.db import get_pool
    user_id = session.get("user_id")
    pool = get_pool()
    with pool.get_session() as s:
        s.execute(text("""
            INSERT INTO ahmf.deals (title, status, project_type, genre, loan_amount, interest_rate,
                term_months, borrower_name, budget, producer, director, cast_summary, territory, created_by)
            VALUES (:title, :status, :type, :genre, :amount, :rate, :term, :borrower, :budget,
                :producer, :director, :cast, :territory, :uid)
        """), {
            "title": title, "status": status, "type": project_type, "genre": genre,
            "amount": loan_amount or None, "rate": interest_rate or None, "term": term_months,
            "borrower": borrower_name, "budget": budget or None,
            "producer": producer, "director": director, "cast": cast_summary,
            "territory": territory, "uid": user_id,
        })
    return module_deals(session)


@rt("/module/contacts")
def module_contacts(session):
    from sqlalchemy import text
    from utils.db import get_pool
    try:
        pool = get_pool()
        with pool.get_session() as s:
            contacts = s.execute(text("""
                SELECT contact_id, name, company, contact_type, email, phone
                FROM ahmf.contacts ORDER BY name LIMIT 50
            """)).fetchall()
    except Exception:
        contacts = []

    rows = []
    for c in contacts:
        rows.append(Tr(
            Td(c[1]), Td(c[2] or "—"), Td(c[3]), Td(c[4] or "—"), Td(c[5] or "—"),
        ))

    return Div(
        Div(
            H1("Contacts"),
            Button("+ Add Contact", cls="auth-btn", hx_get="/module/contact/new", hx_target="#center-content", hx_swap="innerHTML"),
            style="display:flex;justify-content:space-between;align-items:center;",
        ),
        Table(
            Thead(Tr(Th("Name"), Th("Company"), Th("Type"), Th("Email"), Th("Phone"))),
            Tbody(*rows) if rows else Tbody(Tr(Td("No contacts yet.", colspan="5", style="text-align:center;padding:2rem;color:#64748b;"))),
            style="width:100%;border-collapse:collapse;margin-top:1rem;",
        ) if True else "",
        cls="module-content",
    )


@rt("/module/contact/new")
def contact_new_form(session):
    from config.settings import CONTACT_TYPES
    type_opts = [Option(t.replace("_", " ").title(), value=t) for t in CONTACT_TYPES]
    return Div(
        H1("New Contact"),
        Form(
            Div(
                Div(Label("Name", Input(type="text", name="name", required=True)), style="flex:1"),
                Div(Label("Company", Input(type="text", name="company")), style="flex:1"),
                style="display:flex;gap:1rem;",
            ),
            Div(
                Div(Label("Type", Select(*type_opts, name="contact_type")), style="flex:1"),
                Div(Label("Email", Input(type="email", name="email")), style="flex:1"),
                Div(Label("Phone", Input(type="text", name="phone")), style="flex:1"),
                style="display:flex;gap:1rem;",
            ),
            Label("Notes", Textarea(name="notes", rows="3", style="width:100%;padding:0.5rem;border:1px solid #e2e8f0;border-radius:8px;font-family:inherit;")),
            Button("Create Contact", type="submit", cls="auth-btn"),
            cls="auth-form",
            hx_post="/module/contact/create",
            hx_target="#center-content",
            hx_swap="innerHTML",
        ),
        cls="module-content",
    )


@rt("/module/contact/create", methods=["POST"])
def contact_create(session, name: str, company: str = "", contact_type: str = "other",
                   email: str = "", phone: str = "", notes: str = ""):
    from sqlalchemy import text
    from utils.db import get_pool
    user_id = session.get("user_id")
    pool = get_pool()
    with pool.get_session() as s:
        s.execute(text("""
            INSERT INTO ahmf.contacts (name, company, contact_type, email, phone, notes, created_by)
            VALUES (:name, :company, :type, :email, :phone, :notes, :uid)
        """), {"name": name, "company": company, "type": contact_type, "email": email,
               "phone": phone, "notes": notes, "uid": user_id})
    return module_contacts(session)


# Scaffold module routes for Sales, Credit, Accounting, Comms
@rt("/module/sales")
def module_sales(session):
    return _scaffold_page("Sales & Collections",
        "Revenue tracking and collateral monitoring engine.",
        ["Territory-Based Sales Mapping", "Distributor Integration", "Collection Management & Alerts",
         "Variance Analysis (Projected vs Actual)", "Receivable Tracking & Delay Flagging"])

@rt("/module/credit")
def module_credit(session):
    return _scaffold_page("Credit Rating",
        "Counterparty strength assessment layer.",
        ["Automated Distributor & Producer Scoring", "Payment Reliability Tracking",
         "Risk Assessment Metrics", "Custom Rating Frameworks"])

@rt("/module/accounting")
def module_accounting(session):
    return _scaffold_page("Accounting",
        "Transaction-level financial integrity.",
        ["Multi-Account Balance Tracking", "Payment Evidence & Audit Trail",
         "FX & Currency Management", "Automated Reconciliation"])

@rt("/module/comms")
def module_comms(session):
    return _scaffold_page("Communications",
        "Execution control layer.",
        ["Integrated Messaging", "Task Assignment & Deadline Tracking",
         "Version-Controlled Notes", "Milestone & Payment Notifications"])

@rt("/module/estimates")
def module_estimates(session):
    return Div(
        H1("Sales Estimates Generator"),
        P("Upload a script or project package to receive projected MGs, box office forecasts, "
          "and ancillary revenue models benchmarked against comparable films.", style="color:#64748b;margin-bottom:1.5rem;"),
        Div(
            Div(Div("Estimates Generated", cls="stat-label"), Div("0", cls="stat-value"), cls="stat-card"),
            Div(Div("Avg Confidence", cls="stat-label"), Div("—", cls="stat-value"), cls="stat-card"),
            cls="stats-grid",
        ),
        P("Use the AI chat to generate estimates:", style="margin-top:1rem;color:#475569;"),
        P("Try: ", Code("estimate:new"), " or ask: ", Em("'Estimate revenue for a $15M horror film with Florence Pugh'"),
          style="font-size:0.85rem;color:#64748b;"),
        Button("Generate New Estimate", cls="auth-btn", onclick="showChat();var ta=document.getElementById('chat-input');if(ta)ta.value='estimate:new';",
               style="margin-top:1rem;"),
        cls="module-content",
    )


# ---------------------------------------------------------------------------
# Register Product Module Routes (3-9)
# ---------------------------------------------------------------------------

from modules.risk import register_routes as risk_routes
from modules.budget import register_routes as budget_routes
from modules.schedule import register_routes as schedule_routes
from modules.funding import register_routes as funding_routes
from modules.dataroom import register_routes as dataroom_routes
from modules.audience import register_routes as audience_routes
from modules.talent import register_routes as talent_routes

risk_routes(rt)
budget_routes(rt)
schedule_routes(rt)
funding_routes(rt)
dataroom_routes(rt)
audience_routes(rt)
talent_routes(rt)


# ---------------------------------------------------------------------------
# Main Page
# ---------------------------------------------------------------------------

@rt("/")
def index(session):
    if not session.get("user_id"):
        return RedirectResponse("/login", status_code=303)

    user = {
        "user_id": session.get("user_id"),
        "email": session.get("email"),
        "display_name": session.get("display_name", "User"),
    }
    thread_id = session.get("thread_id")
    if not thread_id:
        thread_id = str(_uuid.uuid4())
        session["thread_id"] = thread_id

    return (
        Title("AHMF — Ashland Hill Media Finance"),
        Style(APP_CSS),
        Div(
            _left_pane(user),
            Div(
                Div(
                    H2("AI Chat", id="center-title"),
                    Button("Inspector", cls="header-btn", onclick="toggleRightPane()"),
                    cls="center-header",
                ),
                Div(id="center-content", cls="module-content", style="display:none;overflow-y:auto;flex:1;"),
                Div(agui.chat(thread_id), cls="center-chat", id="center-chat"),
                cls="center-pane",
            ),
            _right_pane(),
            cls="app-layout",
        ),
        Script(LAYOUT_JS),
    )


# ---------------------------------------------------------------------------
# Serve
# ---------------------------------------------------------------------------

serve(host="0.0.0.0", port=5010)
