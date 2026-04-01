"""
Credit Rating Module

AI-powered counterparty strength assessment — distributor/producer scoring,
payment reliability tracking, and risk tier classification.
"""

import os, json, logging
from fasthtml.common import *
from sqlalchemy import text
from utils.db import get_pool

logger = logging.getLogger(__name__)


def _get_llm():
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1",
                      model="grok-3-mini", temperature=0.3)


def _tier_color(tier):
    return {"AAA": "#16a34a", "AA": "#16a34a", "A": "#22c55e", "BBB": "#f59e0b",
            "BB": "#f97316", "B": "#dc2626", "CCC": "#dc2626", "NR": "#94a3b8"}.get(tier or "NR", "#64748b")


def get_credit_rating(contact_name: str) -> str:
    """Look up credit rating for a contact (distributor/producer) by name."""
    pool = get_pool()
    with pool.get_session() as s:
        rows = s.execute(text("""
            SELECT c.name, c.company, c.contact_type, cr.score, cr.payment_reliability,
                   cr.risk_tier, cr.factors, cr.rated_at
            FROM ahmf.credit_ratings cr
            JOIN ahmf.contacts c ON c.contact_id = cr.contact_id
            WHERE c.name ILIKE :q
            ORDER BY cr.rated_at DESC LIMIT 5
        """), {"q": f"%{contact_name}%"}).fetchall()
    if not rows:
        return f"No credit rating found for '{contact_name}'."
    lines = [f"## Credit Ratings\n", "| Name | Company | Type | Score | Reliability | Tier |",
             "|------|---------|------|-------|-------------|------|"]
    for r in rows:
        lines.append(f"| {r[0]} | {r[1] or '—'} | {r[2]} | {r[3]:.0f}/100 | {r[4]:.0f}/100 | {r[5] or 'NR'} |")
    return "\n".join(lines)


