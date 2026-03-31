"""
Product 6: Soft Funding Discovery Engine

"Kayak for film incentives" — searchable database of global tax incentives
with rebate calculator and deal linking.
"""

import json, logging
from fasthtml.common import *
from sqlalchemy import text
from utils.db import get_pool

logger = logging.getLogger(__name__)


def search_incentives_tool(country: str = "", incentive_type: str = "", query: str = "") -> str:
    """Search the global film incentive database by country, type, or keyword."""
    pool = get_pool()
    with pool.get_session() as s:
        conditions = ["is_active = TRUE"]
        params = {}
        if country:
            conditions.append("country ILIKE :country")
            params["country"] = f"%{country}%"
        if incentive_type:
            conditions.append("incentive_type ILIKE :itype")
            params["itype"] = f"%{incentive_type}%"
        if query:
            conditions.append("(name ILIKE :q OR region ILIKE :q OR eligibility ILIKE :q)")
            params["q"] = f"%{query}%"
        where = " AND ".join(conditions)
        rows = s.execute(text(f"""
            SELECT name, country, region, incentive_type, rebate_percent, min_spend, avg_processing_days, notes
            FROM ahmf.incentive_programs WHERE {where} ORDER BY rebate_percent DESC LIMIT 15
        """), params).fetchall()
    if not rows:
        return "No matching incentive programs found."
    lines = ["## Incentive Programs\n", "| Program | Country | Type | Rebate | Min Spend | Processing |",
             "|---------|---------|------|--------|-----------|------------|"]
    for r in rows:
        spend = f"${r[5]:,.0f}" if r[5] else "None"
        lines.append(f"| {r[0]} | {r[1]} ({r[2]}) | {r[3]} | {r[4]}% | {spend} | ~{r[6] or '?'} days |")
    return "\n".join(lines)


def register_routes(rt):

    @rt("/module/funding")
    def module_funding(session):
        pool = get_pool()
        with pool.get_session() as s:
            programs = s.execute(text("""
                SELECT program_id, name, country, region, incentive_type, rebate_percent, min_spend, avg_processing_days
                FROM ahmf.incentive_programs WHERE is_active = TRUE ORDER BY rebate_percent DESC
            """)).fetchall()
            total = len(programs)
            countries = len(set(p[2] for p in programs))
            avg_rebate = sum(p[5] for p in programs) / total if total else 0

        program_rows = [Tr(
            Td(p[1]), Td(f"{p[2]} ({p[3]})"), Td(p[4].replace("_", " ").title() if p[4] else ""),
            Td(f"{p[5]}%", style="font-weight:600;color:#16a34a;"), Td(f"${p[6]:,.0f}" if p[6] else "—"),
            Td(f"~{p[7]} days" if p[7] else "—"),
        ) for p in programs]

        return Div(
            H1("Soft Funding Discovery"),
            P("Centralized database of global tax incentives and public funding programs.", style="color:#64748b;margin-bottom:1.5rem;"),
            Div(
                Div(Div("Programs", cls="stat-label"), Div(str(total), cls="stat-value"), cls="stat-card"),
                Div(Div("Countries", cls="stat-label"), Div(str(countries), cls="stat-value"), cls="stat-card"),
                Div(Div("Avg Rebate", cls="stat-label"), Div(f"{avg_rebate:.1f}%", cls="stat-value", style="color:#16a34a;"), cls="stat-card"),
                cls="stats-grid",
            ),
            # Search
            Form(
                Div(
                    Div(Input(type="text", name="country", placeholder="Country..."), style="flex:1"),
                    Div(Select(Option("All Types", value=""), Option("Tax Credit", value="tax_credit"),
                               Option("Cash Rebate", value="cash_rebate"), Option("Tax Relief", value="tax_relief"),
                               Option("Tax Offset", value="tax_offset"), Option("Grant", value="grant"),
                               Option("Tax Rebate", value="tax_rebate"), name="incentive_type"), style="flex:1"),
                    Button("Search", type="submit", cls="auth-btn"),
                    style="display:flex;gap:0.5rem;align-items:end;",
                ),
                hx_get="/module/funding/search", hx_target="#incentive-results", hx_swap="innerHTML",
                style="margin-bottom:1rem;",
            ),
            # Rebate calculator
            Div(
                H2("Rebate Calculator", style="font-size:1rem;"),
                Form(
                    Div(
                        Div(Input(type="number", name="spend", placeholder="Qualifying spend ($)", style="width:100%;"), style="flex:1"),
                        Div(Input(type="number", name="rebate_pct", placeholder="Rebate %", step="0.1", style="width:100%;"), style="flex:1"),
                        Button("Calculate", type="submit", cls="auth-btn"),
                        style="display:flex;gap:0.5rem;align-items:end;",
                    ),
                    hx_get="/module/funding/calc", hx_target="#calc-result", hx_swap="innerHTML",
                ),
                Div(id="calc-result", style="margin-top:0.5rem;"),
                style="padding:1rem;background:#f8fafc;border-radius:12px;border:1px solid #e2e8f0;margin-bottom:1.5rem;",
            ),
            Div(
                Table(
                    Thead(Tr(Th("Program"), Th("Location"), Th("Type"), Th("Rebate"), Th("Min Spend"), Th("Processing"))),
                    Tbody(*program_rows),
                    style="width:100%;border-collapse:collapse;font-size:0.8rem;",
                ),
                id="incentive-results",
            ),
            cls="module-content",
        )

    @rt("/module/funding/search")
    def funding_search(country: str = "", incentive_type: str = "", session=None):
        pool = get_pool()
        with pool.get_session() as s:
            conditions = ["is_active = TRUE"]
            params = {}
            if country:
                conditions.append("(country ILIKE :c OR region ILIKE :c)")
                params["c"] = f"%{country}%"
            if incentive_type:
                conditions.append("incentive_type = :t")
                params["t"] = incentive_type
            where = " AND ".join(conditions)
            programs = s.execute(text(f"""
                SELECT name, country, region, incentive_type, rebate_percent, min_spend, avg_processing_days
                FROM ahmf.incentive_programs WHERE {where} ORDER BY rebate_percent DESC
            """), params).fetchall()

        if not programs:
            return P("No programs match your criteria.", style="color:#94a3b8;text-align:center;padding:1rem;")

        rows = [Tr(Td(p[0]), Td(f"{p[1]} ({p[2]})"), Td(p[3].replace("_", " ").title() if p[3] else ""),
                   Td(f"{p[4]}%", style="font-weight:600;color:#16a34a;"), Td(f"${p[5]:,.0f}" if p[5] else "—"),
                   Td(f"~{p[6]} days" if p[6] else "—")) for p in programs]
        return Table(
            Thead(Tr(Th("Program"), Th("Location"), Th("Type"), Th("Rebate"), Th("Min Spend"), Th("Processing"))),
            Tbody(*rows), style="width:100%;border-collapse:collapse;font-size:0.8rem;",
        )

    @rt("/module/funding/calc")
    def funding_calc(spend: float = 0, rebate_pct: float = 0, session=None):
        if not spend or not rebate_pct:
            return P("Enter qualifying spend and rebate percentage.", style="color:#94a3b8;font-size:0.85rem;")
        rebate = spend * (rebate_pct / 100)
        return Div(
            Span(f"Estimated rebate: ", style="color:#475569;"),
            Span(f"${rebate:,.0f}", style="font-weight:700;color:#16a34a;font-size:1.1rem;"),
            Span(f" ({rebate_pct}% of ${spend:,.0f})", style="color:#94a3b8;font-size:0.85rem;"),
        )
