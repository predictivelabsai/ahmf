"""
Product 4: Smart Budgeting Tool

Dynamic budgeting — AI generates production budgets with 3 scenarios (low/mid/high).
"""

import os, json, logging
from fasthtml.common import *
from sqlalchemy import text
from utils.db import get_pool
from config.settings import GENRES, VFX_LEVELS, CAST_TIERS, BUDGET_CATEGORIES, BUDGET_GROUPS

logger = logging.getLogger(__name__)


def _get_llm():
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1",
                      model="grok-3-mini", temperature=0.3)


def generate_budget_tool(title: str, genre: str = "Drama", locations: str = "",
                         cast_tier: str = "Mid-Level", vfx_level: str = "Light",
                         shoot_days: str = "30") -> str:
    """Generate a 3-scenario production budget for a film project. Returns budget breakdown by department."""
    llm = _get_llm()
    cats = ", ".join(BUDGET_CATEGORIES)
    prompt = f"""You are a film production budget expert. Generate a production budget with 3 scenarios for this project.

Project: {title} | Genre: {genre} | Cast Tier: {cast_tier}
VFX Level: {vfx_level} | Locations: {locations} | Shoot Days: {shoot_days}

Return ONLY valid JSON:
{{
  "scenarios": {{
    "low": {{"total": <number>, "items": [{{"category": "<category>", "subcategory": "<line item detail>", "amount": <number>}}, ...]}},
    "mid": {{"total": <number>, "items": [...]}},
    "high": {{"total": <number>, "items": [...]}}
  }},
  "summary": "<2 sentence budget analysis>"
}}

Use these industry-standard categories grouped as:
  ATL (Above-the-Line): Story & Rights, Producer, Director, Cast
  BTL (Below-the-Line): Extras, Production Staff, Art Department, Set Construction, Props, Wardrobe, Makeup & Hair, Grip & Electrical, Camera, Sound, Transportation, Locations, Catering
  Post-Production: Visual Effects, Music, Post-Production Picture, Post-Production Sound
  Other: Insurance, Legal, Financing Costs, Publicity, Contingency, Overhead/Fee

Include 15-20 line items per scenario covering all groups."""
    try:
        resp = llm.invoke(prompt)
        content = resp.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(content)
        scenarios = data.get("scenarios", {})
        summary = data.get("summary", "")

        lines = [f"## Budget Estimate: {title}\n", summary, ""]
        for scenario in ["low", "mid", "high"]:
            sc = scenarios.get(scenario, {})
            total = sc.get("total", 0)
            lines.append(f"### {scenario.upper()} Scenario — ${total:,.0f}")
            lines.append("| Category | Item | Amount |")
            lines.append("|----------|------|--------|")
            for item in sc.get("items", []):
                lines.append(f"| {item.get('category', '')} | {item.get('subcategory', '')} | ${item.get('amount', 0):,.0f} |")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"Error generating budget: {e}"


