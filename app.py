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

from agents.registry import AGENTS, AGENTS_BY_SLUG, AGENTS_BY_CATEGORY, CATEGORIES


# ---------------------------------------------------------------------------
# Layout Components
# ---------------------------------------------------------------------------

def _agent_browser():
    """Left-pane browser of all agents, grouped by category."""
    groups = []
    for cat in CATEGORIES:
        agents = AGENTS_BY_CATEGORY.get(cat["key"], [])
        buttons = [
            Button(
                Span(a.icon, cls="aitem-icon"),
                Span(a.name, cls="aitem-name"),
                Span(a.prefix, cls="aitem-prefix"),
                cls="agent-item",
                onclick=f"fillChat({a.prefix + ' '!r})",
                title=a.one_liner,
            )
            for a in agents
        ]
        groups.append(Div(
            Button(
                Span(cat["icon"], cls="cat-icon"),
                Span(cat["name"], cls="cat-name"),
                Span(f"{len(agents)}", cls="cat-count"),
                Span("▸", cls="cat-arrow"),
                cls="cat-toggle",
                onclick=f"toggleGroup('cat-{cat['key']}')",
                id=f"btn-cat-{cat['key']}",
            ),
            Div(*buttons, cls="agent-list", id=f"cat-{cat['key']}"),
            cls="agent-group",
        ))
    return Div(*groups, cls="agent-browser")


def _bottom_nav():
    items = [
        ("Pipeline", "/module/pipeline", "◆"),
        ("User Guide", "#", "✎"),
    ]
    links = []
    for label, href, icon in items:
        onclick = f"loadModule('{href}', '{label}')" if not href.startswith("http") and href != "#" else ""
        if label == "User Guide":
            onclick = "loadModule('/module/guide', 'User Guide')"
        links.append(A(
            Span(icon, cls="bottom-nav-icon"),
            Span(label, cls="bottom-nav-label"),
            href="#",
            onclick=onclick,
            cls="bottom-nav-link",
        ))
    return Div(*links, cls="bottom-nav")


def _sample_cards():
    """Gemini-style sample-question cards below the chat input."""
    prompts = [
        "deal:list",
        "estimate: revenue for a $15M horror film with Florence Pugh",
        "risk: analyze a $20M action film shooting in Georgia",
        "budget: generate for a $15M drama, 35 days in NYC",
        "talent:search Florence Pugh",
        "incentives",
    ]
    chips = [
        Button(
            Span(p, cls="sample-card-text"),
            cls="sample-card",
            onclick=f"fillAndSend({p!r})",
            title=p,
        )
        for p in prompts
    ]
    return Div(
        Div(
            Span("Try a prompt", cls="sample-cards-label"),
            id="sample-cards-label",
        ),
        Div(*chips, id="sample-cards-row", cls="sample-cards-row"),
        id="sample-cards",
        cls="sample-cards",
    )


