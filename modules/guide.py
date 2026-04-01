"""
User Guide — in-app navigable walkthrough of all AHMF features.

Screenshots are served from static/guide/ directory.
"""

from fasthtml.common import *


GUIDE_SECTIONS = [
    {
        "id": "overview",
        "title": "Platform Overview",
        "content": (
            "Ashland Hill Media Finance (AHMF) is a centralized, AI-driven operating system "
            "purpose-built for film financing. It replaces fragmented spreadsheets and siloed "
            "workflows with a unified data architecture, covering the full lifecycle of film "
            "financing transactions from origination to collections and portfolio analytics."
        ),
        "screenshot": "01_welcome.png",
        "caption": "The AI Chat welcome screen with quick-action cards for common workflows.",
    },
    {
        "id": "chat",
        "title": "AI Chat Assistant",
        "content": (
            "The AI Chat is your intelligent co-pilot. Ask questions in natural language or use "
            "structured commands. The assistant has access to your deal data, contacts, TMDB/OMDB "
            "movie databases, and all AI analysis tools. Type `help` to see available commands."
        ),
        "screenshot": "15_chat_help.png",
        "caption": "The help command shows all available structured commands.",
        "commands": [
            ("`deal:list`", "View all deals in your pipeline"),
            ("`portfolio`", "Aggregate portfolio statistics"),
            ("`contact:search NAME`", "Search your contact database"),
            ("`incentives`", "Search global film tax incentives"),
            ("`talent:search NAME`", "Look up actors/directors via TMDB"),
            ("`help`", "Show all available commands"),
        ],
    },
    {
        "id": "deals",
        "title": "Deal Pipeline",
        "content": (
            "The Deals module is the core of the Film Financing OS. Track every deal from "
            "pipeline through active to closed. Each deal captures loan terms, project details, "
            "borrower information, and key creative attachments (producer, director, cast)."
        ),
        "screenshot": "02_deals.png",
        "caption": "Deal Pipeline dashboard with stats cards and recent deals.",
    },
    {
        "id": "deal-new",
        "title": "Creating a Deal",
        "content": (
            "Create new deals with comprehensive project information: title, genre, project type, "
            "loan amount, interest rate, term, budget, and creative attachments. Deals flow through "
            "Pipeline > Active > Closed statuses."
        ),
        "screenshot": "03_deal_new.png",
        "caption": "New Deal form with all fields for structuring a financing transaction.",
    },
    {
        "id": "contacts",
        "title": "Contacts",
        "content": (
            "Manage your network of distributors, producers, sales agents, investors, and legal "
            "contacts. Each contact is typed and can be linked to multiple deals for relationship "
            "intelligence."
        ),
        "screenshot": "04_contacts.png",
        "caption": "Contacts list with company, type, and contact details.",
    },
    {
        "id": "sales",
        "title": "Sales & Collections",
        "content": (
            "Track territory-based sales contracts linked to deals and distributors. Monitor "
            "minimum guarantee (MG) commitments, record collection payments, and flag overdue "
            "receivables. The variance analysis shows projected vs actual collections per contract."
        ),
        "screenshot": "05_sales.png",
        "caption": "Sales & Collections dashboard with contract stats, MG tracking, and collection status.",
    },
    {
        "id": "credit",
        "title": "Credit Rating",
        "content": (
            "AI-powered counterparty strength assessment. Select any contact (distributor, producer, "
            "sales agent) and generate a credit score (0-100), payment reliability rating, risk tier "
            "(AAA through CCC), and detailed factor breakdown covering track record, financial "
            "stability, market position, and payment history."
        ),
        "screenshot": "17_credit.png",
        "caption": "Credit Rating dashboard with AI-generated counterparty scoring.",
    },
    {
        "id": "accounting",
        "title": "Accounting",
        "content": (
            "Full transaction ledger tracking disbursements, repayments, fees, and interest across "
            "all deals. Multi-currency support with net position calculation. Each transaction links "
            "to a deal and counterparty with reference notes for audit trail."
        ),
        "screenshot": "18_accounting.png",
        "caption": "Accounting module with transaction ledger, disbursement/repayment tracking, and net position.",
    },
    {
        "id": "comms",
        "title": "Communications",
        "content": (
            "Deal-linked messaging and task management. Create notes, tasks with due dates, and "
            "notifications tied to specific deals. Tasks have interactive checkboxes to mark "
            "completion, with overdue flagging for missed deadlines."
        ),
        "screenshot": "19_comms.png",
        "caption": "Communications module with messages, tasks, and deadline tracking.",
    },
    {
        "id": "estimates",
        "title": "Sales Estimates Generator",
        "content": (
            "Upload a script or enter project details to receive AI-powered revenue projections. "
            "The system benchmarks against comparable films using TMDB and OMDB data, generating "
            "territory-level MG estimates, box office forecasts, and confidence scores."
        ),
        "screenshot": "06_estimates.png",
        "caption": "Sales Estimates module with AI-powered revenue projection tools.",
    },
    {
        "id": "risk",
        "title": "Production Risk Scoring",
        "content": (
            "The AI risk engine evaluates execution risk across 6 dimensions: Script Complexity, "
            "Budget Feasibility, Schedule Risk, Jurisdictional Risk, Crew/Talent Risk, and "
            "Completion Risk. Each project receives an overall score (0-100) and risk tier "
            "(Low/Moderate/Elevated/High) with specific mitigation recommendations."
        ),
        "screenshot": "08_risk_form.png",
        "caption": "Risk assessment input form with project parameters.",
    },
    {
        "id": "budget",
        "title": "Smart Budgeting",
        "content": (
            "AI generates production budgets with three scenarios (Low/Mid/High) based on "
            "genre, cast tier, VFX level, shooting days, and locations. Each scenario includes "
            "detailed line items across Above-the-Line, Below-the-Line, Post, Insurance, and "
            "Contingency categories."
        ),
        "screenshot": "09_budget.png",
        "caption": "Smart Budgeting module for AI-generated 3-scenario budgets.",
    },
    {
        "id": "schedule",
        "title": "Production Scheduling",
        "content": (
            "Generate optimized day-by-day shooting schedules with AI-powered location clustering. "
            "The system minimizes company moves, groups day/night scenes, and accounts for actor "
            "availability and labor constraints."
        ),
        "screenshot": "10_schedule.png",
        "caption": "Production Scheduling with AI-optimized location clustering.",
    },
    {
        "id": "funding",
        "title": "Soft Funding Discovery",
        "content": (
            "Search a database of 16+ global film tax incentive programs across 11 countries. "
            "Filter by country and incentive type, use the rebate calculator to estimate returns, "
            "and link incentive programs to your deals."
        ),
        "screenshot": "04_funding.png",
        "caption": "Soft Funding Discovery with searchable incentive database and rebate calculator.",
    },
    {
        "id": "dataroom",
        "title": "Deal Closing & Data Room",
        "content": (
            "Manage the closing process for each deal with auto-generated checklists covering "
            "Legal, Insurance, Financial, Distribution, Tax Incentives, and Compliance categories. "
            "Track progress with interactive checkboxes and monitor document status."
        ),
        "screenshot": "13_checklist.png",
        "caption": "Closing checklist with 20 items across 6 categories, interactive progress tracking.",
    },
    {
        "id": "audience",
        "title": "Audience & Marketing Intelligence",
        "content": (
            "AI analyzes target audience segments, predicts demographics and psychographics, "
            "recommends marketing channel allocation and spend levels, and optimizes release "
            "strategy including domestic timing, international rollout, and festival positioning."
        ),
        "screenshot": "11_audience.png",
        "caption": "Audience Intelligence module for AI-powered marketing analysis.",
    },
    {
        "id": "talent",
        "title": "Talent Intelligence",
        "content": (
            "Search actors and directors using live TMDB data. Run AI-powered talent analysis "
            "to get cast recommendations scored by heat index (market popularity), genre fit, "
            "salary tier, and international sales impact. Simulate cast packages to project "
            "revenue combinations."
        ),
        "screenshot": "14_talent_search.png",
        "caption": "Talent Intelligence with TMDB-powered actor search and AI cast recommendations.",
    },
]


