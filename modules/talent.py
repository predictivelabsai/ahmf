"""
Product 9: Talent Intelligence

AI-powered cast recommendations using TMDB data, tonal fit analysis,
heat index, ROI correlation, and package simulation.
"""

import os, json, logging
from fasthtml.common import *
from sqlalchemy import text
from utils.db import get_pool
from config.settings import GENRES

logger = logging.getLogger(__name__)


def _get_llm():
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1",
                      model="grok-3-mini", temperature=0.4)


def search_talent_tool(query: str) -> str:
    """Search for actors/directors using TMDB. Returns name, popularity, and known-for titles."""
    from utils.tmdb_util import search_people
    try:
        results = search_people(query, limit=8)
        if not results:
            return f"No talent found for '{query}'."
        lines = [f"## Talent Search: {query}\n",
                 "| Name | Popularity | Known For |", "|------|------------|-----------|"]
        for p in results:
            known = ", ".join(f"{k['title']} ({k['year']})" for k in p.get("known_for", []) if k.get("title"))
            lines.append(f"| {p['name']} | {p['popularity']:.0f} | {known} |")
        return "\n".join(lines)
    except Exception as e:
        return f"Error searching talent: {e}"


def analyze_talent_tool(title: str, genre: str = "Drama", tone: str = "",
                        budget: str = "", roles: str = "") -> str:
    """Recommend cast for a film project based on genre, tone, budget fit, and market heat."""
    from utils.tmdb_util import search_people
    llm = _get_llm()
    prompt = f"""You are a film casting and talent intelligence expert. Recommend cast for this project.

Project: {title} | Genre: {genre} | Tone: {tone} | Budget: {budget}
Roles Needed: {roles}

For each recommendation, provide:
- Actor name, why they fit, a comparable role they've done
- Heat score (1-10 based on current market popularity)
- Genre fit score (1-10)
- Estimated salary tier (Low/Mid/High/Premium)
- International sales impact (Low/Mid/High)

Return ONLY valid JSON:
{{
  "recommendations": [
    {{
      "name": "...",
      "role": "...",
      "why_fit": "...",
      "comparable_role": "...",
      "heat_score": <int 1-10>,
      "genre_fit": <int 1-10>,
      "salary_tier": "Mid",
      "intl_impact": "High"
    }}
  ],
  "package_sims": [
    {{"combo": "Actor A + Actor B", "projected_domestic": "...", "projected_intl": "...", "chemistry_notes": "..."}}
  ],
  "summary": "..."
}}

Recommend 5-8 actors and 2-3 package combinations."""
    try:
        resp = llm.invoke(prompt)
        content = resp.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(content)
        recs = data.get("recommendations", [])
        packages = data.get("package_sims", [])
        summary = data.get("summary", "")

        lines = [f"## Talent Recommendations: {title}\n", summary, "",
                 "| Actor | Role | Heat | Fit | Salary | Intl Impact | Why |",
                 "|-------|------|------|-----|--------|-------------|-----|"]
        for r in recs:
            lines.append(f"| {r.get('name','')} | {r.get('role','')} | {r.get('heat_score','')}/10 | {r.get('genre_fit','')}/10 | {r.get('salary_tier','')} | {r.get('intl_impact','')} | {r.get('why_fit','')} |")
        if packages:
            lines.append("\n### Package Simulations")
            for p in packages:
                lines.append(f"- **{p.get('combo','')}**: Domestic {p.get('projected_domestic','?')}, Intl {p.get('projected_intl','?')} — {p.get('chemistry_notes','')}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error analyzing talent: {e}"


def register_routes(rt):

    @rt("/module/talent")
    def module_talent(session):
        pool = get_pool()
        with pool.get_session() as s:
            reports = s.execute(text("""
                SELECT report_id, title, created_at FROM ahmf.talent_reports ORDER BY created_at DESC LIMIT 20
            """)).fetchall()
        rows = [Div(
            Span(r[1], cls="deal-card-title"),
            Div(r[2].strftime('%b %d, %Y') if r[2] else '', cls="deal-card-meta"),
            cls="deal-card", hx_get=f"/module/talent/{r[0]}", hx_target="#center-content", hx_swap="innerHTML",
        ) for r in reports]

        return Div(
            Div(H1("Talent Intelligence"),
                Button("+ New Analysis", cls="auth-btn", hx_get="/module/talent/new", hx_target="#center-content", hx_swap="innerHTML"),
                style="display:flex;justify-content:space-between;align-items:center;"),
            P("AI-powered cast recommendations with heat index, genre fit, and package simulation.", style="color:#64748b;margin-bottom:1.5rem;"),
            # Quick talent search
            Div(
                H2("Quick Search", style="font-size:1rem;"),
                Form(
                    Div(Input(type="text", name="query", placeholder="Search actor or director...", style="flex:1;"),
                        Button("Search", type="submit", cls="auth-btn"),
                        style="display:flex;gap:0.5rem;"),
                    hx_get="/module/talent/search", hx_target="#talent-search-results", hx_swap="innerHTML",
                ),
                Div(id="talent-search-results", style="margin-top:0.5rem;"),
                style="padding:1rem;background:#f8fafc;border-radius:12px;border:1px solid #e2e8f0;margin-bottom:1.5rem;",
            ),
            Div(*rows) if rows else P("No reports yet.", style="color:#94a3b8;text-align:center;padding:2rem;"),
            cls="module-content",
        )

    @rt("/module/talent/search")
    def talent_search(query: str = "", session=None):
        if not query:
            return P("Enter a name to search.", style="color:#94a3b8;font-size:0.85rem;")
        from utils.tmdb_util import search_people
        try:
            results = search_people(query, limit=6)
        except Exception as e:
            return P(f"Error: {e}", style="color:#dc2626;font-size:0.85rem;")
        if not results:
            return P(f"No results for '{query}'.", style="color:#94a3b8;font-size:0.85rem;")
        cards = []
        for p in results:
            known = ", ".join(f"{k['title']}" for k in p.get("known_for", []) if k.get("title"))
            cards.append(Div(
                Div(Span(p["name"], style="font-weight:600;"), Span(f" — {p.get('known_for_department', '')}", style="color:#64748b;font-size:0.8rem;")),
                Div(f"Popularity: {p['popularity']:.0f} | Known for: {known}", style="font-size:0.75rem;color:#475569;"),
                style="padding:0.5rem;border:1px solid #e2e8f0;border-radius:6px;margin-bottom:0.3rem;",
            ))
        return Div(*cards)

    @rt("/module/talent/new")
    def talent_new(session):
        return Div(
            H1("New Talent Analysis"),
            Form(
                Div(Div(Label("Project Title", Input(type="text", name="title", required=True)), style="flex:1"),
                    Div(Label("Genre", Select(*[Option(g, value=g) for g in GENRES], name="genre")), style="flex:1"),
                    style="display:flex;gap:1rem;"),
                Div(Div(Label("Tone / Style", Input(type="text", name="tone", placeholder="e.g. Dark, grounded, cerebral")), style="flex:1"),
                    Div(Label("Budget", Input(type="text", name="budget", placeholder="e.g. $25M")), style="flex:1"),
                    style="display:flex;gap:1rem;"),
                Label("Roles Needed", Textarea(name="roles", rows="3", placeholder="e.g. Male lead (40s, ex-military), Female lead (30s, journalist), Villain (50s, corporate exec)",
                      style="width:100%;padding:0.5rem;border:1px solid #e2e8f0;border-radius:8px;font-family:inherit;")),
                Button("Analyze Talent", type="submit", cls="auth-btn"),
                cls="auth-form", hx_post="/module/talent/analyze", hx_target="#center-content", hx_swap="innerHTML",
            ),
            cls="module-content",
        )

    @rt("/module/talent/analyze", methods=["POST"])
    def talent_analyze(session, title: str, genre: str = "Drama", tone: str = "",
                       budget: str = "", roles: str = ""):
        llm = _get_llm()
        prompt = f"""You are a film casting expert. Recommend cast for this project.

Project: {title} | Genre: {genre} | Tone: {tone} | Budget: {budget}
Roles: {roles}

Return ONLY valid JSON:
{{"recommendations": [{{"name": "...", "role": "...", "why_fit": "...", "comparable_role": "...", "heat_score": <1-10>, "genre_fit": <1-10>, "salary_tier": "Mid", "intl_impact": "High"}}], "package_sims": [{{"combo": "...", "projected_domestic": "...", "projected_intl": "...", "chemistry_notes": "..."}}], "summary": "..."}}

5-8 actors, 2-3 packages."""
        try:
            resp = llm.invoke(prompt)
            content = resp.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            data = json.loads(content)
        except Exception as e:
            return Div(H1("Error"), P(f"AI analysis failed: {e}"), cls="module-content")

        recs = data.get("recommendations", [])
        packages = data.get("package_sims", [])
        summary = data.get("summary", "")

        pool = get_pool()
        with pool.get_session() as s:
            s.execute(text("""
                INSERT INTO ahmf.talent_reports (title, project_params, recommendations, package_sims, analysis_text, created_by)
                VALUES (:title, :params, :recs, :pkgs, :summary, :uid)
            """), {"title": title, "params": json.dumps({"genre": genre, "tone": tone, "budget": budget, "roles": roles}),
                   "recs": json.dumps(recs), "pkgs": json.dumps(packages), "summary": summary, "uid": session.get("user_id")})

        def _heat_color(score):
            if score >= 8: return "#dc2626"
            if score >= 6: return "#f59e0b"
            return "#16a34a"

        rec_cards = []
        for r in recs:
            heat = r.get("heat_score", 5)
            fit = r.get("genre_fit", 5)
            rec_cards.append(Div(
                Div(
                    Span(r.get("name", ""), style="font-weight:700;font-size:0.95rem;"),
                    Span(f" as {r.get('role', '')}", style="color:#64748b;"),
                    style="margin-bottom:0.3rem;",
                ),
                Div(
                    Span(f"Heat: {heat}/10", style=f"color:{_heat_color(heat)};font-weight:600;margin-right:1rem;font-size:0.8rem;"),
                    Span(f"Fit: {fit}/10", style="color:#0066cc;font-weight:600;margin-right:1rem;font-size:0.8rem;"),
                    Span(f"Salary: {r.get('salary_tier', '?')}", style="color:#475569;margin-right:1rem;font-size:0.8rem;"),
                    Span(f"Intl: {r.get('intl_impact', '?')}", style="color:#475569;font-size:0.8rem;"),
                ),
                Div(r.get("why_fit", ""), style="font-size:0.8rem;color:#475569;margin-top:0.2rem;"),
                Div(f"Comparable: {r.get('comparable_role', '')}", style="font-size:0.75rem;color:#94a3b8;font-style:italic;"),
                style="padding:0.75rem;border:1px solid #e2e8f0;border-radius:10px;margin-bottom:0.5rem;",
            ))

        pkg_els = [Div(
            Div(Span(p.get("combo", ""), style="font-weight:600;"), style="margin-bottom:0.2rem;"),
            Div(f"Domestic: {p.get('projected_domestic', '?')} | International: {p.get('projected_intl', '?')}",
                style="font-size:0.8rem;color:#475569;"),
            Div(p.get("chemistry_notes", ""), style="font-size:0.75rem;color:#64748b;font-style:italic;"),
            style="padding:0.75rem;border:1px solid #e2e8f0;border-radius:10px;margin-bottom:0.5rem;background:#f8fafc;",
        ) for p in packages]

        return Div(
            H1(f"Talent: {title}"),
            P(summary, style="color:#475569;margin-bottom:1rem;"),
            H2("Cast Recommendations"),
            *rec_cards,
            H2("Package Simulations", style="margin-top:1.5rem;") if pkg_els else "",
            *pkg_els,
            Button("Back", cls="auth-btn", style="margin-top:1.5rem;", onclick="loadModule('/module/talent', 'Talent Intel')"),
            cls="module-content",
        )

    @rt("/module/talent/{report_id}")
    def talent_detail(report_id: str, session):
        pool = get_pool()
        with pool.get_session() as s:
            row = s.execute(text("""
                SELECT title, recommendations, package_sims, analysis_text
                FROM ahmf.talent_reports WHERE report_id = :rid
            """), {"rid": report_id}).fetchone()
        if not row:
            return Div(P("Report not found."), cls="module-content")
        title, recs_json, pkgs_json, summary = row
        recs = recs_json if isinstance(recs_json, list) else json.loads(recs_json or "[]")
        packages = pkgs_json if isinstance(pkgs_json, list) else json.loads(pkgs_json or "[]")

        rec_rows = [Tr(Td(r.get("name", "")), Td(r.get("role", "")), Td(f"{r.get('heat_score', '')}/10"),
                       Td(f"{r.get('genre_fit', '')}/10"), Td(r.get("salary_tier", "")), Td(r.get("intl_impact", "")))
                    for r in recs]
        return Div(
            H1(f"Talent: {title}"), P(summary or "", style="color:#475569;margin-bottom:1rem;"),
            Table(Thead(Tr(Th("Actor"), Th("Role"), Th("Heat"), Th("Fit"), Th("Salary"), Th("Intl"))),
                  Tbody(*rec_rows), style="width:100%;border-collapse:collapse;font-size:0.85rem;"),
            Button("Back", cls="auth-btn", style="margin-top:1.5rem;", onclick="loadModule('/module/talent', 'Talent Intel')"),
            cls="module-content",
        )
