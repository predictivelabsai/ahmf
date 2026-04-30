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
import json
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
    "You are Monika, the AI assistant for Ashland Hill Media Finance — a film financing company. "
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
from modules.sales import search_sales_contracts
from modules.credit import get_credit_rating
from modules.accounting import search_transactions
from modules.comms import search_messages

TOOLS = [
    search_deals, get_deal_detail, get_portfolio_overview, search_contacts,
    search_movies, get_movie_details,
    analyze_production_risk, generate_budget_tool, generate_schedule_tool,
    search_incentives_tool, generate_closing_checklist_tool,
    analyze_audience_tool, search_talent_tool, analyze_talent_tool,
    search_sales_contracts, get_credit_rating, search_transactions, search_messages,
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
            "| `sales:list` | List sales contracts |\n"
            "| `credit:CONTACT` | Look up credit rating |\n"
            "| `transactions` | View transaction ledger |\n"
            "| `messages` | View messages & tasks |\n"
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
    if first == "sales:list" or first == "sales":
        return search_sales_contracts(rest)
    if first.startswith("credit:") and len(first) > 7:
        return get_credit_rating(first[7:])
    if first == "transactions" or first == "txns":
        return search_transactions(rest)
    if first == "messages" or first == "tasks":
        return search_messages(rest)

    return None


# ---------------------------------------------------------------------------
# FastHTML App
# ---------------------------------------------------------------------------

from utils.clerk import is_clerk_enabled, get_publishable_key, get_frontend_api

_hdrs = [
    Script(src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"),
    Script(src="https://cdn.plot.ly/plotly-2.32.0.min.js"),
]

if is_clerk_enabled():
    _fapi = get_frontend_api()
    _pk = get_publishable_key()
    _hdrs.extend([
        Script(src=f"https://{_fapi}/npm/@clerk/ui@1/dist/ui.browser.js",
               crossorigin="anonymous", defer=True),
        Script(src=f"https://{_fapi}/npm/@clerk/clerk-js@6/dist/clerk.browser.js",
               crossorigin="anonymous", defer=True, data_clerk_publishable_key=_pk),
    ])

app, rt = fast_app(
    exts="ws",
    secret_key=os.getenv("JWT_SECRET", "ahmf-dev-secret"),
    hdrs=tuple(_hdrs),
)

from utils.agui import setup_agui, get_chat_styles, StreamingCommand, list_conversations

agui = setup_agui(app, langgraph_agent, command_interceptor=_command_interceptor)


@rt("/api/health")
def health_check():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Layout CSS
# ---------------------------------------------------------------------------

APP_CSS = ""  # CSS now in static/app.css

LAYOUT_JS = ""  # JS now in static/chat.js


# ---------------------------------------------------------------------------
# Sidebar icons (SVG)
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Layout Components
# ---------------------------------------------------------------------------

def _left_pane(user=None):
    display = user.get("display_name", "User") if user else None
    user_email = user.get("email", "") if user else None
    initials = (display[0].upper() if display else "U")

    nav = [
        ("home",       "Home",                     "/module/home",       "⌂"),
        ("deals",      "Deals",                    "/module/deals",      "◇"),
        ("sales",      "Sales & Collections",      "/module/sales",      "□"),
        ("accounting", "Accounting & Transactions", "/module/accounting", "◈"),
        ("contacts",   "Contacts",                 "/module/contacts",   "◎"),
        ("tasks",      "Tasks",                    "/module/comms",      "☑"),
        ("reporting",  "Reporting",                "/module/reporting",  "▥"),
    ]
    nav_links = [
        A(
            Span(icon, cls="nav-icon"),
            Span(label, cls="nav-label"),
            href="#",
            onclick=f"loadModule('{path}', '{label}')",
            cls=f"nav-item{'active' if item_id == 'home' else ''}",
            id=f"nav-{item_id}",
        )
        for item_id, label, path, icon in nav
    ]

    ai_link = A(
        Span("◐", cls="nav-icon"),
        Span("AI Assistant", cls="nav-label"),
        href="#",
        onclick="showChat()",
        cls="nav-item",
        id="nav-chat",
    )

    user_block = (
        Div(
            Div(
                Div(initials, cls="user-avatar"),
                Div(
                    Div(display or "User", cls="user-name"),
                    Div(user_email or "", cls="user-email-text"),
                ),
                cls="user-profile",
            ),
            Div(
                A("Settings", href="#", onclick="loadModule('/module/guide','User Guide')", cls="footer-link"),
                A("Help Center", href="#", onclick="loadModule('/module/guide','User Guide')", cls="footer-link"),
                cls="footer-links",
            ),
            A("Sign out", href="/logout", cls="footer-link signout"),
        )
        if user else
        Button("Sign in", onclick="window.location.href='/login'", cls="auth-btn", style="width:100%;")
    )

    return Div(
        Div(
            A(Span("▲■", cls="logo-mark"), href="/", cls="logo-link"),
            cls="sidebar-logo",
        ),
        Div(
            *nav_links,
            ai_link,
            cls="sidebar-nav",
        ),
        Div(
            Div("FAVORITE DEALS", cls="sidebar-section-title"),
            Div(id="favorite-deals", hx_get="/api/favorite-deals", hx_trigger="load", hx_swap="innerHTML"),
            cls="sidebar-section",
        ),
        Div(
            Div("FOLDERS", cls="sidebar-section-title"),
            A("📁 LSA", href="#", cls="folder-link"),
            A("📁 Budget Sheets", href="#", cls="folder-link"),
            cls="sidebar-section",
        ),
        Div(user_block, cls="sidebar-footer"),
        cls="left-pane",
    )


def _right_pane():
    """Right pane: Documents (chat mode) or AI Copilot (module mode)."""
    return Div(
        Div(
            Span("AI Copilot", id="right-pane-title", cls="right-pane-title"),
            Div(
                Button("New", cls="copilot-new-btn", onclick="clearCopilot()",
                       title="Start new conversation"),
                Button("✕", cls="right-close-btn", onclick="toggleRightPane()"),
                cls="right-header-actions",
            ),
            cls="right-header",
        ),
        # Mode A: Documents — shown when main AI chat is active
        Div(
            Div("Artifacts from your AI conversation will appear here.",
                cls="right-empty-state", id="documents-empty"),
            id="right-documents",
            cls="right-body",
            style="display:none;",
        ),
        # Mode B: AI Copilot — shown when a module page is active
        Div(
            Div(
                Div(id="copilot-welcome",
                    hx_get="/api/copilot/welcome/home",
                    hx_trigger="load", hx_swap="innerHTML"),
                id="copilot-messages", cls="copilot-messages",
            ),
            Div(
                Div(NotStr("<span class='copilot-dots'><span>.</span><span>.</span><span>.</span></span>"),
                    cls="copilot-thinking-bubble"),
                id="copilot-thinking", cls="htmx-indicator",
                style="padding: 0 14px 8px;",
            ),
            Div(
                Form(
                    Div(
                        Input(type="text", name="msg", id="copilot-input",
                              placeholder="Ask about this data...",
                              autocomplete="off", cls="copilot-input"),
                        Hidden(name="module_id", id="copilot-module-id", value="home"),
                        Button(NotStr("&#10148;"), type="submit",
                               cls="copilot-send-icon", title="Send"),
                        cls="copilot-input-wrap",
                    ),
                    id="copilot-form",
                    hx_post="/api/copilot/query",
                    hx_target="#copilot-messages",
                    hx_swap="beforeend",
                    hx_indicator="#copilot-thinking",
                ),
                Div(id="copilot-hint", cls="copilot-hint",
                    hx_get="/api/copilot/hints/home",
                    hx_trigger="load", hx_swap="innerHTML"),
                cls="copilot-input-area",
            ),
            id="right-copilot",
            cls="right-body",
        ),
        # Trace content target for main chat OOB swaps
        Div(id="trace-content", style="display:none;"),
        id="right-pane",
        cls="right-pane",
    )


# ---------------------------------------------------------------------------
# Copilot API Routes
# ---------------------------------------------------------------------------

@rt("/api/copilot/welcome/{module_id}")
def copilot_welcome(module_id: str):
    from agents.copilot import COPILOT_SHORTCUTS
    shortcuts = COPILOT_SHORTCUTS.get(module_id, COPILOT_SHORTCUTS.get("home", []))
    chips = []
    for label, desc in shortcuts:
        safe = label.replace("'", "\\'")
        chips.append(
            Span(label, cls="copilot-chip", title=desc,
                 onclick=f"insertCopilotCmd('{safe}')"))
    return Div(
        Div("Hi! I can query your data. Ask a question or try:", Br(), *chips,
            cls="copilot-msg copilot-system"),
        id="copilot-welcome",
    )


@rt("/api/copilot/hints/{module_id}")
def copilot_hints(module_id: str):
    from agents.copilot import COPILOT_SHORTCUTS
    shortcuts = COPILOT_SHORTCUTS.get(module_id, COPILOT_SHORTCUTS.get("home", []))
    codes = " ".join(f"<code>{label}</code>" for label, _ in shortcuts[:4])
    return NotStr(f"Try: {codes}")


@rt("/api/copilot/query", methods=["POST"])
async def copilot_query_endpoint(msg: str, module_id: str = "home", session=None):
    from agents.copilot import copilot_query
    import html as _html

    user_bubble = Div(
        Div(_html.escape(msg), cls="copilot-msg copilot-user"),
    )

    try:
        result = await copilot_query(msg, module_id)
    except Exception as e:
        result = f"Error: {str(e)[:200]}"

    asst_bubble = Div(
        Div(NotStr(result), cls="copilot-msg copilot-assistant"),
    )

    clear_and_scroll = Script(
        "document.getElementById('copilot-input').value='';"
        "var cm=document.getElementById('copilot-messages');if(cm)cm.scrollTop=cm.scrollHeight;"
    )

    return Div(user_bubble, asst_bubble, clear_and_scroll)


# ---------------------------------------------------------------------------
# Notification Helper
# ---------------------------------------------------------------------------

def _create_notification(pool, deal_id, subject, body, user_id):
    """Insert a notification message into ahmf.messages."""
    from sqlalchemy import text
    with pool.get_session() as s:
        s.execute(text("""
            INSERT INTO ahmf.messages (deal_id, from_user, subject, body, message_type, status)
            VALUES (:did, :uid, :subj, :body, 'notification', 'open')
        """), {"did": deal_id, "uid": user_id, "subj": subject, "body": body})


# ---------------------------------------------------------------------------
# CSV Export APIs
# ---------------------------------------------------------------------------

@rt("/api/export/deals")
def export_deals(session):
    import csv, io
    from sqlalchemy import text
    from utils.db import get_pool
    from starlette.responses import Response
    pool = get_pool()
    with pool.get_session() as s:
        rows = s.execute(text("""
            SELECT deal_id, title, project_type, genre, status, loan_amount, currency,
                   interest_rate, term_months, borrower_name, producer, director,
                   budget, territory, origination_date, maturity_date
            FROM ahmf.deals ORDER BY created_at DESC
        """)).fetchall()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Deal ID", "Title", "Type", "Genre", "Status", "Loan Amount", "Currency",
                     "Interest Rate", "Term (months)", "Borrower", "Producer", "Director",
                     "Budget", "Territory", "Origination Date", "Maturity Date"])
    for r in rows:
        writer.writerow(list(r))
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=deals_export.csv"})


@rt("/api/export/transactions")
def export_transactions(session):
    import csv, io
    from sqlalchemy import text
    from utils.db import get_pool
    from starlette.responses import Response
    pool = get_pool()
    with pool.get_session() as s:
        rows = s.execute(text("""
            SELECT t.txn_id, d.title AS deal, t.txn_type, t.amount, t.currency,
                   c.name AS counterparty, t.reference, t.posted_date
            FROM ahmf.transactions t
            LEFT JOIN ahmf.deals d ON d.deal_id = t.deal_id
            LEFT JOIN ahmf.contacts c ON c.contact_id = t.counterparty_id
            ORDER BY t.posted_date DESC
        """)).fetchall()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Txn ID", "Deal", "Type", "Amount", "Currency", "Counterparty", "Reference", "Date"])
    for r in rows:
        writer.writerow(list(r))
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=transactions_export.csv"})


@rt("/api/export/contacts")
def export_contacts(session):
    import csv, io
    from sqlalchemy import text
    from utils.db import get_pool
    from starlette.responses import Response
    pool = get_pool()
    with pool.get_session() as s:
        rows = s.execute(text("""
            SELECT c.contact_id, c.name, c.company, c.contact_type, c.email, c.phone,
                   c.credit_score, cr.risk_tier
            FROM ahmf.contacts c
            LEFT JOIN ahmf.credit_ratings cr ON c.contact_id = cr.contact_id
            ORDER BY c.name
        """)).fetchall()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Contact ID", "Name", "Company", "Type", "Email", "Phone", "Credit Score", "Risk Tier"])
    for r in rows:
        writer.writerow(list(r))
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=contacts_export.csv"})