def _left_pane(user=None):
    user_email = user.get("email", "") if user else None
    display = user.get("display_name", "User") if user else None

    signin_block = (
        Div(
            Span("◇", style="color:var(--accent);"),
            Span(user_email or display, style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:500;font-size:.72rem;"),
            Button("Sign out", style="font-size:.62rem;padding:.15rem .4rem;background:transparent;border:1px solid var(--line-br);border-radius:.3rem;color:var(--ink-dim);cursor:pointer;",
                   onclick="window.location.href='/logout'"),
            style="display:flex;align-items:center;gap:.4rem;",
        )
        if user else
        Button("Sign in", onclick="window.location.href='/login'",
               style="width:100%;padding:.4rem;background:transparent;border:1px solid var(--line-br);border-radius:.45rem;color:var(--ink-muted);cursor:pointer;font-size:.72rem;")
    )

    return Div(
        Div(
            A(Span("◐", cls="brand-mark"), Span("Monika"),
              href="/", cls="brand-link"),
            Span("Beta", cls="brand-badge"),
            cls="left-header",
        ),
        Div(
            # Sessions section
            Div(
                Button("+ New chat", cls="new-chat-btn", onclick="window.location.href='/?new=1'"),
                Div(Span("Sessions", cls="section-label")),
                Div(id="conv-list", hx_get="/agui-conv/list", hx_trigger="load", hx_swap="innerHTML"),
                cls="sessions-section",
            ),
            Hr(cls="left-hr"),
            # Agents section
            Div(
                Div(Span("Agents", cls="section-label")),
                _agent_browser(),
                cls="agents-section",
            ),
            Hr(cls="left-hr"),
            # Workspace section
            Div(
                Div(Span("Workspace", cls="section-label")),
                _bottom_nav(),
                cls="workspace-section",
            ),
            cls="left-body",
        ),
        Div(signin_block, cls="left-footer"),
        cls="left-pane",
    )


def _right_pane():
    """Canvas pane — starts empty; filled by agent artifacts."""
    return Div(
        Div(
            Div(H3("Canvas", cls="right-title"),
                Span("", id="artifact-subtitle", cls="right-subtitle"),
                cls="right-header-left"),
            Button("✕", cls="right-close", onclick="toggleArtifactPane()"),
            cls="right-header",
        ),
        Div(
            Div(
                Div("◈", cls="artifact-empty-icon"),
                P("Canvas renders here as agents produce artifacts — deal briefs, risk scores, budget tables, sales estimates.",
                  cls="artifact-empty-text"),
                id="artifact-empty",
                cls="artifact-empty",
            ),
            Div(id="artifact-body", cls="artifact-body", style="display:none"),
            cls="right-body",
        ),
        id="right-pane", cls="right-pane",
    )


# ---------------------------------------------------------------------------
# Auth Routes
# ---------------------------------------------------------------------------

@rt("/login", methods=["GET"])
def login_page(session):
    if session.get("user_id"):
        return RedirectResponse("/", status_code=303)
    return Titled(
        "Monika — Login",
        Link(rel="stylesheet", href="/static/app.css"),
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
            "Monika — Login",
            Link(rel="stylesheet", href="/static/app.css"),
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
def register_page(session):
    if session.get("user_id"):
        return RedirectResponse("/", status_code=303)
    return Titled(
        "Monika — Register",
        Link(rel="stylesheet", href="/static/app.css"),
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
            Link(rel="stylesheet", href="/static/app.css"),
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

PIPELINE_STAGES = [
    ("pipeline",  "Pipeline"),
    ("active",    "Active"),
    ("approved",  "Approved"),
    ("funded",    "Funded"),
    ("closed",    "Closed"),
    ("declined",  "Declined"),
]

STAGE_COLORS = {
    "pipeline":  "#C89B5B",
    "active":    "#4A8E66",
    "approved":  "#2F7151",
    "funded":    "#1F5D43",
    "closed":    "#6B4E2F",
    "declined":  "#9C8F7A",
}


def _pipeline_card(deal, sym="$"):
    title = deal[1]
    status = deal[2] or "pipeline"
    amount = deal[3]
    borrower = deal[4] or "—"
    genre = deal[5] or ""
    amt_str = f"{sym}{float(amount)/1_000_000:.1f}M" if amount else "—"

    status_colors = {"pipeline": "#C89B5B", "active": "#4A8E66", "approved": "#2F7151",
                     "funded": "#1F5D43", "closed": "#6B4E2F", "declined": "#9C8F7A"}
    heat = status_colors.get(status, "#CFC8B4")

    return Div(
        Div(
            Div(
                Span(cls="heat-dot", style=f"background:{heat}"),
                Span(title, cls="card-title"),
                cls="card-head",
            ),
            Div(
                Span(genre.replace("_", " ").title() if genre else borrower,
                     cls="card-sub"),
                cls="card-meta",
            ),
            Div(
                Span(f"{amt_str} loan", cls="card-metric") if amount else Span("—", cls="card-metric"),
                Span("·"),
                Span(borrower, cls="card-metric"),
                cls="card-metrics-line",
            ),
            cls="pipeline-deal-card",
        ),
        hx_get=f"/module/deal/{deal[0]}",
        hx_target="#center-content",
        hx_swap="innerHTML",
        style="cursor:pointer;",
    )


@rt("/module/pipeline")
def module_pipeline(session, status_filter: str = ""):
    from sqlalchemy import text
    from utils.db import get_pool
    try:
        pool = get_pool()
        with pool.get_session() as s:
            rows = s.execute(text("""
                SELECT deal_id, title, status, loan_amount, borrower_name, genre
                FROM ahmf.deals ORDER BY status, created_at DESC
            """)).fetchall()
    except Exception:
        rows = []

    by_stage: dict[str, list] = {}
    for r in rows:
        stage = r[2] or "pipeline"
        by_stage.setdefault(stage, []).append(r)

    columns = []
    for stage_key, stage_label in PIPELINE_STAGES:
        cards = by_stage.get(stage_key, [])
        columns.append(Div(
            Div(
                Span(stage_label, cls="col-title"),
                Span(str(len(cards)), cls="col-count"),
                cls="col-head",
                style=f"border-bottom-color:{STAGE_COLORS.get(stage_key, '#CFC8B4')}",
            ),
            Div(*[_pipeline_card(c) for c in cards], cls="col-body"),
            cls="kanban-col",
        ))

    filters = Div(
        Button("All", cls=f"filter-chip{' active' if not status_filter else ''}",
               hx_get="/module/pipeline", hx_target="#center-content", hx_swap="innerHTML"),
        *[Button(label, cls=f"filter-chip{' active' if status_filter == key else ''}",
                 hx_get=f"/module/pipeline?status_filter={key}", hx_target="#center-content", hx_swap="innerHTML")
          for key, label in PIPELINE_STAGES],
        cls="pipeline-filters",
    )

    return Div(
        filters,
        Div(*columns, cls="kanban-board"),
        Div(
            Button("+ New Deal", cls="auth-btn", hx_get="/module/deal/new", hx_target="#center-content", hx_swap="innerHTML"),
            style="padding:0.75rem 1.1rem;",
        ),
        cls="pipeline-center",
    )


@rt("/module/deals")
def module_deals(session):
    return module_pipeline(session)


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
def index(session, new: str = "", thread: str = ""):
    if not session.get("user_id"):
        from modules.landing import landing_page
        return landing_page()

    # New chat: generate fresh thread
    if new == "1":
        thread_id = str(_uuid.uuid4())
        session["thread_id"] = thread_id
    elif thread:
        # Resume specific thread
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
        Link(rel="stylesheet", href="/static/app.css"),
        Div(
            Div(id="left-overlay", cls="left-overlay", onclick="toggleLeftPane()"),
            _left_pane(user),
            Div(
                Div(
                    Div(
                        Button("☰", cls="mobile-menu-btn", onclick="toggleLeftPane()"),
                        Span("Monika", cls="chat-header-title", id="center-title"),
                        Span("·", cls="chat-header-dot"),
                        Span("AI Chat", cls="chat-header-agent"),
                        cls="chat-header-left",
                    ),
                    Div(
                        Button("Copy chat", id="copy-chat-btn", cls="chat-action-btn",
                               onclick="copyChat()"),
                        Button("Share", id="share-chat-btn", cls="chat-action-btn",
                               onclick="shareChat()"),
                        Button("Canvas", id="artifact-btn", cls="artifact-toggle-btn",
                               onclick="toggleArtifactPane()"),
                        cls="chat-header-actions",
                    ),
                    cls="chat-header",
                ),
                Div(id="center-content", cls="module-content", style="display:none;overflow-y:auto;flex:1;"),
                Div(agui.chat(thread_id), cls="center-chat", id="center-chat"),
                _sample_cards(),
                cls="center-pane",
            ),
            _right_pane(),
            cls="app-layout pane-closed",
        ),
        Script(src="/static/chat.js"),
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