def register_routes(rt):

    @rt("/module/guide")
    def module_guide(session):
        toc_items = [
            A(
                s["title"],
                href=f"#guide-{s['id']}",
                style="display:block;padding:0.35rem 0;color:#0066cc;font-size:0.85rem;text-decoration:none;",
                onclick=f"document.getElementById('guide-{s['id']}').scrollIntoView({{behavior:'smooth'}});return false;",
            )
            for s in GUIDE_SECTIONS
        ]

        sections = []
        for s in GUIDE_SECTIONS:
            children = [
                H2(s["title"], style="margin-bottom:0.5rem;"),
                P(s["content"], style="color:#475569;margin-bottom:1rem;line-height:1.6;"),
            ]

            if s.get("commands"):
                cmd_rows = [
                    Tr(Td(NotStr(cmd), style="font-family:monospace;"), Td(desc, style="color:#475569;"))
                    for cmd, desc in s["commands"]
                ]
                children.append(Table(
                    Thead(Tr(Th("Command"), Th("Description"))),
                    Tbody(*cmd_rows),
                    style="width:100%;border-collapse:collapse;font-size:0.85rem;margin-bottom:1rem;",
                ))

            children.append(Div(
                Img(src=f"/static/guide/{s['screenshot']}", alt=s["caption"],
                    style="width:100%;border-radius:8px;border:1px solid #e2e8f0;"),
                P(s["caption"], style="font-size:0.75rem;color:#94a3b8;text-align:center;margin-top:0.5rem;font-style:italic;"),
                style="margin-bottom:2rem;",
            ))

            sections.append(Div(*children, id=f"guide-{s['id']}", style="margin-bottom:2.5rem;padding-bottom:1.5rem;border-bottom:1px solid #f1f5f9;"))

        return Div(
            H1("User Guide"),
            P("Complete walkthrough of all AHMF platform features.", style="color:#64748b;margin-bottom:1.5rem;"),
            # Table of contents
            Div(
                H3("Contents", style="font-size:0.9rem;margin-bottom:0.5rem;"),
                *toc_items,
                style="padding:1rem;background:#f8fafc;border-radius:12px;border:1px solid #e2e8f0;margin-bottom:2rem;",
            ),
            # Sections
            *sections,
            cls="module-content",
        )