def register_routes(rt):

    @rt("/module/credit")
    def module_credit(session):
        pool = get_pool()
        with pool.get_session() as s:
            ratings = s.execute(text("""
                SELECT cr.rating_id, c.name, c.company, c.contact_type, cr.score,
                       cr.payment_reliability, cr.risk_tier, cr.rated_at
                FROM ahmf.credit_ratings cr
                JOIN ahmf.contacts c ON c.contact_id = cr.contact_id
                ORDER BY cr.rated_at DESC LIMIT 30
            """)).fetchall()
            stats = s.execute(text("""
                SELECT COUNT(*), COALESCE(AVG(score), 0),
                       COUNT(CASE WHEN risk_tier IN ('B', 'CCC') THEN 1 END)
                FROM ahmf.credit_ratings
            """)).fetchone()

        total = stats[0] if stats else 0
        avg_score = stats[1] if stats else 0
        high_risk = stats[2] if stats else 0

        rows = []
        for r in ratings:
            color = _tier_color(r[6])
            rows.append(Div(
                Div(Span(r[1], cls="deal-card-title"),
                    Span(r[6] or "NR", style=f"font-weight:700;color:{color};font-size:0.9rem;"),
                    style="display:flex;justify-content:space-between;align-items:center;"),
                Div(f"{r[2] or '—'} | {r[3]} | Score: {r[4]:.0f}/100 | Reliability: {r[5]:.0f}/100", cls="deal-card-meta"),
                cls="deal-card", hx_get=f"/module/credit/{r[0]}", hx_target="#center-content", hx_swap="innerHTML",
            ))

        return Div(
            Div(H1("Credit Rating"),
                Button("+ Rate Contact", cls="auth-btn", hx_get="/module/credit/new", hx_target="#center-content", hx_swap="innerHTML"),
                style="display:flex;justify-content:space-between;align-items:center;"),
            P("Counterparty strength assessment — distributor and producer scoring.", style="color:#64748b;margin-bottom:1rem;"),
            Div(
                Div(Div("Contacts Rated", cls="stat-label"), Div(str(total), cls="stat-value"), cls="stat-card"),
                Div(Div("Avg Score", cls="stat-label"), Div(f"{avg_score:.0f}/100", cls="stat-value", style="color:#0066cc;"), cls="stat-card"),
                Div(Div("High Risk", cls="stat-label"), Div(str(high_risk), cls="stat-value", style="color:#dc2626;"), cls="stat-card"),
                cls="stats-grid",
            ),
            H2("Rated Contacts"),
            Div(*rows) if rows else P("No ratings yet. Rate your first counterparty.", style="color:#94a3b8;text-align:center;padding:2rem;"),
            cls="module-content",
        )

    @rt("/module/credit/new")
    def credit_new(session):
        pool = get_pool()
        with pool.get_session() as s:
            contacts = s.execute(text("""
                SELECT contact_id, name, company, contact_type FROM ahmf.contacts ORDER BY name
            """)).fetchall()
        contact_opts = [Option(f"{c[1]} ({c[2] or c[3]})", value=str(c[0])) for c in contacts]
        if not contact_opts:
            return Div(H1("Rate Contact"), P("No contacts to rate. Create contacts first."),
                       Button("Back", cls="auth-btn", onclick="loadModule('/module/credit', 'Credit Rating')"), cls="module-content")

        return Div(
            H1("Rate Contact"),
            P("Select a contact to generate an AI-powered credit assessment.", style="color:#64748b;margin-bottom:1rem;"),
            Form(
                Label("Contact", Select(*contact_opts, name="contact_id", required=True)),
                P("The AI will analyze the contact's profile and generate a credit score, "
                  "payment reliability rating, risk tier, and contributing factors.",
                  style="font-size:0.85rem;color:#94a3b8;margin:1rem 0;"),
                Button("Generate Rating", type="submit", cls="auth-btn"),
                cls="auth-form", hx_post="/module/credit/rate", hx_target="#center-content", hx_swap="innerHTML",
            ),
            cls="module-content",
        )

    @rt("/module/credit/rate", methods=["POST"])
    def credit_rate(session, contact_id: str):
        pool = get_pool()
        with pool.get_session() as s:
            contact = s.execute(text("""
                SELECT contact_id, name, company, contact_type, email, notes FROM ahmf.contacts WHERE contact_id = :cid
            """), {"cid": contact_id}).fetchone()
        if not contact:
            return Div(P("Contact not found."), cls="module-content")

        llm = _get_llm()
        prompt = f"""You are a film finance credit analyst. Rate this counterparty.

Name: {contact[1]}
Company: {contact[2] or 'Unknown'}
Type: {contact[3]}
Notes: {contact[5] or 'None'}

Return ONLY valid JSON:
{{
  "score": <int 0-100>,
  "payment_reliability": <int 0-100>,
  "risk_tier": "<AAA|AA|A|BBB|BB|B|CCC>",
  "factors": {{
    "track_record": "<assessment>",
    "financial_stability": "<assessment>",
    "market_position": "<assessment>",
    "payment_history": "<assessment>"
  }},
  "summary": "<2-sentence assessment>"
}}"""
        try:
            resp = llm.invoke(prompt)
            content = resp.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            data = json.loads(content)
        except Exception as e:
            return Div(H1("Error"), P(f"AI rating failed: {e}"), cls="module-content")

        score = data.get("score", 50)
        reliability = data.get("payment_reliability", 50)
        tier = data.get("risk_tier", "BBB")
        factors = data.get("factors", {})
        summary = data.get("summary", "")

        with pool.get_session() as s:
            s.execute(text("""
                INSERT INTO ahmf.credit_ratings (contact_id, score, payment_reliability, risk_tier, factors, rated_by)
                VALUES (:cid, :score, :rel, :tier, :factors, :uid)
            """), {"cid": contact_id, "score": score, "rel": reliability, "tier": tier,
                   "factors": json.dumps(factors), "uid": session.get("user_id")})

        color = _tier_color(tier)
        factor_els = [Div(
            Div(k.replace("_", " ").title(), style="font-weight:600;font-size:0.8rem;color:#1e293b;"),
            Div(v, style="font-size:0.8rem;color:#475569;"),
            style="padding:0.5rem;border:1px solid #e2e8f0;border-radius:8px;",
        ) for k, v in factors.items()]

        return Div(
            H1(f"Credit Rating: {contact[1]}"),
            P(f"{contact[2] or ''} | {contact[3]}", style="color:#64748b;margin-bottom:1rem;"),
            Div(
                Div(Div("Credit Score", cls="stat-label"), Div(f"{score}/100", cls="stat-value", style=f"color:{color};"), cls="stat-card"),
                Div(Div("Payment Reliability", cls="stat-label"), Div(f"{reliability}/100", cls="stat-value"), cls="stat-card"),
                Div(Div("Risk Tier", cls="stat-label"), Div(tier, cls="stat-value", style=f"color:{color};"), cls="stat-card"),
                cls="stats-grid",
            ),
            P(summary, style="color:#475569;margin:1rem 0;padding:1rem;background:#f8fafc;border-radius:12px;border:1px solid #e2e8f0;"),
            H2("Rating Factors"),
            Div(*factor_els, style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;"),
            Button("Back", cls="auth-btn", style="margin-top:1.5rem;", onclick="loadModule('/module/credit', 'Credit Rating')"),
            cls="module-content",
        )

    @rt("/module/credit/{rating_id}")
    def credit_detail(rating_id: str, session):
        pool = get_pool()
        with pool.get_session() as s:
            row = s.execute(text("""
                SELECT cr.score, cr.payment_reliability, cr.risk_tier, cr.factors, cr.rated_at,
                       c.name, c.company, c.contact_type
                FROM ahmf.credit_ratings cr
                JOIN ahmf.contacts c ON c.contact_id = cr.contact_id
                WHERE cr.rating_id = :rid
            """), {"rid": rating_id}).fetchone()
        if not row:
            return Div(P("Rating not found."), cls="module-content")

        score, reliability, tier, factors_json, rated_at, name, company, ctype = row
        factors = factors_json if isinstance(factors_json, dict) else json.loads(factors_json or "{}")
        color = _tier_color(tier)

        factor_els = [Div(
            Div(k.replace("_", " ").title(), style="font-weight:600;font-size:0.8rem;"),
            Div(v, style="font-size:0.8rem;color:#475569;"),
            style="padding:0.5rem;border:1px solid #e2e8f0;border-radius:8px;",
        ) for k, v in factors.items()]

        return Div(
            H1(f"Credit Rating: {name}"),
            P(f"{company or ''} | {ctype} | Rated {rated_at.strftime('%b %d, %Y') if rated_at else '?'}", style="color:#64748b;margin-bottom:1rem;"),
            Div(
                Div(Div("Score", cls="stat-label"), Div(f"{score:.0f}/100", cls="stat-value", style=f"color:{color};"), cls="stat-card"),
                Div(Div("Reliability", cls="stat-label"), Div(f"{reliability:.0f}/100", cls="stat-value"), cls="stat-card"),
                Div(Div("Tier", cls="stat-label"), Div(tier or "NR", cls="stat-value", style=f"color:{color};"), cls="stat-card"),
                cls="stats-grid",
            ),
            H2("Factors"), Div(*factor_els, style="display:grid;grid-template-columns:1fr 1fr;gap:0.75rem;") if factor_els else P("No factors."),
            Button("Back", cls="auth-btn", style="margin-top:1.5rem;", onclick="loadModule('/module/credit', 'Credit Rating')"),
            cls="module-content",
        )
