"""Central registry of Monika's film-finance AI agent categories.

Defines agent groups for the sidebar browser and sample-card prompts.
Each AgentSpec maps to one of the existing LangGraph tools.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AgentSpec:
    slug: str
    name: str
    category: str
    icon: str
    one_liner: str
    prefix: str
    example_prompts: tuple[str, ...] = field(default_factory=tuple)


CATEGORIES: list[dict] = [
    {
        "key": "sourcing",
        "name": "Deal Sourcing & Screening",
        "icon": "◉",
    },
    {
        "key": "underwriting",
        "name": "Film Underwriting Engine",
        "icon": "◈",
    },
    {
        "key": "diligence",
        "name": "Production & Diligence",
        "icon": "◆",
    },
    {
        "key": "capital",
        "name": "Market & Talent Intel",
        "icon": "◐",
    },
    {
        "key": "operations",
        "name": "Slate Operations",
        "icon": "◼",
    },
]

AGENTS: tuple[AgentSpec, ...] = (
    # Deal Sourcing & Screening
    AgentSpec(
        slug="deal_search", name="Deal Search",
        category="sourcing", icon="✓", prefix="deals:",
        one_liner="Search and browse the deal pipeline.",
        example_prompts=(
            "deal:list",
            "deals: show me all active deals",
            "deals: find horror films in pipeline",
            "deal:1",
        ),
    ),
    AgentSpec(
        slug="portfolio_overview", name="Portfolio Overview",
        category="sourcing", icon="∑", prefix="portfolio:",
        one_liner="Aggregate portfolio statistics and loan exposure.",
        example_prompts=(
            "portfolio",
            "portfolio: what's our total committed amount?",
            "portfolio: break down deals by status",
            "portfolio: show exposure by genre",
        ),
    ),
    AgentSpec(
        slug="contact_search", name="Contact Search",
        category="sourcing", icon="✉", prefix="contacts:",
        one_liner="Search distributors, producers, agents and financiers.",
        example_prompts=(
            "contact:search Distributor",
            "contacts: find all producers",
            "contacts: who is at Lionsgate?",
            "contacts: search sales agents in Europe",
        ),
    ),

    # Film Underwriting Engine
    AgentSpec(
        slug="sales_estimate", name="Sales Estimates",
        category="underwriting", icon="≡", prefix="estimate:",
        one_liner="TMDB/OMDB comp analysis with territory MG projections.",
        example_prompts=(
            "estimate: revenue for a $15M horror film with Florence Pugh",
            "estimate:new",
            "estimate: project MGs for a $25M action film across 20 territories",
            "estimate: compare revenue comps for mid-budget sci-fi",
        ),
    ),
    AgentSpec(
        slug="risk_scoring", name="Risk Scoring",
        category="underwriting", icon="⚠", prefix="risk:",
        one_liner="AI scores 6 risk dimensions (0-100) with mitigations.",
        example_prompts=(
            "risk: analyze a $20M action film shooting in Georgia with heavy VFX",
            "risk:new",
            "risk: score production risk for a period drama in the UK",
            "risk: evaluate risk for an indie horror with first-time director",
        ),
    ),
    AgentSpec(
        slug="smart_budget", name="Smart Budget",
        category="underwriting", icon="▤", prefix="budget:",
        one_liner="AI generates low/mid/high budget scenarios with line items.",
        example_prompts=(
            "budget: generate for a $15M drama with A-list cast, 35 days in NYC",
            "budget:new",
            "budget: create a $5M horror budget for 20-day shoot",
            "budget: low/mid/high scenarios for a $30M action film",
        ),
    ),
    AgentSpec(
        slug="credit_rating", name="Credit Rating",
        category="underwriting", icon="◈", prefix="credit:",
        one_liner="Counterparty credit ratings and ML-based scoring.",
        example_prompts=(
            "credit:Lionsgate",
            "credit: look up rating for A24",
            "credit: score StudioCanal counterparty risk",
            "credit: what's the credit profile of our top distributors?",
        ),
    ),

    # Production & Diligence
    AgentSpec(
        slug="data_room", name="Data Room",
        category="diligence", icon="☷", prefix="dataroom:",
        one_liner="Per-deal closing checklists and document tracking.",
        example_prompts=(
            "dataroom: generate closing checklist for deal 1",
            "dataroom: what documents are missing for the horror deal?",
            "dataroom: status of closing items across active deals",
            "dataroom: create document checklist for a new pre-sales deal",
        ),
    ),
    AgentSpec(
        slug="scheduling", name="Scheduling",
        category="diligence", icon="⌂", prefix="schedule:",
        one_liner="AI-generated day-by-day shooting schedules.",
        example_prompts=(
            "schedule: create a 25-day shooting schedule for a thriller at 3 locations",
            "schedule:new",
            "schedule: plan a 30-day shoot across NYC and Atlanta",
            "schedule: optimize a 20-day indie shoot for weather windows",
        ),
    ),
    AgentSpec(
        slug="soft_funding", name="Soft Funding",
        category="diligence", icon="◰", prefix="incentives:",
        one_liner="16+ global incentive programs and rebate calculator.",
        example_prompts=(
            "incentives",
            "incentives: what tax credits are available for shooting in Georgia?",
            "incentives: compare UK vs Canada vs Australia rebates",
            "incentives: find best incentive for a $20M film shooting 40 days",
        ),
    ),

    # Market & Talent Intel
    AgentSpec(
        slug="movie_search", name="Movie Search",
        category="capital", icon="⚯", prefix="tmdb:",
        one_liner="TMDB/OMDB search for comparable titles and market data.",
        example_prompts=(
            "tmdb: search for recent horror films",
            "tmdb: find films similar to A Quiet Place",
            "tmdb: box office data for Blumhouse productions",
            "tmdb: compare budget vs revenue for mid-budget thrillers",
        ),
    ),
    AgentSpec(
        slug="talent_intel", name="Talent Intel",
        category="capital", icon="↗", prefix="talent:",
        one_liner="Actor/director search with heat, fit and ROI scores.",
        example_prompts=(
            "talent:search Florence Pugh",
            "talent: find rising horror directors",
            "talent: who are the hottest actors for action films right now?",
            "talent: compare box office draw of Chris Hemsworth vs Oscar Isaac",
        ),
    ),
    AgentSpec(
        slug="audience_intel", name="Audience Intel",
        category="capital", icon="∿", prefix="audience:",
        one_liner="AI-predicted audience segments and marketing strategy.",
        example_prompts=(
            "audience: analyze target audience for a $30M sci-fi film",
            "audience:new",
            "audience: marketing channel strategy for indie horror",
            "audience: predict demographic breakdown for a family drama",
        ),
    ),

    # Slate Operations
    AgentSpec(
        slug="sales_contracts", name="Sales & Collections",
        category="operations", icon="Δ", prefix="sales:",
        one_liner="Sales contracts, MG tracking and collections.",
        example_prompts=(
            "sales:list",
            "sales: show overdue collections",
            "sales: list contracts expiring this quarter",
            "sales: MG status across active deals",
        ),
    ),
    AgentSpec(
        slug="accounting", name="Accounting",
        category="operations", icon="⚒", prefix="txns:",
        one_liner="Transaction ledger and financial operations.",
        example_prompts=(
            "transactions",
            "txns: show recent disbursements",
            "txns: list all interest payments this month",
            "txns: reconciliation status for active loans",
        ),
    ),
    AgentSpec(
        slug="communications", name="Communications",
        category="operations", icon="∠", prefix="messages:",
        one_liner="Messages, tasks and internal communications.",
        example_prompts=(
            "messages",
            "messages: show open tasks",
            "messages: unread messages this week",
            "messages: task status for deal closings",
        ),
    ),
)

AGENTS_BY_SLUG: dict[str, AgentSpec] = {a.slug: a for a in AGENTS}
AGENTS_BY_CATEGORY: dict[str, list[AgentSpec]] = {}
for a in AGENTS:
    AGENTS_BY_CATEGORY.setdefault(a.category, []).append(a)