@rt("/api/import/contacts", methods=["POST"])
async def import_contacts(session, request):
    import csv, io
    from sqlalchemy import text
    from utils.db import get_pool
    form = await request.form()
    upload = form.get("file")
    if not upload:
        return Div(P("No file uploaded.", style="color:#dc2626;"), cls="module-content")
    content = (await upload.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))
    pool = get_pool()
    imported = 0
    skipped = 0
    with pool.get_session() as s:
        for row in reader:
            name = row.get("Name") or row.get("name") or ""
            if not name.strip():
                skipped += 1
                continue
            existing = s.execute(text("SELECT 1 FROM ahmf.contacts WHERE name = :n"), {"n": name.strip()}).fetchone()
            if existing:
                skipped += 1
                continue
            s.execute(text("""
                INSERT INTO ahmf.contacts (name, company, contact_type, email, phone, created_by)
                VALUES (:name, :company, :type, :email, :phone, :uid)
            """), {
                "name": name.strip(),
                "company": (row.get("Company") or row.get("company") or "").strip(),
                "type": (row.get("Type") or row.get("contact_type") or "other").strip().lower(),
                "email": (row.get("Email") or row.get("email") or "").strip(),
                "phone": (row.get("Phone") or row.get("phone") or "").strip(),
                "uid": session.get("user_id"),
            })
            imported += 1
    return module_contacts(session, import_msg=f"Imported {imported} contacts ({skipped} skipped)")


# ---------------------------------------------------------------------------
# Clerk session bridge
# ---------------------------------------------------------------------------

def _check_clerk_session(request, session):
    """Check for Clerk __session cookie and sync to FastHTML session."""
    if not is_clerk_enabled():
        return session.get("user_id")
    if session.get("user_id"):
        return session.get("user_id")

    token = request.cookies.get("__session") or ""
    if not token:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        return None

    from utils.clerk import verify_clerk_token, get_clerk_user
    payload = verify_clerk_token(token)
    if not payload:
        return None

    clerk_user_id = payload.get("sub")
    if not clerk_user_id:
        return None

    clerk_user = get_clerk_user(clerk_user_id)
    if not clerk_user or not clerk_user.get("email"):
        return None

    from utils.auth import get_user_by_email, create_user
    email = clerk_user["email"]
    existing = get_user_by_email(email)
    if not existing:
        existing = create_user(email, password="clerk-managed",
                               display_name=clerk_user["display_name"])
    if not existing:
        return None

    session["user_id"] = existing["user_id"]
    session["email"] = existing["email"]
    session["display_name"] = existing.get("display_name", "")
    return session["user_id"]


# ---------------------------------------------------------------------------
# Auth Routes
# ---------------------------------------------------------------------------