def register_routes(rt):

    @rt("/module/budget")
    def module_budget(session):
        pool = get_pool()
        with pool.get_session() as s:
            budgets = s.execute(text("""
                SELECT budget_id, title, scenario, total_amount, created_at
                FROM ahmf.budgets ORDER BY created_at DESC LIMIT 20
            """)).fetchall()

        rows = []
        for b in budgets:
            rows.append(Div(
                Div(Span(b[1], cls="deal-card-title"),
                    Span(f"${b[3]:,.0f}" if b[3] else "—", style="font-weight:700;color:#0066cc;font-size:0.85rem;"),
                    style="display:flex;justify-content:space-between;align-items:center;"),
                Div(f"{(b[2] or 'mid').upper()} scenario | {b[4].strftime('%b %d, %Y') if b[4] else ''}", cls="deal-card-meta"),
                cls="deal-card",
                hx_get=f"/module/budget/{b[0]}", hx_target="#center-content", hx_swap="innerHTML",
            ))

        return Div(
            Div(H1("Smart Budgeting"), Button("+ Generate Budget", cls="auth-btn",
                hx_get="/module/budget/new", hx_target="#center-content", hx_swap="innerHTML"),
                style="display:flex;justify-content:space-between;align-items:center;"),
            P("AI-powered budget generation with low/mid/high scenarios.", style="color:#64748b;margin-bottom:1.5rem;"),
            Div(*rows) if rows else P("No budgets yet.", style="color:#94a3b8;text-align:center;padding:2rem;"),
            cls="module-content",
        )

    @rt("/module/budget/new")
    def budget_new(session):
        return Div(
            H1("Generate Production Budget"),
            Form(
                Div(Div(Label("Project Title", Input(type="text", name="title", required=True)), style="flex:1"),
                    Div(Label("Genre", Select(*[Option(g, value=g) for g in GENRES], name="genre")), style="flex:1"),
                    style="display:flex;gap:1rem;"),
                Div(Div(Label("Cast Tier", Select(*[Option(c, value=c) for c in CAST_TIERS], name="cast_tier")), style="flex:1"),
                    Div(Label("VFX Level", Select(*[Option(v, value=v) for v in VFX_LEVELS], name="vfx_level")), style="flex:1"),
                    Div(Label("Shoot Days", Input(type="number", name="shoot_days", value="30")), style="flex:1"),
                    style="display:flex;gap:1rem;"),
                Label("Locations", Input(type="text", name="locations", placeholder="e.g. Los Angeles, New Zealand")),
                Button("Generate Budget", type="submit", cls="auth-btn"),
                cls="auth-form",
                hx_post="/module/budget/generate", hx_target="#center-content", hx_swap="innerHTML",
            ),
            cls="module-content",
        )

    @rt("/module/budget/generate", methods=["POST"])
    def budget_generate(session, title: str, genre: str = "Drama", cast_tier: str = "Mid-Level",
                        vfx_level: str = "Light", shoot_days: str = "30", locations: str = ""):
        llm = _get_llm()
        prompt = f"""You are a film production budget expert. Generate a production budget with 3 scenarios.

Project: {title} | Genre: {genre} | Cast Tier: {cast_tier}
VFX Level: {vfx_level} | Locations: {locations} | Shoot Days: {shoot_days}

Return ONLY valid JSON:
{{"scenarios": {{"low": {{"total": <number>, "items": [{{"category": "<category>", "subcategory": "<line item detail>", "amount": <number>}}]}}, "mid": {{"total": ..., "items": [...]}}, "high": {{"total": ..., "items": [...]}}}}, "summary": "..."}}

Use these industry-standard categories grouped as:
  ATL (Above-the-Line): Story & Rights, Producer, Director, Cast
  BTL (Below-the-Line): Extras, Production Staff, Art Department, Set Construction, Props, Wardrobe, Makeup & Hair, Grip & Electrical, Camera, Sound, Transportation, Locations, Catering
  Post-Production: Visual Effects, Music, Post-Production Picture, Post-Production Sound
  Other: Insurance, Legal, Financing Costs, Publicity, Contingency, Overhead/Fee
Include 15-20 items per scenario covering all groups."""
        try:
            resp = llm.invoke(prompt)
            content = resp.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            data = json.loads(content)
        except Exception as e:
            return Div(H1("Error"), P(f"AI analysis failed: {e}"), cls="module-content")

        scenarios = data.get("scenarios", {})
        summary = data.get("summary", "")
        params = json.dumps({"genre": genre, "cast_tier": cast_tier, "vfx_level": vfx_level,
                              "locations": locations, "shoot_days": shoot_days})

        # Persist all 3 scenarios
        pool = get_pool()
        for sc_name in ["low", "mid", "high"]:
            sc = scenarios.get(sc_name, {})
            with pool.get_session() as s:
                s.execute(text("""
                    INSERT INTO ahmf.budgets (title, project_params, scenario, total_amount, breakdown, analysis_text, created_by)
                    VALUES (:title, :params, :sc, :total, :breakdown, :summary, :uid)
                """), {"title": title, "params": params, "sc": sc_name, "total": sc.get("total", 0),
                       "breakdown": json.dumps(sc.get("items", [])), "summary": summary, "uid": session.get("user_id")})

        # Render results with ATL/BTL/Post/Other grouping
        scenario_tabs = []
        for sc_name in ["low", "mid", "high"]:
            sc = scenarios.get(sc_name, {})
            items = sc.get("items", [])
            grouped_rows = []
            for group_name, group_cats in BUDGET_GROUPS.items():
                group_items = [i for i in items if i.get("category", "") in group_cats]
                if group_items:
                    group_total = sum(i.get("amount", 0) for i in group_items)
                    grouped_rows.append(Tr(
                        Td(B(group_name), colspan="2", style="background:#f1f5f9;padding:0.5rem;"),
                        Td(B(f"${group_total:,.0f}"), style="text-align:right;background:#f1f5f9;padding:0.5rem;"),
                    ))
                    for i in group_items:
                        grouped_rows.append(Tr(
                            Td(i.get("category", ""), style="padding-left:1.5rem;color:#64748b;"),
                            Td(i.get("subcategory", "")),
                            Td(f"${i.get('amount', 0):,.0f}", style="text-align:right;"),
                        ))
            # Any items not matching known groups
            ungrouped = [i for i in items if i.get("category", "") not in
                         [c for cats in BUDGET_GROUPS.values() for c in cats]]
            if ungrouped:
                for i in ungrouped:
                    grouped_rows.append(Tr(Td(i.get("category", "")), Td(i.get("subcategory", "")),
                                           Td(f"${i.get('amount', 0):,.0f}", style="text-align:right;")))
            scenario_tabs.append(Div(
                H2(f"{sc_name.upper()} — ${sc.get('total', 0):,.0f}", style="margin-top:1.5rem;"),
                Table(
                    Thead(Tr(Th("Category"), Th("Item"), Th("Amount", style="text-align:right;"))),
                    Tbody(*grouped_rows),
                    style="width:100%;border-collapse:collapse;font-size:0.85rem;",
                ),
            ))

        return Div(
            H1(f"Budget: {title}"),
            P(summary, style="color:#475569;margin-bottom:1rem;"),
            Div(
                Div(Div("Low", cls="stat-label"), Div(f"${scenarios.get('low', {}).get('total', 0):,.0f}", cls="stat-value", style="color:#16a34a;"), cls="stat-card"),
                Div(Div("Mid", cls="stat-label"), Div(f"${scenarios.get('mid', {}).get('total', 0):,.0f}", cls="stat-value", style="color:#0066cc;"), cls="stat-card"),
                Div(Div("High", cls="stat-label"), Div(f"${scenarios.get('high', {}).get('total', 0):,.0f}", cls="stat-value", style="color:#dc2626;"), cls="stat-card"),
                cls="stats-grid",
            ),
            *scenario_tabs,
            Button("Back", cls="auth-btn", style="margin-top:1.5rem;", onclick="loadModule('/module/budget', 'Smart Budget')"),
            cls="module-content",
        )

    @rt("/module/budget/{budget_id}")
    def budget_detail(budget_id: str, session):
        pool = get_pool()
        with pool.get_session() as s:
            row = s.execute(text("""
                SELECT title, scenario, total_amount, breakdown, analysis_text FROM ahmf.budgets WHERE budget_id = :bid
            """), {"bid": budget_id}).fetchone()
        if not row:
            return Div(P("Budget not found."), cls="module-content")
        title, scenario, total, breakdown_json, summary = row
        items = breakdown_json if isinstance(breakdown_json, list) else json.loads(breakdown_json or "[]")
        grouped_rows = []
        for group_name, group_cats in BUDGET_GROUPS.items():
            group_items = [i for i in items if i.get("category", "") in group_cats]
            if group_items:
                group_total = sum(i.get("amount", 0) for i in group_items)
                grouped_rows.append(Tr(
                    Td(B(group_name), colspan="2", style="background:#f1f5f9;padding:0.5rem;"),
                    Td(B(f"${group_total:,.0f}"), style="text-align:right;background:#f1f5f9;padding:0.5rem;"),
                ))
                for i in group_items:
                    grouped_rows.append(Tr(
                        Td(i.get("category", ""), style="padding-left:1.5rem;color:#64748b;"),
                        Td(i.get("subcategory", "")),
                        Td(f"${i.get('amount', 0):,.0f}", style="text-align:right;"),
                    ))
        ungrouped = [i for i in items if i.get("category", "") not in
                     [c for cats in BUDGET_GROUPS.values() for c in cats]]
        for i in ungrouped:
            grouped_rows.append(Tr(Td(i.get("category", "")), Td(i.get("subcategory", "")),
                                   Td(f"${i.get('amount', 0):,.0f}", style="text-align:right;")))
        return Div(
            H1(f"Budget: {title}"),
            Div(Div(Div("Scenario", cls="stat-label"), Div(scenario.upper(), cls="stat-value"), cls="stat-card"),
                Div(Div("Total", cls="stat-label"), Div(f"${total:,.0f}" if total else "—", cls="stat-value"), cls="stat-card"),
                cls="stats-grid"),
            P(summary or "", style="color:#475569;margin:1rem 0;"),
            Table(Thead(Tr(Th("Category"), Th("Item"), Th("Amount", style="text-align:right;"))),
                  Tbody(*grouped_rows), style="width:100%;border-collapse:collapse;font-size:0.85rem;"),
            Button("Back", cls="auth-btn", style="margin-top:1.5rem;", onclick="loadModule('/module/budget', 'Smart Budget')"),
            cls="module-content",
        )
