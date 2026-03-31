"""
Product 3: Production Risk Scoring System

"Moody's for execution risk" — AI evaluates execution risk across 6 dimensions
to generate a structured production risk score.
"""

import os, json, uuid, logging
from fasthtml.common import *
from sqlalchemy import text
from utils.db import get_pool
from config.settings import RISK_DIMENSIONS, RISK_TIERS, VFX_LEVELS, GENRES

logger = logging.getLogger(__name__)


def _get_llm():
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1",
                      model="grok-3-mini", temperature=0.3)


def _tier_for_score(score):
    for tier, (lo, hi) in RISK_TIERS.items():
        if lo <= score <= hi:
            return tier
    return "high"


def _tier_color(tier):
    return {"low": "#16a34a", "moderate": "#f59e0b", "elevated": "#f97316", "high": "#dc2626"}.get(tier, "#64748b")


# ---------------------------------------------------------------------------
# AI tool (callable from chat agent)
# ---------------------------------------------------------------------------

def analyze_production_risk(title: str, genre: str = "", budget: str = "",
                            locations: str = "", vfx_level: str = "Light",
                            stunts: str = "No", jurisdiction: str = "",
                            shoot_days: str = "30") -> str:
    """Analyze production risk for a film project. Returns risk scores across 6 dimensions and mitigations."""
    llm = _get_llm()
    prompt = f"""You are a film production risk analyst. Score this project on 6 risk dimensions (0-100, where 100=highest risk).

Project: {title}
Genre: {genre} | Budget: {budget} | VFX Level: {vfx_level}
Locations: {locations} | Stunts: {stunts}
Jurisdiction: {jurisdiction} | Shoot Days: {shoot_days}

Return ONLY valid JSON (no markdown):
{{
  "scores": {{
    "Script Complexity": <int>,
    "Budget Feasibility": <int>,
    "Schedule Risk": <int>,
    "Jurisdictional Risk": <int>,
    "Crew/Talent Risk": <int>,
    "Completion Risk": <int>
  }},
  "overall_score": <int>,
  "mitigations": ["<mitigation 1>", "<mitigation 2>", "<mitigation 3>"],
  "summary": "<2-3 sentence risk assessment>"
}}"""
    try:
        resp = llm.invoke(prompt)
        content = resp.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(content)
        scores = data.get("scores", {})
        overall = data.get("overall_score", 50)
        tier = _tier_for_score(overall)
        mitigations = data.get("mitigations", [])
        summary = data.get("summary", "")

        lines = [f"## Risk Assessment: {title}\n"]
        lines.append(f"**Overall Score:** {overall}/100 — **{tier.upper()}** risk\n")
        lines.append("| Dimension | Score |")
        lines.append("|-----------|-------|")
        for dim in RISK_DIMENSIONS:
            s = scores.get(dim, 50)
            lines.append(f"| {dim} | {s}/100 |")
        lines.append(f"\n{summary}\n")
        if mitigations:
            lines.append("**Mitigations:**")
            for m in mitigations:
                lines.append(f"- {m}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error analyzing risk: {e}"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

def register_routes(rt):

    @rt("/module/risk")
    def module_risk(session):
        pool = get_pool()
        with pool.get_session() as s:
            assessments = s.execute(text("""
                SELECT assessment_id, title, overall_score, risk_tier, created_at
                FROM ahmf.risk_assessments ORDER BY created_at DESC LIMIT 20
            """)).fetchall()

        rows = []
        for a in assessments:
            color = _tier_color(a[3] or "moderate")
            rows.append(Div(
                Div(
                    Span(a[1], cls="deal-card-title"),
                    Span(f"{a[2]:.0f}/100", style=f"color:{color};font-weight:700;font-size:0.85rem;"),
                    style="display:flex;justify-content:space-between;align-items:center;",
                ),
                Div(f"{(a[3] or 'N/A').upper()} risk | {a[4].strftime('%b %d, %Y') if a[4] else ''}", cls="deal-card-meta"),
                cls="deal-card",
                hx_get=f"/module/risk/{a[0]}",
                hx_target="#center-content",
                hx_swap="innerHTML",
            ))

        return Div(
            Div(
                H1("Production Risk Scoring"),
                Button("+ New Assessment", cls="auth-btn",
                       hx_get="/module/risk/new", hx_target="#center-content", hx_swap="innerHTML"),
                style="display:flex;justify-content:space-between;align-items:center;",
            ),
            P("AI-driven feasibility engine — evaluate execution risk across 6 dimensions.", style="color:#64748b;margin-bottom:1.5rem;"),
            Div(*rows) if rows else P("No assessments yet. Create your first one.", style="color:#94a3b8;text-align:center;padding:2rem;"),
            cls="module-content",
        )

    @rt("/module/risk/new")
    def risk_new(session):
        return Div(
            H1("New Risk Assessment"),
            Form(
                Div(
                    Div(Label("Project Title", Input(type="text", name="title", required=True, placeholder="Film title")), style="flex:1"),
                    Div(Label("Genre", Select(*[Option(g, value=g) for g in GENRES], name="genre")), style="flex:1"),
                    style="display:flex;gap:1rem;",
                ),
                Div(
                    Div(Label("Budget", Input(type="text", name="budget", placeholder="e.g. $15M")), style="flex:1"),
                    Div(Label("Shoot Days", Input(type="number", name="shoot_days", value="30")), style="flex:1"),
                    Div(Label("VFX Level", Select(*[Option(v, value=v) for v in VFX_LEVELS], name="vfx_level")), style="flex:1"),
                    style="display:flex;gap:1rem;",
                ),
                Label("Locations", Input(type="text", name="locations", placeholder="e.g. Atlanta, Prague, London")),
                Div(
                    Div(Label("Jurisdiction", Input(type="text", name="jurisdiction", placeholder="e.g. Georgia, USA")), style="flex:1"),
                    Div(Label("Stunts/Action", Select(Option("No", value="No"), Option("Light", value="Light"),
                                                       Option("Heavy", value="Heavy"), name="stunts")), style="flex:1"),
                    style="display:flex;gap:1rem;",
                ),
                Button("Analyze Risk", type="submit", cls="auth-btn"),
                cls="auth-form",
                hx_post="/module/risk/analyze",
                hx_target="#center-content",
                hx_swap="innerHTML",
            ),
            cls="module-content",
        )

    @rt("/module/risk/analyze", methods=["POST"])
    def risk_analyze(session, title: str, genre: str = "", budget: str = "",
                     shoot_days: str = "30", vfx_level: str = "Light",
                     locations: str = "", jurisdiction: str = "", stunts: str = "No"):
        llm = _get_llm()
        prompt = f"""You are a film production risk analyst. Score this project on 6 risk dimensions (0-100, where 100=highest risk).

Project: {title}
Genre: {genre} | Budget: {budget} | VFX Level: {vfx_level}
Locations: {locations} | Stunts: {stunts}
Jurisdiction: {jurisdiction} | Shoot Days: {shoot_days}

Return ONLY valid JSON (no markdown):
{{"scores": {{"Script Complexity": <int>, "Budget Feasibility": <int>, "Schedule Risk": <int>, "Jurisdictional Risk": <int>, "Crew/Talent Risk": <int>, "Completion Risk": <int>}}, "overall_score": <int>, "mitigations": ["..."], "summary": "..."}}"""
        try:
            resp = llm.invoke(prompt)
            content = resp.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            data = json.loads(content)
        except Exception as e:
            return Div(H1("Error"), P(f"AI analysis failed: {e}"), cls="module-content")

        scores = data.get("scores", {})
        overall = data.get("overall_score", 50)
        tier = _tier_for_score(overall)
        mitigations = data.get("mitigations", [])
        summary = data.get("summary", "")

        # Persist
        pool = get_pool()
        with pool.get_session() as s:
            s.execute(text("""
                INSERT INTO ahmf.risk_assessments (title, project_details, scores, overall_score, risk_tier, mitigations, analysis_text, created_by)
                VALUES (:title, :details, :scores, :overall, :tier, :mits, :summary, :uid)
            """), {
                "title": title,
                "details": json.dumps({"genre": genre, "budget": budget, "vfx_level": vfx_level,
                                        "locations": locations, "jurisdiction": jurisdiction, "stunts": stunts, "shoot_days": shoot_days}),
                "scores": json.dumps(scores), "overall": overall, "tier": tier,
                "mits": json.dumps(mitigations), "summary": summary, "uid": session.get("user_id"),
            })

        color = _tier_color(tier)
        score_cards = [
            Div(
                Div(dim, cls="stat-label"),
                Div(f"{scores.get(dim, 50)}", cls="stat-value",
                    style=f"color:{_tier_color(_tier_for_score(scores.get(dim, 50)))}"),
                cls="stat-card",
            ) for dim in RISK_DIMENSIONS
        ]

        return Div(
            H1(f"Risk Assessment: {title}"),
            Div(
                Div(Div("Overall Score", cls="stat-label"),
                    Div(f"{overall}/100", cls="stat-value", style=f"color:{color}"), cls="stat-card"),
                Div(Div("Risk Tier", cls="stat-label"),
                    Div(tier.upper(), cls="stat-value", style=f"color:{color}"), cls="stat-card"),
                *score_cards,
                cls="stats-grid",
            ),
            Div(P(summary, style="color:#475569;font-size:0.9rem;"), style="margin:1rem 0;padding:1rem;background:#f8fafc;border-radius:12px;border:1px solid #e2e8f0;"),
            H2("Mitigations", style="margin-top:1.5rem;"),
            Ul(*[Li(m, style="margin:0.4rem 0;color:#475569;") for m in mitigations]) if mitigations else P("None identified."),
            Button("Back to Risk Scoring", cls="auth-btn", style="margin-top:1.5rem;",
                   onclick="loadModule('/module/risk', 'Risk Scoring')"),
            cls="module-content",
        )

    @rt("/module/risk/{assessment_id}")
    def risk_detail(assessment_id: str, session):
        pool = get_pool()
        with pool.get_session() as s:
            row = s.execute(text("""
                SELECT title, scores, overall_score, risk_tier, mitigations, analysis_text, project_details
                FROM ahmf.risk_assessments WHERE assessment_id = :aid
            """), {"aid": assessment_id}).fetchone()
        if not row:
            return Div(P("Assessment not found."), cls="module-content")

        title, scores_json, overall, tier, mits_json, summary, details = row
        scores = scores_json if isinstance(scores_json, dict) else json.loads(scores_json or "{}")
        mitigations = mits_json if isinstance(mits_json, list) else json.loads(mits_json or "[]")
        color = _tier_color(tier or "moderate")

        score_cards = [
            Div(Div(dim, cls="stat-label"),
                Div(f"{scores.get(dim, 50)}", cls="stat-value",
                    style=f"color:{_tier_color(_tier_for_score(scores.get(dim, 50)))}"),
                cls="stat-card")
            for dim in RISK_DIMENSIONS
        ]

        return Div(
            H1(f"Risk Assessment: {title}"),
            Div(
                Div(Div("Overall Score", cls="stat-label"), Div(f"{overall}/100", cls="stat-value", style=f"color:{color}"), cls="stat-card"),
                Div(Div("Risk Tier", cls="stat-label"), Div((tier or "N/A").upper(), cls="stat-value", style=f"color:{color}"), cls="stat-card"),
                *score_cards, cls="stats-grid",
            ),
            Div(P(summary or "", style="color:#475569;"), style="margin:1rem 0;padding:1rem;background:#f8fafc;border-radius:12px;border:1px solid #e2e8f0;"),
            H2("Mitigations"), Ul(*[Li(m) for m in mitigations]) if mitigations else P("None."),
            Button("Back", cls="auth-btn", style="margin-top:1rem;", onclick="loadModule('/module/risk', 'Risk Scoring')"),
            cls="module-content",
        )