@rt("/login", methods=["GET"])
def login_page(request, session):
    if session.get("user_id"):
        return RedirectResponse("/", status_code=303)
    if is_clerk_enabled():
        _check_clerk_session(request, session)
        if session.get("user_id"):
            return RedirectResponse("/", status_code=303)
        return Titled(
            "Monika — Sign In",
            Link(rel="stylesheet", href="/static/app.css?v=3"),
            Div(
                Div(id="clerk-signin", style="min-height:400px;display:flex;justify-content:center;"),
                Script("""
                    window.addEventListener('load', async function() {
                        await Clerk.load({ ui: { ClerkUI: window.__internal_ClerkUICtor } });
                        if (Clerk.user) { window.location.href = '/'; return; }
                        Clerk.mountSignIn(document.getElementById('clerk-signin'), {
                            afterSignInUrl: '/',
                            afterSignUpUrl: '/',
                        });
                    });
                """),
                cls="auth-container",
            ),
        )
    return Titled(
        "Monika — Login",
        Link(rel="stylesheet", href="/static/app.css?v=3"),
        Div(
            H2("Sign In", style="text-align:center; margin-bottom:1.5rem;"),
            Form(
                Input(type="email", name="email", placeholder="Email", required=True),
                Input(type="password", name="password", placeholder="Password", required=True),
                Button("Sign In", type="submit", cls="auth-btn"),
                Div(
                    A("Forgot password?", href="/forgot-password"),
                    style="text-align:right;margin-top:0.25rem;",
                ),
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
            "Monika — Login",
            Link(rel="stylesheet", href="/static/app.css?v=3"),
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


@rt("/register", methods=["GET"])
def register_page(request, session):
    if session.get("user_id"):
        return RedirectResponse("/", status_code=303)
    if is_clerk_enabled():
        _check_clerk_session(request, session)
        if session.get("user_id"):
            return RedirectResponse("/", status_code=303)
        return Titled(
            "Monika — Create Account",
            Link(rel="stylesheet", href="/static/app.css?v=3"),
            Div(
                Div(id="clerk-signup", style="min-height:400px;display:flex;justify-content:center;"),
                Script("""
                    window.addEventListener('load', async function() {
                        await Clerk.load({ ui: { ClerkUI: window.__internal_ClerkUICtor } });
                        if (Clerk.user) { window.location.href = '/'; return; }
                        Clerk.mountSignUp(document.getElementById('clerk-signup'), {
                            afterSignInUrl: '/',
                            afterSignUpUrl: '/',
                        });
                    });
                """),
                cls="auth-container",
            ),
        )
    return Titled(
        "Monika — Register",
        Link(rel="stylesheet", href="/static/app.css?v=3"),
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
            "Monika — Register",
            Link(rel="stylesheet", href="/static/app.css?v=3"),
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
    if is_clerk_enabled():
        return Titled(
            "Logging out…",
            Link(rel="stylesheet", href="/static/app.css?v=3"),
            Script("""
                window.addEventListener('load', async function() {
                    await Clerk.load({ ui: { ClerkUI: window.__internal_ClerkUICtor } });
                    await Clerk.signOut();
                    window.location.href = '/login';
                });
            """),
        )
    return RedirectResponse("/login", status_code=303)


@rt("/forgot-password", methods=["GET"])
def forgot_password_page():
    if is_clerk_enabled():
        return RedirectResponse("/login", status_code=303)
    return Titled(
        "Monika — Reset Password",
        Link(rel="stylesheet", href="/static/app.css?v=3"),
        Div(
            H2("Reset Password", style="text-align:center; margin-bottom:1.5rem;"),
            Form(
                Input(type="email", name="email", placeholder="Email", required=True),
                Button("Send Reset Link", type="submit", cls="auth-btn"),
                Div(A("Back to sign in", href="/login"), cls="auth-link"),
                cls="auth-form",
                method="post",
                action="/forgot-password",
            ),
            cls="auth-container",
        ),
    )


@rt("/forgot-password", methods=["POST"])
def forgot_password_submit(email: str):
    from utils.auth import get_user_by_email, create_password_reset_token
    user = get_user_by_email(email)
    msg = "If an account exists with that email, a reset link has been generated."
    if user:
        token = create_password_reset_token(user["user_id"])
        logger.info(f"Password reset token for {email}: /reset-password?token={token}")
    return Titled(
        "Monika — Reset Password",
        Link(rel="stylesheet", href="/static/app.css?v=3"),
        Div(
            H2("Check Your Email", style="text-align:center; margin-bottom:1.5rem;"),
            P(msg, style="text-align:center;font-size:0.85rem;color:#64748b;max-width:320px;margin:0 auto 1rem;"),
            Div(A("Back to sign in", href="/login"), cls="auth-link"),
            cls="auth-container",
        ),
    )


@rt("/reset-password", methods=["GET"])
def reset_password_page(token: str = ""):
    if not token:
        return RedirectResponse("/login", status_code=303)
    return Titled(
        "Monika — New Password",
        Link(rel="stylesheet", href="/static/app.css?v=3"),
        Div(
            H2("Set New Password", style="text-align:center; margin-bottom:1.5rem;"),
            Form(
                Hidden(name="token", value=token),
                Input(type="password", name="password", placeholder="New password", required=True, minlength="6"),
                Input(type="password", name="password_confirm", placeholder="Confirm password", required=True, minlength="6"),
                Button("Reset Password", type="submit", cls="auth-btn"),
                cls="auth-form",
                method="post",
                action="/reset-password",
            ),
            cls="auth-container",
        ),
    )


@rt("/reset-password", methods=["POST"])
def reset_password_submit(token: str, password: str, password_confirm: str):
    if password != password_confirm:
        return Titled(
            "Monika — New Password",
            Link(rel="stylesheet", href="/static/app.css?v=3"),
            Div(
                H2("Set New Password", style="text-align:center; margin-bottom:1.5rem;"),
                Form(
                    Hidden(name="token", value=token),
                    Input(type="password", name="password", placeholder="New password", required=True, minlength="6"),
                    Input(type="password", name="password_confirm", placeholder="Confirm password", required=True, minlength="6"),
                    Button("Reset Password", type="submit", cls="auth-btn"),
                    cls="auth-form",
                    method="post",
                    action="/reset-password",
                ),
                Div("Passwords do not match.", style="color:#dc2626;text-align:center;font-size:0.8rem;margin-top:0.5rem;"),
                cls="auth-container",
            ),
        )
    from utils.auth import reset_password_with_token
    if reset_password_with_token(token, password):
        return Titled(
            "Monika — Password Reset",
            Link(rel="stylesheet", href="/static/app.css?v=3"),
            Div(
                H2("Password Reset", style="text-align:center; margin-bottom:1.5rem;"),
                P("Your password has been updated.", style="text-align:center;font-size:0.85rem;color:#64748b;"),
                Div(A("Sign in", href="/login"), cls="auth-link"),
                cls="auth-container",
            ),
        )
    return Titled(
        "Monika — Error",
        Link(rel="stylesheet", href="/static/app.css?v=3"),
        Div(
            H2("Invalid or Expired Link", style="text-align:center; margin-bottom:1.5rem;"),
            P("This reset link is invalid or has expired.", style="text-align:center;font-size:0.85rem;color:#dc2626;"),
            Div(A("Request a new link", href="/forgot-password"), cls="auth-link"),
            cls="auth-container",
        ),
    )


# ---------------------------------------------------------------------------
# Module Routes (HTMX partials loaded into center pane)
# ---------------------------------------------------------------------------

STATUS_COLORS = {
    "pipeline": "#D6AE6E", "active": "#4A8E66", "approved": "#2F7151",
    "funded": "#1F5D43", "closed": "#6B4E2F", "declined": "#9C8F7A",
    "pre-production": "#3B82F6", "production": "#22C55E",
}

GENRE_GRADIENTS = {
    "drama":    "linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)",
    "action":   "linear-gradient(135deg, #2d1b00 0%, #8B4513 50%, #D2691E 100%)",
    "horror":   "linear-gradient(135deg, #1a0000 0%, #3d0000 50%, #5c0000 100%)",
    "comedy":   "linear-gradient(135deg, #1a2a1a 0%, #2d5a2d 50%, #3d7a3d 100%)",
    "sci-fi":   "linear-gradient(135deg, #0a0a2e 0%, #1a1a4e 50%, #2a2a6e 100%)",
    "thriller": "linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 50%, #3a3a3a 100%)",
    "default":  "linear-gradient(135deg, #1e293b 0%, #334155 50%, #475569 100%)",
}


def _deal_poster_card(deal):
    title = deal[1]
    status = deal[2] or "pipeline"
    amount = deal[3]
    borrower = deal[4] or "—"
    genre = (deal[5] or "").lower()
    amt_str = f"${float(amount):,.0f}" if amount else "—"
    gradient = GENRE_GRADIENTS.get(genre, GENRE_GRADIENTS["default"])
    status_color = STATUS_COLORS.get(status, "#CFC8B4")
    status_label = status.replace("_", " ").title()

    return Div(
        Div(
            Span(status_label, cls="poster-status", style=f"background:{status_color}"),
            Div(title[0] if title else "?", cls="poster-initial"),
            cls="poster-image",
            style=f"background:{gradient}",
        ),
        Div(
            Div(
                Span(title, cls="poster-title"),
                cls="poster-title-row",
            ),
            Div(borrower, cls="poster-prodco"),
            Div(f"Net Loan: {amt_str}", cls="poster-loan"),
            cls="poster-info",
        ),
        cls="deal-poster-card",
        hx_get=f"/module/deal/{deal[0]}",
        hx_target="#center-content",
        hx_swap="innerHTML",
    )


@rt("/api/favorite-deals")
def api_favorite_deals(session):
    from sqlalchemy import text
    from utils.db import get_pool
    try:
        pool = get_pool()
        with pool.get_session() as s:
            rows = s.execute(text("""
                SELECT deal_id, title FROM ahmf.deals
                WHERE status IN ('active','funded','pipeline')
                ORDER BY created_at DESC LIMIT 5
            """)).fetchall()
    except Exception:
        rows = []
    if not rows:
        return Span("No deals yet", style="font-size:.72rem;color:var(--ink-dim);padding:.4rem;")
    links = [
        A(f"⭐ {r[1]}", href="#",
          onclick=f"loadModule('/module/deal/{r[0]}','Deal: {r[1]}')",
          cls="favorite-deal-link")
        for r in rows
    ]
    return Div(*links)


@rt("/module/home")
def module_home(session):
    from sqlalchemy import text
    from utils.db import get_pool
    display = session.get("display_name", "User")
    import datetime
    hour = datetime.datetime.now().hour
    greeting = "Good morning" if hour < 12 else ("Good afternoon" if hour < 17 else "Good evening")

    deals_count = 0
    total_loan = 0
    avg_rate = 0
    tasks_due = 0
    tasks_overdue = 0
    deals = []
    messages = []
    notifications = []
    status_breakdown = []
    active_count = 0
    active_loan = 0
    pipeline_count = 0
    pipeline_loan = 0
    total_collected = 0
    total_mg = 0

    try:
        pool = get_pool()
        with pool.get_session() as s:
            stats = s.execute(text("""
                SELECT COUNT(*), COALESCE(SUM(loan_amount),0), COALESCE(AVG(interest_rate),0)
                FROM ahmf.deals
            """)).fetchone()
            deals_count = stats[0]
            total_loan = float(stats[1])
            avg_rate = float(stats[2])

            active_stats = s.execute(text("""
                SELECT COUNT(*), COALESCE(SUM(loan_amount),0)
                FROM ahmf.deals WHERE status = 'active'
            """)).fetchone()
            active_count = active_stats[0]
            active_loan = float(active_stats[1])

            pipeline_stats = s.execute(text("""
                SELECT COUNT(*), COALESCE(SUM(loan_amount),0)
                FROM ahmf.deals WHERE status = 'pipeline'
            """)).fetchone()
            pipeline_count = pipeline_stats[0]
            pipeline_loan = float(pipeline_stats[1])

            coll_stats = s.execute(text("""
                SELECT COALESCE(SUM(amount_received), 0), COALESCE(SUM(mg_amount), 0)
                FROM ahmf.collections c
                JOIN ahmf.sales_contracts sc ON sc.contract_id = c.contract_id
            """)).fetchone()
            total_collected = float(coll_stats[0])
            total_mg = float(coll_stats[1])

            tasks_row = s.execute(text("""
                SELECT
                    COUNT(*) FILTER (WHERE due_date >= CURRENT_DATE AND status='open'),
                    COUNT(*) FILTER (WHERE due_date < CURRENT_DATE AND status='open')
                FROM ahmf.messages WHERE message_type='task'
            """)).fetchone()
            tasks_due = tasks_row[0] if tasks_row else 0
            tasks_overdue = tasks_row[1] if tasks_row else 0

            deals = s.execute(text("""
                SELECT deal_id, title, status, loan_amount, borrower_name, genre
                FROM ahmf.deals ORDER BY created_at DESC LIMIT 10
            """)).fetchall()

            messages = s.execute(text("""
                SELECT subject, due_date, status, body
                FROM ahmf.messages
                WHERE message_type='task' AND status='open'
                ORDER BY due_date ASC NULLS LAST LIMIT 5
            """)).fetchall()

            notifications = s.execute(text("""
                SELECT subject, body, created_at FROM ahmf.messages
                WHERE message_type='notification' AND status='open'
                ORDER BY created_at DESC LIMIT 5
            """)).fetchall()

            status_breakdown = s.execute(text("""
                SELECT status, COUNT(*), COALESCE(SUM(loan_amount),0)
                FROM ahmf.deals GROUP BY status ORDER BY status
            """)).fetchall()

    except Exception as e:
        logger.warning(f"Dashboard query error: {e}")

    ep_fees = total_loan * 0.03
    profit_splits = total_loan * 0.015

    collection_rate = (total_collected / total_mg * 100) if total_mg > 0 else 0

    kpi_cards = Div(
        Div(Div("Internal Rate of Return", cls="kpi-label"), Div(f"{avg_rate:.0f}%", cls="kpi-value"), Div("all time", cls="kpi-sub"), cls="kpi-card"),
        Div(Div("Gross Yield", cls="kpi-label"), Div(f"{avg_rate * 1.3:.0f}%", cls="kpi-value"), Div("all time, annualized", cls="kpi-sub"), cls="kpi-card"),
        Div(Div("Executive Producer Fees", cls="kpi-label"), Div(f"${ep_fees:,.0f}", cls="kpi-value"), Div("since start of the year", cls="kpi-sub"), cls="kpi-card"),
        Div(Div("Profit Splits", cls="kpi-label"), Div(f"${profit_splits:,.0f}", cls="kpi-value"), Div("since start of the year", cls="kpi-sub"), cls="kpi-card"),
        cls="kpi-grid",
    )

    portfolio_cards = Div(
        Div(Div("Active Deals", cls="kpi-label"), Div(str(active_count), cls="kpi-value"), Div(f"${active_loan:,.0f} exposure", cls="kpi-sub"), cls="kpi-card"),
        Div(Div("Pipeline", cls="kpi-label"), Div(str(pipeline_count), cls="kpi-value"), Div(f"${pipeline_loan:,.0f} pending", cls="kpi-sub"), cls="kpi-card"),
        Div(Div("Total Portfolio", cls="kpi-label"), Div(f"${total_loan:,.0f}", cls="kpi-value"), Div(f"{deals_count} deals", cls="kpi-sub"), cls="kpi-card"),
        Div(Div("Collection Rate", cls="kpi-label"), Div(f"{collection_rate:.0f}%", cls="kpi-value"), Div(f"${total_collected:,.0f} collected", cls="kpi-sub"), cls="kpi-card"),
        cls="kpi-grid",
    )

    notif_items = [Div(
        Div(Span("\U0001f514", style="margin-right:.5rem;"), Span(n[0], style="font-weight:500;font-size:.85rem;"),
            style="display:flex;align-items:center;"),
        Div(n[1] or "", style="font-size:.75rem;color:var(--ink-muted);margin-top:.25rem;"),
        style="padding:.75rem;border-left:3px solid #8b5cf6;background:#f5f3ff;border-radius:0 8px 8px 0;margin-bottom:.5rem;",
    ) for n in notifications]

    notif_section = Div(
        Div(Span("\U0001f514", cls="section-icon"), Span("Notifications", cls="section-title-text"), cls="section-header"),
        *(notif_items if notif_items else [Div("No new notifications", style="font-size:.8rem;color:var(--ink-dim);padding:.5rem;")]),
        cls="dashboard-card",
    )

    todo_items = []
    for m in messages:
        priority = "Medium priority"
        if m[1] and str(m[1]) < str(datetime.date.today()):
            priority = "ASAP"
        elif m[1] and str(m[1]) == str(datetime.date.today()):
            priority = "High priority"
        due_str = f"Due {m[1]}" if m[1] else "No due date"
        todo_items.append(
            Div(
                Span("○", cls="todo-check"),
                Div(
                    Span(m[0] or "Task", cls="todo-text"),
                    Div(
                        Span(due_str, cls="todo-due"),
                        Span(priority, cls=f"todo-priority {'todo-asap' if priority == 'ASAP' else 'todo-high' if priority == 'High priority' else ''}"),
                        cls="todo-meta",
                    ),
                    cls="todo-content",
                ),
                cls="todo-item",
            )
        )
    if not todo_items:
        todo_items = [Div("No open tasks", cls="empty-state")]

    agenda = Div(
        Div(Span("📅", cls="section-icon"), Span("Agenda", cls="section-title-text"), cls="section-header"),
        Div(
            Div(Span("9AM", cls="agenda-time"), Div(cls="agenda-block empty"), cls="agenda-slot"),
            Div(Span("10AM", cls="agenda-time"), Div("Weekly Sync", cls="agenda-block meeting"), cls="agenda-slot"),
            Div(Span("11AM", cls="agenda-time"), Div("Deep focus time", cls="agenda-block focus"), cls="agenda-slot"),
            Div(Span("12PM", cls="agenda-time"), Div("Lunch", cls="agenda-block lunch"), cls="agenda-slot"),
            Div(Span("1PM", cls="agenda-time"), Div(cls="agenda-block empty"), cls="agenda-slot"),
            cls="agenda-widget",
        ),
        cls="dashboard-card",
    )

    todo_section = Div(
        Div(
            Div(
                Div(Span("☑", cls="section-icon"), Span("To-Do", cls="section-title-text"), cls="section-header"),
                *todo_items,
                cls="dashboard-card todo-card",
            ),
            agenda,
            cls="todo-agenda-row",
        ),
    )

    deal_cards = [_deal_poster_card(d) for d in deals]
    if not deal_cards:
        deal_cards = [Div("No deals yet. Create your first deal.", cls="empty-state")]

    deals_section = Div(
        Div(Span("⭐", cls="section-icon"), Span("Deals", cls="section-title-text"), cls="section-header"),
        Div(*deal_cards, cls="deals-scroll"),
        cls="dashboard-card",
    )

    chart_data = {s[0]: float(s[2]) for s in status_breakdown} if status_breakdown else {}
    analytics_section = Div(
        Div(Span("◎", cls="section-icon"), Span("Analytics & Reporting", cls="section-title-text"), cls="section-header"),
        Div(
            Div(
                Div("Repayments", cls="chart-title"),
                Div(f"${total_loan * 0.85:,.2f}", cls="chart-value"),
                Div(id="chart-repayments", style="height:120px;"),
                cls="chart-card",
            ),
            Div(
                Div("Sales & Collections", cls="chart-title"),
                Div(f"${total_loan * 0.45:,.2f}", cls="chart-value"),
                Div(id="chart-sales", style="height:120px;"),
                cls="chart-card",
            ),
            cls="charts-row",
        ),
        Div(
            Div(
                Div("Profit Splits", cls="chart-title"),
                Div(f"${profit_splits:,.0f}", cls="chart-value"),
                Div(id="chart-profits", style="height:120px;"),
                cls="chart-card",
            ),
            Div(
                Div("EP Fees Flow", cls="chart-title"),
                Div(f"${ep_fees:,.2f}", cls="chart-value"),
                Div(id="chart-fees", style="height:120px;"),
                cls="chart-card",
            ),
            Div(
                Div("Post-Maturity Interest", cls="chart-title"),
                Div(f"${total_loan * 0.02:,.2f}", cls="chart-value"),
                Div(id="chart-interest", style="height:120px;"),
                cls="chart-card",
            ),
            cls="charts-row charts-row-3",
        ),
        cls="dashboard-card",
    )

    chart_js = Script(f"""
    (function() {{
        var months = ['Jan','Feb','Mar','Apr','May'];
        var layout = {{margin:{{t:5,r:10,b:25,l:40}},paper_bgcolor:'transparent',plot_bgcolor:'transparent',font:{{size:10,color:'#7A7A7A'}},xaxis:{{showgrid:false}},yaxis:{{showgrid:true,gridcolor:'#E8E4DC'}}}};
        var config = {{displayModeBar:false,responsive:true}};
        var repay = [{{x:months,y:[{total_loan*0.1:.0f},{total_loan*0.15:.0f},{total_loan*0.2:.0f},{total_loan*0.22:.0f},{total_loan*0.18:.0f}],type:'scatter',fill:'tozeroy',line:{{color:'#3B82F6'}},fillcolor:'rgba(59,130,246,0.15)'}}];
        var sales = [{{x:months,y:[{total_loan*0.08:.0f},{total_loan*0.12:.0f},{total_loan*0.09:.0f},{total_loan*0.11:.0f},{total_loan*0.05:.0f}],type:'bar',marker:{{color:'#3B82F6'}},name:'Deliveries'}},
                     {{x:months,y:[{total_loan*0.06:.0f},{total_loan*0.09:.0f},{total_loan*0.07:.0f},{total_loan*0.08:.0f},{total_loan*0.04:.0f}],type:'bar',marker:{{color:'#93C5FD'}},name:'Sales'}}];
        var profits = [{{x:months,y:[{profit_splits*0.15:.0f},{profit_splits*0.2:.0f},{profit_splits*0.25:.0f},{profit_splits*0.22:.0f},{profit_splits*0.18:.0f}],type:'bar',marker:{{color:'#3B82F6'}}}}];
        var fees = [{{x:months,y:[{ep_fees*0.1:.0f},{ep_fees*0.15:.0f},{ep_fees*0.22:.0f},{ep_fees*0.28:.0f},{ep_fees*0.25:.0f}],type:'bar',marker:{{color:'#EF4444'}}}}];
        var interest = [{{x:months,y:[{total_loan*0.003:.0f},{total_loan*0.004:.0f},{total_loan*0.005:.0f},{total_loan*0.004:.0f},{total_loan*0.004:.0f}],type:'scatter',fill:'tozeroy',line:{{color:'#3B82F6'}},fillcolor:'rgba(59,130,246,0.15)'}}];
        if(document.getElementById('chart-repayments')) Plotly.newPlot('chart-repayments',repay,layout,config);
        if(document.getElementById('chart-sales')) Plotly.newPlot('chart-sales',sales,{{...layout,barmode:'group'}},config);
        if(document.getElementById('chart-profits')) Plotly.newPlot('chart-profits',profits,layout,config);
        if(document.getElementById('chart-fees')) Plotly.newPlot('chart-fees',fees,layout,config);
        if(document.getElementById('chart-interest')) Plotly.newPlot('chart-interest',interest,layout,config);
    }})();
    """)

    return Div(
        Div(
            Div(
                H1(f"{greeting}, {display}", cls="dash-greeting"),
                P(f"Today you have {tasks_due} due tasks and {tasks_overdue} overdue", cls="dash-subtitle"),
                cls="dash-greeting-block",
            ),
            Div(
                Button("New Deal +", cls="new-deal-btn",
                       hx_get="/module/deal/new", hx_target="#center-content", hx_swap="innerHTML"),
                cls="dash-actions",
            ),
            cls="dash-header",
        ),
        kpi_cards,
        portfolio_cards,
        notif_section,
        todo_section,
        deals_section,
        analytics_section,
        chart_js,
        cls="module-content dashboard-content",
    )


@rt("/module/reporting")
def module_reporting(session, view: str = "territory", period: str = "all"):
    from sqlalchemy import text
    from utils.db import get_pool
    pool = get_pool()

    period_clause = ""
    if period == "year":
        period_clause = "AND d.created_at >= DATE_TRUNC('year', CURRENT_DATE)"
    elif period == "quarter":
        period_clause = "AND d.created_at >= DATE_TRUNC('quarter', CURRENT_DATE)"
    elif period == "month":
        period_clause = "AND d.created_at >= DATE_TRUNC('month', CURRENT_DATE)"

    with pool.get_session() as s:
        if view == "territory":
            rows = s.execute(text(f"""
                SELECT sc.territory, COUNT(DISTINCT sc.deal_id), COALESCE(SUM(sc.mg_amount), 0),
                       COALESCE(SUM(c.amount_received), 0)
                FROM ahmf.sales_contracts sc
                LEFT JOIN ahmf.collections c ON c.contract_id = sc.contract_id
                JOIN ahmf.deals d ON d.deal_id = sc.deal_id
                WHERE 1=1 {period_clause}
                GROUP BY sc.territory ORDER BY SUM(sc.mg_amount) DESC NULLS LAST
            """)).fetchall()
            headers = ["Territory", "Deals", "Total MG", "Collected", "Collection Rate"]
            data_rows = []
            for r in rows:
                mg = float(r[2])
                col = float(r[3])
                rate = f"{col/mg*100:.0f}%" if mg > 0 else "\u2014"
                data_rows.append(Tr(Td(r[0] or "Unknown"), Td(str(r[1])), Td(f"${mg:,.0f}"), Td(f"${col:,.0f}"), Td(rate)))

        elif view == "genre":
            rows = s.execute(text(f"""
                SELECT COALESCE(genre, 'Unknown'), COUNT(*), COALESCE(SUM(loan_amount), 0),
                       COALESCE(AVG(loan_amount), 0), COALESCE(AVG(interest_rate), 0)
                FROM ahmf.deals d WHERE 1=1 {period_clause}
                GROUP BY genre ORDER BY SUM(loan_amount) DESC NULLS LAST
            """)).fetchall()
            headers = ["Genre", "Deals", "Total Exposure", "Avg Deal Size", "Avg Rate"]
            data_rows = [Tr(Td(r[0]), Td(str(r[1])), Td(f"${float(r[2]):,.0f}"),
                           Td(f"${float(r[3]):,.0f}"), Td(f"{float(r[4]):.1f}%")) for r in rows]

        elif view == "status":
            rows = s.execute(text(f"""
                SELECT status, COUNT(*), COALESCE(SUM(loan_amount), 0), COALESCE(AVG(interest_rate), 0)
                FROM ahmf.deals d WHERE 1=1 {period_clause}
                GROUP BY status ORDER BY status
            """)).fetchall()
            headers = ["Status", "Deals", "Total Exposure", "Avg Rate"]
            data_rows = [Tr(Td(r[0].title()), Td(str(r[1])), Td(f"${float(r[2]):,.0f}"),
                           Td(f"{float(r[3]):.1f}%")) for r in rows]

        else:  # size
            rows = s.execute(text(f"""
                SELECT CASE
                    WHEN loan_amount < 5000000 THEN 'Under $5M'
                    WHEN loan_amount < 10000000 THEN '$5M - $10M'
                    WHEN loan_amount < 25000000 THEN '$10M - $25M'
                    ELSE '$25M+'
                END AS bucket, COUNT(*), COALESCE(SUM(loan_amount), 0), COALESCE(AVG(interest_rate), 0)
                FROM ahmf.deals d WHERE loan_amount IS NOT NULL {period_clause}
                GROUP BY bucket ORDER BY MIN(loan_amount)
            """)).fetchall()
            headers = ["Loan Size", "Deals", "Total Exposure", "Avg Rate"]
            data_rows = [Tr(Td(r[0]), Td(str(r[1])), Td(f"${float(r[2]):,.0f}"),
                           Td(f"{float(r[3]):.1f}%")) for r in rows]

    if not data_rows:
        data_rows = [Tr(Td("No data for this period.", colspan=str(len(headers)), style="text-align:center;padding:2rem;color:#94a3b8;"))]

    view_buttons = []
    for v, label in [("territory", "By Territory"), ("genre", "By Genre"), ("status", "By Status"), ("size", "By Loan Size")]:
        active = " filter-active" if v == view else ""
        view_buttons.append(Button(label, cls=f"filter-chip{active}",
            hx_get=f"/module/reporting?view={v}&period={period}", hx_target="#center-content", hx_swap="innerHTML"))

    period_buttons = []
    for p, label in [("all", "All Time"), ("year", "This Year"), ("quarter", "This Quarter"), ("month", "This Month")]:
        active = " filter-active" if p == period else ""
        period_buttons.append(Button(label, cls=f"filter-chip{active}",
            hx_get=f"/module/reporting?view={view}&period={p}", hx_target="#center-content", hx_swap="innerHTML"))

    return Div(
        H1("Reporting"),
        Div(
            Div(*view_buttons, style="display:flex;gap:.5rem;flex-wrap:wrap;"),
            Div(*period_buttons, style="display:flex;gap:.5rem;flex-wrap:wrap;"),
            style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:.75rem;margin-bottom:1rem;",
        ),
        Table(
            Thead(Tr(*[Th(h) for h in headers])),
            Tbody(*data_rows),
            style="width:100%;border-collapse:collapse;font-size:.85rem;",
        ),
        cls="module-content",
    )


@rt("/module/deals")
def module_deals(session, status: str = "", loan_min: str = "", loan_max: str = "", view: str = "grid"):
    from sqlalchemy import text
    from utils.db import get_pool
    import datetime
    try:
        pool = get_pool()
        with pool.get_session() as s:
            where_clauses = []
            params = {}
            if status:
                where_clauses.append("status = :status")
                params["status"] = status
            if loan_min:
                where_clauses.append("loan_amount >= :lmin")
                params["lmin"] = float(loan_min)
            if loan_max:
                where_clauses.append("loan_amount <= :lmax")
                params["lmax"] = float(loan_max)
            where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
            rows = s.execute(text(f"""
                SELECT deal_id, title, status, loan_amount, borrower_name, genre,
                       origination_date, created_at
                FROM ahmf.deals {where_sql} ORDER BY created_at DESC
            """), params).fetchall()
    except Exception:
        rows = []

    today = datetime.date.today()

    if view == "aging":
        aging_rows = []
        for d in rows:
            deal_status = d[2] or "pipeline"
            orig_date = d[6]
            created_at = d[7]
            start = orig_date or (created_at.date() if hasattr(created_at, 'date') else today)
            days_in = (today - start).days if start else 0
            aging_rows.append(Tr(
                Td(A(d[1], href="#", onclick=f"loadModule('/module/deal/{d[0]}','Deal: {d[1]}');return false;",
                     style="color:var(--blue);text-decoration:none;font-weight:500;")),
                Td(deal_status.title()),
                Td(f"${float(d[3]):,.0f}" if d[3] else "—"),
                Td(str(days_in)),
                Td(str(start) if start != today else "—"),
            ))
        content = Table(
            Thead(Tr(Th("Title"), Th("Status"), Th("Loan"), Th("Days"), Th("Start Date"))),
            Tbody(*aging_rows) if aging_rows else Tbody(Tr(Td("No deals.", colspan="5", style="text-align:center;padding:2rem;"))),
            style="width:100%;border-collapse:collapse;font-size:.85rem;",
        )
    else:
        deal_cards = [_deal_poster_card(d) for d in rows]
        if not deal_cards:
            deal_cards = [Div("No deals yet.", cls="empty-state")]
        content = Div(*deal_cards, cls="deals-grid")

    filter_panel = Div(
        Div(
            Select(
                Option("All statuses", value=""),
                Option("Active", value="active"),
                Option("Pipeline", value="pipeline"),
                Option("Closed", value="closed"),
                Option("Declined", value="declined"),
                name="status",
                hx_get="/module/deals", hx_target="#center-content", hx_swap="innerHTML",
                hx_include="[name='loan_min'],[name='loan_max'],[name='view']",
                style="padding:.35rem .5rem;border:1px solid var(--line);border-radius:.3rem;font-size:.8rem;background:var(--bg-elev);color:var(--ink);",
                **{"value": status} if status else {},
            ),
            Select(
                Option("All loan sizes", value="", **{"data-min": "", "data-max": ""}),
                Option("Under $5M", value="0-5000000"),
                Option("$5M – $10M", value="5000000-10000000"),
                Option("$10M – $15M", value="10000000-15000000"),
                Option("$15M – $25M", value="15000000-25000000"),
                Option("$25M+", value="25000000-"),
                name="loan_range",
                style="padding:.35rem .5rem;border:1px solid var(--line);border-radius:.3rem;font-size:.8rem;background:var(--bg-elev);color:var(--ink);",
                onchange="var v=this.value.split('-');document.querySelector('[name=loan_min]').value=v[0]||'';document.querySelector('[name=loan_max]').value=v[1]||'';this.closest('div').querySelector('[name=status]').dispatchEvent(new Event('change'));",
            ),
            Input(type="hidden", name="loan_min", value=loan_min),
            Input(type="hidden", name="loan_max", value=loan_max),
            Input(type="hidden", name="view", value=view),
            cls="deal-toolbar-btns", style="gap:.5rem;",
        ),
        Div(
            Button("Grid", cls=f"filter-chip{' filter-active' if view == 'grid' else ''}",
                   onclick="document.querySelector('[name=view]').value='grid';document.querySelector('[name=status]').dispatchEvent(new Event('change'));"),
            Button("Aging", cls=f"filter-chip{' filter-active' if view == 'aging' else ''}",
                   onclick="document.querySelector('[name=view]').value='aging';document.querySelector('[name=status]').dispatchEvent(new Event('change'));"),
            A("⤓ CSV", href="/api/export/deals", cls="filter-chip",
              style="text-decoration:none;display:inline-flex;align-items:center;"),
            cls="deal-toolbar-btns", style="gap:.5rem;",
        ),
        style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:.5rem;margin-bottom:.75rem;",
    )

    return Div(
        Div(
            H1("Deals"),
            Button("New Deal +", cls="new-deal-btn",
                   hx_get="/module/deal/new", hx_target="#center-content", hx_swap="innerHTML"),
            cls="deals-header",
        ),
        filter_panel,
        content,
        cls="module-content",
    )


@rt("/module/deal/new")
def deal_new_form(session):
    from config.settings import GENRES, PROJECT_TYPES, DEAL_STATUSES, TERRITORIES, CURRENCIES
    genre_opts = [Option(g, value=g) for g in GENRES]
    type_opts = [Option(t.replace("_", " ").title(), value=t) for t in PROJECT_TYPES]
    currency_opts = [Option(c, value=c) for c in ["USD", "EUR", "GBP", "CAD", "AUD"]]
    collateral_opts = [Option(c, value=c) for c in ["Pre-Sales", "Gap/Unsold", "Tax Credit"]]

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
                Div(Label("Loan Amount", Input(type="number", name="loan_amount", placeholder="0")), style="flex:1"),
                Div(Label("Currency", Select(*currency_opts, name="currency")), style="flex:1"),
                Div(Label("Interest Rate (%)", Input(type="number", name="interest_rate", step="0.01", placeholder="0")), style="flex:1"),
                Div(Label("Term (months)", Input(type="number", name="term_months", placeholder="12")), style="flex:1"),
                style="display:flex;gap:1rem;",
            ),
            Div(
                Div(Label("Collateral Type", Select(*collateral_opts, name="collateral_type")), style="flex:1"),
                style="display:flex;gap:1rem;",
            ),
            Div(
                Div(Label("Origination Date", Input(type="date", name="origination_date")), style="flex:1"),
                Div(Label("Maturity Date", Input(type="date", name="maturity_date")), style="flex:1"),
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
            Label("Notes", Textarea(name="notes", placeholder="Additional notes about this deal...", rows="3",
                                    style="width:100%;border:1px solid #d1d5db;border-radius:6px;padding:0.5rem;font-size:0.9rem;")),
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


@rt("/module/deal/{deal_id}")
def module_deal_detail(deal_id: str, session):
    from sqlalchemy import text as sa_text
    from utils.db import get_pool
    pool = get_pool()
    with pool.get_session() as s:
        deal = s.execute(sa_text("""
            SELECT deal_id, title, project_type, genre, status, loan_amount,
                   currency, interest_rate, term_months, borrower_name,
                   producer, director, cast_summary, budget, territory,
                   origination_date, maturity_date, collateral_type
            FROM ahmf.deals WHERE deal_id = :did
        """), {"did": deal_id}).fetchone()
        contracts = s.execute(sa_text("""
            SELECT sc.territory, c.name AS distributor, sc.mg_amount, sc.status
            FROM ahmf.sales_contracts sc
            LEFT JOIN ahmf.contacts c ON c.contact_id = sc.distributor_id
            WHERE sc.deal_id = :did ORDER BY sc.territory
        """), {"did": deal_id}).fetchall()
        txns = s.execute(sa_text("""
            SELECT t.txn_type, t.amount, t.currency, c.name, t.posted_date, t.reference
            FROM ahmf.transactions t
            LEFT JOIN ahmf.contacts c ON c.contact_id = t.counterparty_id
            WHERE t.deal_id = :did ORDER BY t.posted_date DESC LIMIT 10
        """), {"did": deal_id}).fetchall()
        tasks = s.execute(sa_text("""
            SELECT subject, due_date, status FROM ahmf.messages
            WHERE deal_id = :did AND message_type='task'
            ORDER BY due_date ASC NULLS LAST LIMIT 6
        """), {"did": deal_id}).fetchall()

        deal_credit = s.execute(sa_text("""
            SELECT c.name, cr.score, cr.risk_tier, sc.mg_amount
            FROM ahmf.sales_contracts sc
            JOIN ahmf.contacts c ON c.contact_id = sc.distributor_id
            LEFT JOIN ahmf.credit_ratings cr ON cr.contact_id = c.contact_id
            WHERE sc.deal_id = :did
        """), {"did": deal_id}).fetchall()

    if not deal:
        return Div(P("Deal not found."), cls="module-content")

    title = deal[1]
    project_type = (deal[2] or "feature_film").replace("_", " ").title()
    genre = (deal[3] or "").replace("_", " ").title()
    status = deal[4] or "pipeline"
    loan = float(deal[5]) if deal[5] else 0
    currency = deal[6] or "USD"
    rate = float(deal[7]) if deal[7] else 0
    term = deal[8] or 12
    borrower = deal[9] or "—"
    producer = deal[10] or "—"
    director = deal[11] or "—"
    cast = deal[12] or "—"
    budget = float(deal[13]) if deal[13] else 0
    territory = deal[14] or "—"
    orig_date = deal[15] or "—"
    mat_date = deal[16] or "—"
    collateral_type = deal[17] or "Pre-Sales"
    status_color = STATUS_COLORS.get(status, "#CFC8B4")
    gradient = GENRE_GRADIENTS.get(genre.lower(), GENRE_GRADIENTS["default"])

    interest_reserve = loan * rate / 100 * term / 12
    gross_loan = loan + interest_reserve
    ep_fees = loan * 0.03
    projected_irr = rate * 1.3

    total_sold = sum(float(c[2]) for c in contracts if c[2]) if contracts else 0
    total_unsold = loan - total_sold if loan else 0

    # Hero banner
    hero = Div(
        Div(title, cls="hero-title"),
        Div(str(orig_date)[:4] if orig_date != "—" else "2026", cls="hero-year"),
        cls="deal-hero", style=f"background:{gradient};",
    )

    # Overview
    overview = Div(
        H2("Overview"),
        P(f"{title} is a {genre.lower()} {project_type.lower()} produced by {producer}, "
          f"directed by {director}. Budget: ${budget:,.0f}. Borrower: {borrower}. "
          f"Cast: {cast}. Territory: {territory}.",
          style="color:var(--ink-muted);line-height:1.6;"),
        cls="deal-section",
    )

    # Key Terms cards
    key_terms = Div(
        H2("Key Terms"),
        Div(
            Div(
                Div("Loan Balance", cls="kpi-label"),
                Div(f"${loan:,.0f}", cls="kpi-value"),
                Div(
                    Div(f"Net Loan Facility: ${loan:,.0f}", style="font-size:.72rem;color:var(--ink-dim);margin-top:.5rem;"),
                    Div(f"Interest Reserve: ${interest_reserve:,.0f}", style="font-size:.72rem;color:var(--ink-dim);"),
                    Div(f"Gross Loan Facility: ${gross_loan:,.0f}", style="font-size:.72rem;color:var(--ink-dim);"),
                    Div(f"EP Fees: ${ep_fees:,.0f}", style="font-size:.72rem;color:var(--ink-dim);"),
                    Div(f"Projected IRR: {projected_irr:.1f}%", style="font-size:.72rem;color:var(--ink-dim);"),
                ),
                cls="chart-card",
            ),
            Div(
                Div("Finance Plan", cls="kpi-label"),
                Div(id="chart-finance-plan", style="height:160px;"),
                cls="chart-card",
            ),
            Div(
                Div("Collateral Breakdown", cls="kpi-label"),
                Div(id="chart-collateral", style="height:160px;"),
                cls="chart-card",
            ),
            cls="charts-row charts-row-3",
        ),
        cls="deal-section",
    )

    # Collateral & Receivables (SOW section)
    presales_amt = total_sold
    gap_unsold_amt = total_unsold
    tax_credit_amt = loan * 0.15
    deferral_amt = loan * 0.05
    collateral_total = presales_amt + gap_unsold_amt + tax_credit_amt + deferral_amt
    principal_pct = 0.65
    interest_pct = 0.35
    covered = collateral_total >= loan

    collateral_receivables = Div(
        H2("Collateral & Receivables"),
        Div(
            Div(
                Div(Span("●", style=f"color:{'#16a34a' if covered else '#dc2626'};margin-right:.5rem;"),
                    "Covered" if covered else "Uncovered",
                    style="font-size:.85rem;font-weight:600;margin-bottom:.75rem;"),
                Div("Loan Balance", style="font-size:.72rem;color:var(--ink-dim);margin-bottom:.5rem;"),
                Div(id="chart-cr-loan", style="height:140px;"),
                Div(
                    Div(Span("Net Loan Facility", style="color:var(--ink-dim);font-size:.7rem;"),
                        Span(f"${loan:,.0f}", style="font-size:.7rem;font-weight:500;"), cls="sidebar-kv"),
                    Div(Span("Stated Interest", style="color:var(--ink-dim);font-size:.7rem;"),
                        Span(f"${interest_reserve:,.0f}", style="font-size:.7rem;font-weight:500;"), cls="sidebar-kv"),
                    Div(Span("Post-Maturity Interest", style="color:var(--ink-dim);font-size:.7rem;"),
                        Span(f"${loan * 0.02:,.0f}", style="font-size:.7rem;font-weight:500;"), cls="sidebar-kv"),
                    Div(Span("Other Interest", style="color:var(--ink-dim);font-size:.7rem;"),
                        Span(f"${loan * 0.01:,.0f}", style="font-size:.7rem;font-weight:500;"), cls="sidebar-kv"),
                    Div(Span("Interest Repayments", style="color:var(--ink-dim);font-size:.7rem;"),
                        Span(f"$ ({loan * 0.005:,.0f})", style="font-size:.7rem;font-weight:500;color:var(--red);"), cls="sidebar-kv"),
                ),
                cls="chart-card",
            ),
            Div(
                Div("Collateral", style="font-size:.72rem;color:var(--ink-dim);margin-bottom:.25rem;"),
                Div(f"${collateral_total:,.0f}", style="font-size:1.1rem;font-weight:700;margin-bottom:.5rem;"),
                Div(id="chart-cr-collateral", style="height:180px;"),
                cls="chart-card",
            ),
            cls="charts-row",
        ),
        cls="deal-section",
    )

    # Sales & Collections
    sc_rows = []
    for c in contracts:
        sc_color = {"active": "#16a34a", "completed": "#0052CC", "draft": "#94a3b8"}.get(c[3], "#64748b")
        sc_rows.append(Tr(
            Td(c[0] or "—"), Td(c[1] or "—"),
            Td(f"${float(c[2]):,.0f}" if c[2] else "—"),
            Td(Span((c[3] or "draft").title(), cls="status-pill", style=f"background:{sc_color}20;color:{sc_color};")),
        ))

    sales_section = Div(
        H2("Sales & Collections"),
        Div(
            Div(Div("Sales & Collected", cls="chart-title"), Div(id="chart-deal-sales", style="height:140px;"), cls="chart-card"),
            Div(Div("Sold vs Unsold", cls="chart-title"), Div(id="chart-deal-unsold", style="height:140px;"), cls="chart-card"),
            cls="charts-row",
        ),
        Table(
            Thead(Tr(Th("Territory"), Th("Distributor"), Th("MG Amount"), Th("Status"))),
            Tbody(*sc_rows) if sc_rows else Tbody(Tr(Td("No contracts.", colspan="4", style="color:var(--ink-dim);text-align:center;"))),
        ) if True else "",
        cls="deal-section",
    )

    # Tax Incentives, Guarantees, & Collections (SOW section)
    import random as _rnd
    _rnd.seed(hash(str(deal[0])) % 10000)
    territories_data = [
        {"name": "United Kingdom", "estimated": "$880,000", "funded": "$660,000", "currency": "GBP", "fx": "1.32",
         "balance": loan * 0.08},
        {"name": "Germany", "estimated": "$350,000", "funded": "$280,000", "currency": "EUR", "fx": "1.32",
         "balance": loan * 0.05},
    ]
    terr_cards = []
    for idx, td_item in enumerate(territories_data):
        terr_cards.append(Div(
            Div(
                Div(td_item["name"], style="font-weight:600;font-size:.88rem;"),
                Div("↗", style="color:var(--blue);cursor:pointer;"),
                style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem;",
            ),
            Div(
                Div(Span("Estimated (MFN)", style="color:var(--ink-dim);font-size:.7rem;"),
                    Span(td_item["estimated"], style="font-size:.7rem;font-weight:500;"), cls="sidebar-kv"),
                Div(Span("Funded (MFN)", style="color:var(--ink-dim);font-size:.7rem;"),
                    Span(td_item["funded"], style="font-size:.7rem;font-weight:500;"), cls="sidebar-kv"),
            ),
            Div(id=f"chart-terr-{idx}", style="height:80px;margin:.5rem 0;"),
            Div(
                Div(Span("Original Currency", style="color:var(--ink-dim);font-size:.65rem;"),
                    Span(td_item["currency"], style="font-size:.65rem;"), cls="sidebar-kv"),
                Div(Span("FX (Converted)", style="color:var(--ink-dim);font-size:.65rem;"),
                    Span(td_item["fx"], style="font-size:.65rem;"), cls="sidebar-kv"),
                Div(Span("Balance:", style="color:var(--ink-dim);font-size:.72rem;font-weight:600;"),
                    Span(f"${td_item['balance']:,.0f}", style="font-size:.85rem;font-weight:700;"), cls="sidebar-kv"),
            ),
            cls="chart-card",
        ))

    tax_incentives = Div(
        H2("Tax Incentives, Guarantees, & Collections"),
        Div(*terr_cards, cls="charts-row"),
        cls="deal-section",
    )

    # Right sidebar: Key Terms, Projection, Transactions, Tasks
    txn_items = []
    for t in txns:
        sign = "-" if t[0] == "disbursement" else "+"
        color = "#dc2626" if t[0] == "disbursement" else "#16a34a"
        txn_items.append(Div(
            Div(Span(t[5] or t[0].title(), style="font-size:.72rem;"), cls="txn-ref"),
            Div(f"{sign}${float(t[1]):,.0f}" if t[1] else "—", style=f"font-size:.78rem;font-weight:600;color:{color};"),
            cls="sidebar-txn-item",
        ))

    task_items = []
    for t in tasks:
        task_items.append(Div(
            Span("○", style="color:var(--ink-dim);"),
            Span(t[0] or "Task", style="font-size:.76rem;flex:1;"),
            Span(str(t[1]) if t[1] else "", style="font-size:.66rem;color:var(--red);"),
            cls="sidebar-task-item",
        ))

    # Weighted-average deal credit rating
    total_weight = sum(float(dc[3]) for dc in deal_credit if dc[3] and dc[1])
    weighted_score = sum(float(dc[1]) * float(dc[3]) for dc in deal_credit if dc[1] and dc[3]) / total_weight if total_weight > 0 else 0
    wa_tier = "A" if weighted_score >= 80 else "B" if weighted_score >= 60 else "C" if weighted_score >= 40 else "D" if weighted_score > 0 else "N/A"
    wa_tier_color = {"A": "#16a34a", "B": "#0052CC", "C": "#f59e0b", "D": "#dc2626"}.get(wa_tier, "#64748b")

    credit_counterparty_rows = []
    for dc in deal_credit:
        dc_name = dc[0] or "Unknown"
        dc_score = f"{dc[1]:.0f}" if dc[1] else "—"
        dc_tier = dc[2] or "—"
        dc_mg = f"${float(dc[3]):,.0f}" if dc[3] else "—"
        credit_counterparty_rows.append(Div(
            Div(Span(dc_name, style="font-size:.72rem;font-weight:500;flex:1;"), Span(dc_score, style="font-size:.72rem;font-weight:600;"), cls="sidebar-kv"),
            Div(Span(f"Tier: {dc_tier}", style="font-size:.65rem;color:var(--ink-dim);"), Span(f"MG: {dc_mg}", style="font-size:.65rem;color:var(--ink-dim);"), cls="sidebar-kv"),
            style="padding:.25rem 0;border-bottom:1px solid var(--line);",
        ))

    credit_card = Div(
        H3("Deal Credit", style="font-size:.85rem;"),
        Div(
            Div(Span("Weighted Avg Score", style="color:var(--ink-dim);font-size:.72rem;"),
                Span(f"{weighted_score:.0f}" if weighted_score > 0 else "N/A", style=f"font-size:.85rem;font-weight:700;color:{wa_tier_color};"), cls="sidebar-kv"),
            Div(Span("Risk Tier", style="color:var(--ink-dim);font-size:.72rem;"),
                Span(wa_tier, style=f"font-size:.85rem;font-weight:700;color:{wa_tier_color};"), cls="sidebar-kv"),
            style="margin-bottom:.5rem;padding-bottom:.5rem;border-bottom:1px solid var(--line);",
        ),
        *(credit_counterparty_rows if credit_counterparty_rows else [Div("No counterparty ratings", style="font-size:.72rem;color:var(--ink-dim);")]),
        cls="sidebar-card",
    )

    right_sidebar = Div(
        Div(
            H3("Key Terms", style="font-size:.85rem;"),
            Div(Span("AH Lead", style="color:var(--ink-dim);font-size:.72rem;"), Span(producer, style="font-size:.72rem;font-weight:500;"), cls="sidebar-kv"),
            Div(Span("Prod. Co.", style="color:var(--ink-dim);font-size:.72rem;"), Span(borrower, style="font-size:.72rem;font-weight:500;"), cls="sidebar-kv"),
            Div(Span("Sales Agent", style="color:var(--ink-dim);font-size:.72rem;"), Span("CAA Media Finance", style="font-size:.72rem;font-weight:500;"), cls="sidebar-kv"),
            Div(Span("CAA Agent", style="color:var(--ink-dim);font-size:.72rem;"), Span("Freeway Entertainment", style="font-size:.72rem;font-weight:500;"), cls="sidebar-kv"),
            cls="sidebar-card",
        ),
        Div(
            H3("Projection", style="font-size:.85rem;"),
            Div(f"{term} Months", style="font-size:1.2rem;font-weight:700;"),
            Div("Post-maturity coverage", style="font-size:.68rem;color:var(--ink-dim);"),
            Div(Span("Maturity Date", style="color:var(--ink-dim);font-size:.72rem;"), Span(str(mat_date), style="font-size:.72rem;font-weight:500;"), cls="sidebar-kv"),
            cls="sidebar-card",
        ),
        credit_card,
        Div(
            H3("Transactions", style="font-size:.85rem;"),
            *(txn_items if txn_items else [Div("No transactions", style="font-size:.72rem;color:var(--ink-dim);")]),
            cls="sidebar-card",
        ),
        Div(
            H3("Project Tasks", style="font-size:.85rem;"),
            *(task_items if task_items else [Div("No tasks", style="font-size:.72rem;color:var(--ink-dim);")]),
            cls="sidebar-card",
        ),
        cls="deal-right-sidebar",
    )

    # Communication log
    comms = Div(
        H2("Communication & Action Log"),
        Table(
            Thead(Tr(Th("From"), Th("Subject"), Th("Date"), Th("Actions"))),
            Tbody(
                Tr(Td(producer), Td(f"{title} — Production Meeting"), Td(str(orig_date)), Td("↗ ⭐ 🔗")),
                Tr(Td(borrower), Td(f"{title} — Budget Review"), Td(str(orig_date)), Td("↗ ⭐ 🔗")),
            ),
        ),
        cls="deal-section",
    )

    # Capital waterfall
    tax_credit_val = loan * 0.15 if loan else 0
    gap_val = loan - total_sold - tax_credit_val if loan else 0
    if gap_val < 0:
        gap_val = 0
    total_sources = total_sold + gap_val + tax_credit_val
    ep_fee_wf = loan * 0.03 if loan else 0
    interest_wf = interest_reserve
    net_to_borrower = loan - ep_fee_wf - interest_wf if loan else 0

    waterfall = Div(
        H2("Capital Waterfall"),
        Div(
            Div(
                H3("Sources", style="font-size:.85rem;margin-bottom:.75rem;"),
                Div(Span("Pre-Sales", style="color:var(--ink-dim);"), Span(f"${total_sold:,.0f}", style="font-weight:600;"), cls="sidebar-kv"),
                Div(Span("Gap / Unsold", style="color:var(--ink-dim);"), Span(f"${gap_val:,.0f}", style="font-weight:600;"), cls="sidebar-kv"),
                Div(Span("Tax Credits", style="color:var(--ink-dim);"), Span(f"${tax_credit_val:,.0f}", style="font-weight:600;"), cls="sidebar-kv"),
                Div(Span("Total Sources", style="color:var(--ink-dim);font-weight:600;"), Span(f"${total_sources:,.0f}", style="font-weight:700;color:var(--blue);"), cls="sidebar-kv",
                    style="border-top:1px solid var(--line);padding-top:.5rem;margin-top:.5rem;"),
                cls="chart-card", style="flex:1;",
            ),
            Div(
                H3("Uses", style="font-size:.85rem;margin-bottom:.75rem;"),
                Div(Span("Net Loan Facility", style="color:var(--ink-dim);"), Span(f"${loan:,.0f}", style="font-weight:600;"), cls="sidebar-kv"),
                Div(Span("Less: EP Fees (3%)", style="color:var(--ink-dim);"), Span(f"(${ep_fee_wf:,.0f})", style="font-weight:600;color:#dc2626;"), cls="sidebar-kv"),
                Div(Span("Less: Interest Reserve", style="color:var(--ink-dim);"), Span(f"(${interest_wf:,.0f})", style="font-weight:600;color:#dc2626;"), cls="sidebar-kv"),
                Div(Span("Net to Borrower", style="color:var(--ink-dim);font-weight:600;"), Span(f"${net_to_borrower:,.0f}", style="font-weight:700;color:#16a34a;"), cls="sidebar-kv",
                    style="border-top:1px solid var(--line);padding-top:.5rem;margin-top:.5rem;"),
                cls="chart-card", style="flex:1;",
            ),
            style="display:flex;gap:1rem;",
        ),
        Div(id="chart-waterfall", style="height:260px;margin-top:1rem;"),
        cls="deal-section",
    )

    pre_sales_pct = (total_sold / loan * 100) if loan else 0
    unsold_pct = 100 - pre_sales_pct
    tax_pct = 15

    chart_js = Script(f"""
    (function() {{
        var cfg = {{displayModeBar:false,responsive:true}};
        var lo = {{margin:{{t:5,r:5,b:5,l:5}},paper_bgcolor:'transparent',plot_bgcolor:'transparent',showlegend:true,legend:{{font:{{size:9}}}}}};

        // Finance Plan donut
        Plotly.newPlot('chart-finance-plan',
            [{{values:[{pre_sales_pct:.0f},{unsold_pct:.0f},{tax_pct}],labels:['Pre-Sales','Unsold','Tax Credits'],type:'pie',hole:.55,
               marker:{{colors:['#0052CC','#93C5FD','#16A34A']}},textinfo:'label+percent',textfont:{{size:9}}}}],
            {{...lo,margin:{{t:10,r:10,b:10,l:10}}}},cfg);

        // Collateral Breakdown
        Plotly.newPlot('chart-collateral',
            [{{x:['Pre-Sales','Gap/Unsold','Tax Credits','Deferrals'],y:[{total_sold:.0f},{total_unsold:.0f},{loan*0.15:.0f},{loan*0.05:.0f}],
               type:'bar',marker:{{color:['#0052CC','#93C5FD','#16A34A','#F59E0B']}}}},],
            {{...lo,margin:{{t:10,r:10,b:30,l:45}},xaxis:{{showgrid:false,tickfont:{{size:8}}}},yaxis:{{showgrid:true,gridcolor:'#E5E5E5',tickfont:{{size:8}}}}}},cfg);

        // Sales & Collected line
        var months = ['Jan','Feb','Mar','Apr','May','Jun'];
        Plotly.newPlot('chart-deal-sales',
            [{{x:months,y:[{total_sold*0.1:.0f},{total_sold*0.25:.0f},{total_sold*0.45:.0f},{total_sold*0.65:.0f},{total_sold*0.85:.0f},{total_sold:.0f}],
               type:'scatter',name:'Sales',line:{{color:'#0052CC'}}}},
             {{x:months,y:[0,{total_sold*0.1:.0f},{total_sold*0.2:.0f},{total_sold*0.4:.0f},{total_sold*0.6:.0f},{total_sold*0.8:.0f}],
               type:'scatter',name:'Collected',line:{{color:'#16A34A'}}}}],
            {{...lo,margin:{{t:5,r:10,b:25,l:45}},xaxis:{{showgrid:false}},yaxis:{{showgrid:true,gridcolor:'#E5E5E5'}}}},cfg);

        // Collateral & Receivables - Loan Balance stacked bar
        Plotly.newPlot('chart-cr-loan',
            [{{y:['Loan Balance'],x:[{loan*principal_pct:.0f}],type:'bar',orientation:'h',name:'Principal',marker:{{color:'#0052CC'}}}},
             {{y:['Loan Balance'],x:[{loan*interest_pct:.0f}],type:'bar',orientation:'h',name:'Interest',marker:{{color:'#93C5FD'}}}}],
            {{...lo,margin:{{t:5,r:10,b:25,l:80}},barmode:'stack',yaxis:{{showgrid:false}},xaxis:{{showgrid:true,gridcolor:'#E5E5E5'}},
              showlegend:true,legend:{{font:{{size:8}},orientation:'h',y:-0.3}}}},cfg);

        // Collateral stacked area
        Plotly.newPlot('chart-cr-collateral',
            [{{x:months,y:[{presales_amt*0.2:.0f},{presales_amt*0.4:.0f},{presales_amt*0.6:.0f},{presales_amt*0.8:.0f},{presales_amt*0.9:.0f},{presales_amt:.0f}],
               type:'scatter',fill:'tozeroy',name:'Presales',fillcolor:'rgba(0,82,204,0.3)',line:{{color:'#0052CC'}}}},
             {{x:months,y:[{gap_unsold_amt:.0f},{gap_unsold_amt*0.95:.0f},{gap_unsold_amt*0.9:.0f},{gap_unsold_amt*0.85:.0f},{gap_unsold_amt*0.8:.0f},{gap_unsold_amt*0.75:.0f}],
               type:'scatter',fill:'tonexty',name:'Unsold',fillcolor:'rgba(147,197,253,0.3)',line:{{color:'#93C5FD'}}}},
             {{x:months,y:[{tax_credit_amt:.0f},{tax_credit_amt:.0f},{tax_credit_amt:.0f},{tax_credit_amt:.0f},{tax_credit_amt:.0f},{tax_credit_amt:.0f}],
               type:'scatter',fill:'tonexty',name:'Tax Credits',fillcolor:'rgba(22,163,74,0.2)',line:{{color:'#16A34A'}}}}],
            {{...lo,margin:{{t:5,r:10,b:25,l:50}},xaxis:{{showgrid:false}},yaxis:{{showgrid:true,gridcolor:'#E5E5E5'}},
              showlegend:true,legend:{{font:{{size:8}},orientation:'h',y:-0.25}}}},cfg);

        // Territory mini charts
        var terrMonths = ['Jan','Feb','Mar','Apr','May','Jun'];
        var terrLo = {{margin:{{t:2,r:5,b:15,l:30}},paper_bgcolor:'transparent',plot_bgcolor:'transparent',
                       font:{{size:7,color:'#999'}},xaxis:{{showgrid:false,tickfont:{{size:7}}}},yaxis:{{showgrid:true,gridcolor:'#EEE',tickfont:{{size:7}}}},showlegend:false,height:80}};
        if(document.getElementById('chart-terr-0'))
            Plotly.newPlot('chart-terr-0',[{{x:terrMonths,y:[{loan*0.01:.0f},{loan*0.02:.0f},{loan*0.035:.0f},{loan*0.05:.0f},{loan*0.065:.0f},{loan*0.08:.0f}],
               type:'scatter',line:{{color:'#0052CC',width:1.5}}}}],terrLo,cfg);
        if(document.getElementById('chart-terr-1'))
            Plotly.newPlot('chart-terr-1',[{{x:terrMonths,y:[{loan*0.005:.0f},{loan*0.012:.0f},{loan*0.02:.0f},{loan*0.03:.0f},{loan*0.04:.0f},{loan*0.05:.0f}],
               type:'scatter',line:{{color:'#0052CC',width:1.5}}}}],terrLo,cfg);

        // Sold vs Unsold
        Plotly.newPlot('chart-deal-unsold',
            [{{x:months,y:[{total_unsold:.0f},{total_unsold*0.9:.0f},{total_unsold*0.75:.0f},{total_unsold*0.6:.0f},{total_unsold*0.45:.0f},{total_unsold*0.3:.0f}],
               type:'scatter',name:'Unsold',line:{{color:'#DC2626'}}}},
             {{x:months,y:[{total_sold*0.1:.0f},{total_sold*0.25:.0f},{total_sold*0.45:.0f},{total_sold*0.65:.0f},{total_sold*0.85:.0f},{total_sold:.0f}],
               type:'scatter',name:'Sold',line:{{color:'#0052CC'}}}}],
            {{...lo,margin:{{t:5,r:10,b:25,l:45}},xaxis:{{showgrid:false}},yaxis:{{showgrid:true,gridcolor:'#E5E5E5'}}}},cfg);

        // Capital Waterfall
        if(document.getElementById('chart-waterfall')) {{
            var wfX = ['Pre-Sales','Gap/Unsold','Tax Credits','Total Sources','Gross Loan','EP Fees','Interest Rsv','Net to Borrower'];
            var wfY = [{total_sold:.0f},{gap_val:.0f},{tax_credit_val:.0f},{total_sources:.0f},{loan:.0f},-{ep_fee_wf:.0f},-{interest_wf:.0f},{net_to_borrower:.0f}];
            var wfColors = wfY.map(function(v,i){{ return i===3?'#0052CC':i===7?'#16a34a':v<0?'#dc2626':'#3B82F6'; }});
            Plotly.newPlot('chart-waterfall',
                [{{x:wfX,y:wfY.map(Math.abs),type:'bar',marker:{{color:wfColors}},
                   text:wfY.map(function(v){{return v<0?'-$'+(Math.abs(v)/1e6).toFixed(1)+'M':'$'+(v/1e6).toFixed(1)+'M';}}),
                   textposition:'outside',textfont:{{size:9}}}}],
                {{...lo,margin:{{t:25,r:10,b:60,l:60}},xaxis:{{showgrid:false,tickangle:-30,tickfont:{{size:8}}}},
                  yaxis:{{showgrid:true,gridcolor:'#E5E5E5',tickfont:{{size:8}}}},showlegend:false}},cfg);
        }}
    }})();
    """)

    return Div(
        hero,
        Div(
            Div(overview, key_terms, collateral_receivables, sales_section, tax_incentives, waterfall, comms, cls="deal-main-col"),
            right_sidebar,
            cls="deal-detail-layout",
        ),
        chart_js,
        Div(
            A("\U0001f4ca Balance Sheet", href="#", cls="filter-chip", style="margin-right:.5rem;text-decoration:none;",
              onclick=f"loadModule('/module/accounting/balance/{deal_id}','Balance Sheet')"),
            Button("← Back to Deals", cls="filter-chip",
                   onclick="loadModule('/module/deals','Deals')"),
            style="margin:1rem 0;display:flex;align-items:center;gap:.5rem;",
        ),
        cls="module-content deal-detail-page",
    )


@rt("/module/deal/create", methods=["POST"])
def deal_create(session, title: str, status: str = "pipeline", project_type: str = "feature_film",
                genre: str = "", loan_amount: float = 0, currency: str = "USD",
                interest_rate: float = 0, term_months: int = 12,
                collateral_type: str = "Pre-Sales",
                origination_date: str = "", maturity_date: str = "",
                borrower_name: str = "", budget: float = 0,
                producer: str = "", director: str = "", cast_summary: str = "",
                territory: str = "", notes: str = ""):
    from sqlalchemy import text
    from utils.db import get_pool
    user_id = session.get("user_id")
    notes_json = json.dumps({"notes": notes}) if notes else None
    pool = get_pool()
    with pool.get_session() as s:
        s.execute(text("""
            INSERT INTO ahmf.deals (title, status, project_type, genre, loan_amount, currency,
                interest_rate, term_months, collateral_type, origination_date, maturity_date,
                borrower_name, budget, producer, director, cast_summary, territory, notes, created_by)
            VALUES (:title, :status, :type, :genre, :amount, :currency, :rate, :term,
                :collateral_type, :origination_date, :maturity_date, :borrower, :budget,
                :producer, :director, :cast, :territory, :notes, :uid)
        """), {
            "title": title, "status": status, "type": project_type, "genre": genre,
            "amount": loan_amount or None, "currency": currency,
            "rate": interest_rate or None, "term": term_months,
            "collateral_type": collateral_type,
            "origination_date": origination_date or None,
            "maturity_date": maturity_date or None,
            "borrower": borrower_name, "budget": budget or None,
            "producer": producer, "director": director, "cast": cast_summary,
            "territory": territory, "notes": notes_json, "uid": user_id,
        })
    if status in ('active', 'closed'):
        _create_notification(pool, None, f"Deal '{title}' moved to {status}",
                            f"Deal {title} ({genre}) with loan ${loan_amount:,.0f} is now {status}.", user_id)
    return module_deals(session)


@rt("/module/contacts")
def module_contacts(session, import_msg: str = ""):
    from sqlalchemy import text
    from utils.db import get_pool
    try:
        pool = get_pool()
        with pool.get_session() as s:
            contacts = s.execute(text("""
                SELECT c.contact_id, c.name, c.company, c.contact_type, c.email, c.phone,
                       cr.risk_tier
                FROM ahmf.contacts c
                LEFT JOIN ahmf.credit_ratings cr ON c.contact_id = cr.contact_id
                ORDER BY c.name LIMIT 50
            """)).fetchall()
    except Exception:
        contacts = []

    rows = []
    for c in contacts:
        cid = str(c[0])
        tier = c[6] or "—"
        rows.append(Tr(
            Td(A(c[1], href="#", onclick=f"loadModule('/module/contact/{cid}','Contacts — {c[1]}');return false;",
                 style="color:var(--blue);text-decoration:none;font-weight:500;")),
            Td(c[2] or "—"), Td((c[3] or "").replace("_", " ").title()),
            Td(tier), Td(c[4] or "—"), Td(c[5] or "—"),
            style="cursor:pointer;",
            onclick=f"loadModule('/module/contact/{cid}','Contacts — {c[1]}')",
        ))

    msg_banner = Div(P(import_msg, style="color:#16a34a;font-weight:500;"), style="margin-bottom:.75rem;") if import_msg else ""

    import_form = Form(
        Input(type="file", name="file", accept=".csv", style="font-size:.82rem;"),
        Button("Import", type="submit", cls="filter-chip", style="font-size:.82rem;"),
        style="display:inline-flex;align-items:center;gap:.5rem;",
        hx_post="/api/import/contacts", hx_target="#center-content", hx_swap="innerHTML",
        hx_encoding="multipart/form-data",
    )

    return Div(
        msg_banner,
        Div(
            H1("Contacts"),
            Div(
                A("⤓ CSV", href="/api/export/contacts", cls="filter-chip",
                  style="text-decoration:none;display:inline-flex;align-items:center;font-size:.82rem;"),
                import_form,
                Button("+ Add Contact", cls="auth-btn", hx_get="/module/contact/new", hx_target="#center-content", hx_swap="innerHTML"),
                style="display:flex;align-items:center;gap:.75rem;",
            ),
            style="display:flex;justify-content:space-between;align-items:center;",
        ),
        Table(
            Thead(Tr(Th("Name"), Th("Company"), Th("Type"), Th("Rating"), Th("Email"), Th("Phone"))),
            Tbody(*rows) if rows else Tbody(Tr(Td("No contacts yet.", colspan="6", style="text-align:center;padding:2rem;color:#64748b;"))),
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


@rt("/module/contact/{contact_id}")
def module_contact_detail(contact_id: str, session, tab: str = "details"):
    from sqlalchemy import text as sa_text
    from utils.db import get_pool
    pool = get_pool()
    with pool.get_session() as s:
        contact = s.execute(sa_text("""
            SELECT contact_id, name, company, role, email, phone, contact_type,
                   credit_score, notes, created_at
            FROM ahmf.contacts WHERE contact_id = :cid
        """), {"cid": contact_id}).fetchone()
    if not contact:
        return Div(P("Contact not found."), cls="module-content")

    cid = str(contact[0])
    name = contact[1] or "—"
    company = contact[2] or "—"
    role = contact[3] or "—"
    email = contact[4] or "—"
    phone = contact[5] or "—"
    ctype = (contact[6] or "other").replace("_", " ").title()
    notes = contact[8] or "—"

    tabs = ["Details", "Deals", "Communications", "Analytics"]
    tab_links = []
    for t in tabs:
        slug = t.lower()
        active = "contact-tab active" if slug == tab else "contact-tab"
        tab_links.append(
            A(t, href="#", cls=active,
              hx_get=f"/module/contact/{cid}/tab/{slug}",
              hx_target="#contact-tab-content", hx_swap="innerHTML",
              onclick="document.querySelectorAll('.contact-tab').forEach(t=>t.classList.remove('active'));this.classList.add('active');")
        )

    tab_content = _contact_tab_content(cid, tab, pool)

    return Div(
        Div(
            H1(f"{name}"),
            Div(Span(ctype, cls="status-pill", style="background:#E8F0FE;color:var(--blue);"),
                Span(company, style="color:var(--ink-muted);margin-left:.75rem;font-size:.9rem;"),
                style="display:flex;align-items:center;gap:.5rem;margin-top:.25rem;"),
            cls="contact-header",
        ),
        Div(*tab_links, cls="contact-tabs"),
        Div(tab_content, id="contact-tab-content"),
        Button("← Back to Contacts", cls="filter-chip", style="margin:1rem 0;",
               onclick="loadModule('/module/contacts','Contacts')"),
        cls="module-content",
    )


@rt("/module/contact/{contact_id}/tab/{tab}")
def contact_tab(contact_id: str, tab: str, session):
    from utils.db import get_pool
    pool = get_pool()
    return _contact_tab_content(contact_id, tab, pool)


def _contact_tab_content(contact_id, tab, pool):
    from sqlalchemy import text as sa_text
    import random
    random.seed(hash(contact_id) % 10000)

    if tab == "details":
        with pool.get_session() as s:
            c = s.execute(sa_text("""
                SELECT name, company, role, email, phone, contact_type, notes, created_at
                FROM ahmf.contacts WHERE contact_id = :cid
            """), {"cid": contact_id}).fetchone()
        if not c:
            return Div(P("Contact not found."))
        return Div(
            Div(
                Div(Div("Name", cls="detail-label"), Div(c[0] or "—", cls="detail-value"), cls="detail-row"),
                Div(Div("Company", cls="detail-label"), Div(c[1] or "—", cls="detail-value"), cls="detail-row"),
                Div(Div("Role", cls="detail-label"), Div(c[2] or "—", cls="detail-value"), cls="detail-row"),
                Div(Div("Type", cls="detail-label"), Div((c[5] or "").replace("_", " ").title(), cls="detail-value"), cls="detail-row"),
                Div(Div("Email", cls="detail-label"), Div(c[3] or "—", cls="detail-value"), cls="detail-row"),
                Div(Div("Phone", cls="detail-label"), Div(c[4] or "—", cls="detail-value"), cls="detail-row"),
                Div(Div("Notes", cls="detail-label"), Div(c[6] or "—", cls="detail-value"), cls="detail-row"),
                Div(Div("Created", cls="detail-label"), Div(str(c[7])[:10] if c[7] else "—", cls="detail-value"), cls="detail-row"),
                cls="contact-details-grid",
            ),
        )

    elif tab == "deals":
        with pool.get_session() as s:
            cr = s.execute(sa_text("""
                SELECT score, risk_tier FROM ahmf.credit_ratings WHERE contact_id = :cid LIMIT 1
            """), {"cid": contact_id}).fetchone()
            sc = s.execute(sa_text("""
                SELECT sc.deal_id, d.title, d.status, d.loan_amount, d.interest_rate, d.origination_date
                FROM ahmf.sales_contracts sc
                JOIN ahmf.deals d ON d.deal_id = sc.deal_id
                WHERE sc.distributor_id = :cid
                ORDER BY d.origination_date DESC
            """), {"cid": contact_id}).fetchall()

        deal_rows = []
        if sc:
            seen = set()
            for r in sc:
                did = str(r[0])
                if did in seen:
                    continue
                seen.add(did)
                st = r[2] or "pipeline"
                st_colors = {"active": "#16a34a", "closed": "#0052CC", "pipeline": "#F59E0B", "declined": "#dc2626"}
                sc_color = st_colors.get(st, "#64748b")
                deal_rows.append(Tr(
                    Td(A("↗", href="#", onclick=f"loadModule('/module/deal/{did}','{r[1]}');return false;",
                         style="color:var(--blue);text-decoration:none;")),
                    Td(did[:8].upper()),
                    Td(Span(st.title(), cls="status-pill", style=f"background:{sc_color}20;color:{sc_color};")),
                    Td(f"${float(r[3]):,.0f}" if r[3] else "—"),
                    Td(f"${float(r[3]) * 0.7:,.0f}" if r[3] else "—"),
                    Td(f"{float(r[4]):.1f}%" if r[4] else "—"),
                    Td(str(r[5])[:10] if r[5] else "—"),
                ))

        if not deal_rows:
            statuses = ["Complete", "Live", "Profit Sharing"]
            for i in range(8):
                st = random.choice(statuses)
                sc_color = {"Complete": "#16a34a", "Live": "#F59E0B", "Profit Sharing": "#0052CC"}.get(st, "#64748b")
                loan = random.randint(2, 8) * 500000
                deal_rows.append(Tr(
                    Td("↗", style="color:var(--blue);"),
                    Td(f"AH-{random.randint(1000,9999)}"),
                    Td(Span(st, cls="status-pill", style=f"background:{sc_color}20;color:{sc_color};")),
                    Td(f"${loan:,.0f}"),
                    Td(f"${int(loan * 0.65):,.0f}" if st != "Complete" else "—"),
                    Td(f"{random.uniform(12, 18):.1f}%"),
                    Td(f"2024-{random.randint(1,12):02d}-{random.randint(1,28):02d}"),
                ))

        with pool.get_session() as s:
            mg_stats = s.execute(sa_text("""
                SELECT COUNT(DISTINCT sc.deal_id), COALESCE(SUM(sc.mg_amount), 0)
                FROM ahmf.sales_contracts sc WHERE sc.distributor_id = :cid
            """), {"cid": contact_id}).fetchone()
        total_deal_count = mg_stats[0] if mg_stats else 0
        total_mg = float(mg_stats[1]) if mg_stats else 0

        stats_bar = Div(
            Div(Div("Total Deals", cls="kpi-label"), Div(str(total_deal_count), cls="kpi-value"), cls="kpi-card"),
            Div(Div("Total MG Value", cls="kpi-label"), Div(f"${total_mg:,.0f}", cls="kpi-value"), cls="kpi-card"),
            cls="kpi-grid", style="grid-template-columns:repeat(2,1fr);margin-bottom:1rem;",
        )

        return Div(
            stats_bar,
            Div(
                Button("⊕ New Report", cls="filter-chip"),
                Button("⊲ Filter", cls="filter-chip"),
                Button("⊞ List view", cls="filter-chip"),
                style="display:flex;gap:.5rem;justify-content:flex-end;margin-bottom:1rem;",
            ),
            Table(
                Thead(Tr(Th(""), Th("Deal ID"), Th("Status"), Th("Net Loan"), Th("Loan Balance"),
                         Th("IRR (Projected/Actual)"), Th("Funding Date"))),
                Tbody(*deal_rows),
            ),
        )

    elif tab == "communications":
        senders = ["Lewis Carter", "Mike Rossi", "Eddie Smith", "Will Turner", "Luke Ripley"]
        subjects = ["Production Meeting 8:30PM", "China's DA", "Inception — Here It Is!",
                     "Private & Confidential", "Production Trial Balance"]
        comm_rows = []
        for i in range(5):
            comm_rows.append(Tr(
                Td(Span("→", style="color:var(--blue);margin-right:.5rem;"), senders[i]),
                Td(subjects[i]),
                Td(f"2025-06-{18+i}"),
                Td("↗ ⭐ 🔗"),
            ))
        return Div(
            Table(
                Thead(Tr(Th("From"), Th("Subject"), Th("Date"), Th("Actions"))),
                Tbody(*comm_rows),
            ),
        )

    elif tab == "analytics":
        with pool.get_session() as s:
            cr = s.execute(sa_text("""
                SELECT score, risk_tier, payment_reliability, factors
                FROM ahmf.credit_ratings WHERE contact_id = :cid LIMIT 1
            """), {"cid": contact_id}).fetchone()

        score_val = float(cr[0]) if cr and cr[0] else random.uniform(60, 95)
        tier = cr[1] if cr else random.choice(["AAA", "AA", "A", "BBB"])
        total_deals = random.randint(5, 15)
        senior_pct = random.randint(50, 80)
        bridge_pct = random.randint(10, 30)
        live_pct = random.randint(10, 30)
        profit_pct = random.randint(30, 60)
        completed_pct = random.randint(20, 50)

        deals_labels = [f"Deal {i+1}" for i in range(7)]
        term_per_deal = [random.randint(8, 28) for _ in range(7)]
        term_avg = sum(term_per_deal) / len(term_per_deal)
        irr_per_deal = [round(random.uniform(6, 18), 1) for _ in range(7)]
        irr_avg = sum(irr_per_deal) / len(irr_per_deal)
        ep_fees = [random.randint(30000, 80000) for _ in range(7)]
        coprod_fees = [random.randint(10000, 40000) for _ in range(7)]
        other_fees = [random.randint(5000, 20000) for _ in range(7)]
        init_interest = [random.randint(200000, 600000) for _ in range(7)]
        special_interest = [random.randint(50000, 200000) for _ in range(7)]
        post_mat_interest = [random.randint(20000, 100000) for _ in range(7)]
        total_fee = sum(ep_fees) + sum(coprod_fees) + sum(other_fees)
        total_interest = sum(init_interest) + sum(special_interest) + sum(post_mat_interest)

        irr_max = max(irr_per_deal) + 5
        weighted_avg = [term_avg + random.uniform(-2, 2) for _ in range(7)]

        return Div(
            Div(
                Div(
                    Div("Credit Score", cls="kpi-label", style="font-size:.8rem;"),
                    Div(tier, style="font-size:2rem;font-weight:700;margin:.5rem 0;"),
                    Div("Deal History", style="font-size:.75rem;font-weight:600;color:var(--ink-muted);margin-top:1rem;"),
                    Div(
                        Div(Span("Total Deals", style="color:var(--ink-dim);"), Span(str(total_deals), style="font-weight:600;"), cls="sidebar-kv"),
                        Div(Span("Senior", style="color:var(--ink-dim);"), Span(f"{senior_pct}% ({int(total_deals*senior_pct/100)} deals)", style="font-size:.72rem;"), cls="sidebar-kv"),
                        Div(Span("Bridge", style="color:var(--ink-dim);"), Span(f"{bridge_pct}% ({int(total_deals*bridge_pct/100)} deals)", style="font-size:.72rem;"), cls="sidebar-kv"),
                        Div(Span("Live", style="color:var(--ink-dim);"), Span(f"{live_pct}% ({int(total_deals*live_pct/100)} deals)", style="font-size:.72rem;"), cls="sidebar-kv"),
                        Div(Span("Profit Sharing", style="color:var(--ink-dim);"), Span(f"{profit_pct}% ({int(total_deals*profit_pct/100)} deals)", style="font-size:.72rem;"), cls="sidebar-kv"),
                        Div(Span("Completed", style="color:var(--ink-dim);"), Span(f"{completed_pct}% ({int(total_deals*completed_pct/100)} deals)", style="font-size:.72rem;"), cls="sidebar-kv"),
                    ),
                    cls="chart-card", style="min-width:240px;",
                ),
                Div(
                    Div("Term", cls="kpi-label"),
                    Div(f"{term_avg:.0f} months", style="font-size:1.4rem;font-weight:700;"),
                    Div(f"↑ 3% (3 months)", style="font-size:.72rem;color:#16a34a;margin-bottom:.5rem;"),
                    Div("from last year", style="font-size:.66rem;color:var(--ink-dim);margin-bottom:.5rem;"),
                    Div(id="chart-ct-term", style="height:180px;"),
                    cls="chart-card", style="flex:2;",
                ),
                cls="charts-row", style="align-items:stretch;",
            ),
            Div(
                Div(
                    Div("IRR", cls="kpi-label"),
                    Div(f"{irr_avg:.1f}%", style="font-size:1.4rem;font-weight:700;"),
                    Div(f"↑ 3%", style="font-size:.72rem;color:#16a34a;display:inline;"),
                    Span(" from last deal", style="font-size:.66rem;color:var(--ink-dim);"),
                    Div(id="chart-ct-irr", style="height:180px;margin-top:.5rem;"),
                    cls="chart-card",
                ),
                cls="charts-row",
            ),
            Div(
                Div(
                    Div("Fee", cls="kpi-label"),
                    Div(f"${total_fee:,.0f}", style="font-size:1.4rem;font-weight:700;"),
                    Div(id="chart-ct-fee", style="height:180px;margin-top:.5rem;"),
                    cls="chart-card",
                ),
                Div(
                    Div("Interest (Collected)", cls="kpi-label"),
                    Div(f"${total_interest:,.0f}", style="font-size:1.4rem;font-weight:700;"),
                    Div(id="chart-ct-interest", style="height:180px;margin-top:.5rem;"),
                    cls="chart-card",
                ),
                cls="charts-row",
            ),
            Script(f"""
            (function() {{
                var cfg = {{displayModeBar:false,responsive:true}};
                var lo = {{margin:{{t:10,r:15,b:30,l:40}},paper_bgcolor:'transparent',plot_bgcolor:'transparent',
                           font:{{size:9,color:'#999'}},xaxis:{{showgrid:false}},yaxis:{{showgrid:true,gridcolor:'#E5E5E5'}},
                           showlegend:true,legend:{{font:{{size:8}},orientation:'h',y:1.12}}}};
                var deals = {deals_labels};

                // Term chart
                Plotly.newPlot('chart-ct-term',
                    [{{x:deals,y:{term_per_deal},type:'scatter',name:'Per Deal',mode:'lines+markers',
                       line:{{color:'#0052CC',width:2}},marker:{{size:6}}}},
                     {{x:deals,y:{[round(w,1) for w in weighted_avg]},type:'scatter',name:'Weighted Average',
                       mode:'lines+markers',line:{{color:'#16A34A',width:2,dash:'dot'}},marker:{{size:5,symbol:'diamond'}}}}],
                    lo,cfg);

                // IRR chart
                var irrLo = {{...lo,shapes:[
                    {{type:'line',y0:{irr_max:.0f},y1:{irr_max:.0f},x0:0,x1:6,xref:'x',yref:'y',line:{{color:'#dc2626',width:1,dash:'dash'}}}},
                    {{type:'line',y0:5,y1:5,x0:0,x1:6,xref:'x',yref:'y',line:{{color:'#dc2626',width:1,dash:'dash'}}}}
                ]}};
                Plotly.newPlot('chart-ct-irr',
                    [{{x:deals,y:{irr_per_deal},type:'scatter',mode:'lines',line:{{color:'#0052CC',width:2}}}}],
                    irrLo,cfg);

                // Fee chart
                Plotly.newPlot('chart-ct-fee',
                    [{{x:deals,y:{ep_fees},type:'bar',name:'EP fees',marker:{{color:'#0052CC'}}}},
                     {{x:deals,y:{coprod_fees},type:'bar',name:'Co-producer/producer fees',marker:{{color:'#3B82F6'}}}},
                     {{x:deals,y:{other_fees},type:'bar',name:'Other fees',marker:{{color:'#93C5FD'}}}}],
                    {{...lo,barmode:'group'}},cfg);

                // Interest chart
                Plotly.newPlot('chart-ct-interest',
                    [{{x:deals,y:{init_interest},type:'bar',name:'Initial Interest',marker:{{color:'#0052CC'}}}},
                     {{x:deals,y:{special_interest},type:'bar',name:'Special Interest',marker:{{color:'#3B82F6'}}}},
                     {{x:deals,y:{post_mat_interest},type:'bar',name:'Post-Maturity Interest',marker:{{color:'#93C5FD'}}}}],
                    {{...lo,barmode:'group'}},cfg);
            }})();
            """),
        )

    return Div(P("Unknown tab."))


# Product 1 sub-module routes registered below via register_routes()

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
from modules.guide import register_routes as guide_routes
from modules.sales import register_routes as sales_routes
from modules.credit import register_routes as credit_routes
from modules.accounting import register_routes as accounting_routes
from modules.comms import register_routes as comms_routes
from modules.scoring import register_routes as scoring_routes

risk_routes(rt)
budget_routes(rt)
schedule_routes(rt)
funding_routes(rt)
dataroom_routes(rt)
audience_routes(rt)
talent_routes(rt)
guide_routes(rt)
sales_routes(rt)
credit_routes(rt)
accounting_routes(rt)
comms_routes(rt)
scoring_routes(rt)


# ---------------------------------------------------------------------------
# Main Page
# ---------------------------------------------------------------------------

@rt("/")
def index(request, session, new: str = "", thread: str = ""):
    _check_clerk_session(request, session)
    if not session.get("user_id"):
        from modules.landing import landing_page
        return landing_page()

    if new == "1":
        thread_id = str(_uuid.uuid4())
        session["thread_id"] = thread_id
    elif thread:
        thread_id = thread
        session["thread_id"] = thread_id
    else:
        thread_id = session.get("thread_id")
        if not thread_id:
            thread_id = str(_uuid.uuid4())
            session["thread_id"] = thread_id

    user = {
        "user_id": session.get("user_id"),
        "email": session.get("email"),
        "display_name": session.get("display_name", "User"),
    }

    return (
        Title("Monika — Ashland Hill Media Finance"),
        Link(rel="stylesheet", href="/static/app.css?v=3"),
        Div(
            Div(id="left-overlay", cls="left-overlay", onclick="toggleLeftPane()"),
            _left_pane(user),
            Div(
                Div(
                    Div(
                        Button("☰", cls="mobile-menu-btn", onclick="toggleLeftPane()"),
                        Span("Home", cls="page-title", id="center-title"),
                        cls="page-header-left",
                    ),
                    Div(
                        Input(type="text", placeholder="Search...", cls="header-search"),
                        cls="page-header-right",
                    ),
                    cls="page-header",
                ),
                Div(id="center-content", cls="module-content",
                    hx_get="/module/home", hx_trigger="load", hx_swap="innerHTML",
                    style="overflow-y:auto;flex:1;"),
                Div(agui.chat(thread_id), cls="center-chat", id="center-chat", style="display:none;"),
                cls="center-pane",
            ),
            _right_pane(),
            cls="app-layout",
        ),
        Script(src="/static/chat.js?v=4"),
    )


@rt("/agui-conv/list")
def conv_list(session):
    """Return conversation list for sidebar."""
    current_tid = session.get("thread_id", "")
    user_id = session.get("user_id")
    try:
        # Show user's conversations + unassigned ones
        convs = list_conversations(user_id=user_id, limit=15)
        if not convs:
            convs = list_conversations(user_id=None, limit=15)
    except Exception:
        convs = []
    if not convs:
        return Div(Span("No conversations yet", style="font-size:0.75rem;color:#94a3b8;padding:0.5rem;"))
    items = []
    for c in convs:
        tid = c["thread_id"]
        title = c.get("first_msg") or c.get("title") or "New chat"
        if len(title) > 35:
            title = title[:35] + "..."
        cls = "conv-item conv-active" if tid == current_tid else "conv-item"
        items.append(A(title, href=f"/?thread={tid}", cls=cls))
    return Div(*items)


# ---------------------------------------------------------------------------
# Serve
# ---------------------------------------------------------------------------

serve(port=int(os.environ.get("PORT", 5010)))
