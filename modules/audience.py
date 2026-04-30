"""
Product 8: Audience & Marketing Intelligence/Predictor

AI-powered audience modeling, demographic segmentation, marketing ROI simulation,
and release strategy optimization.
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


def analyze_audience_tool(title: str, genre: str = "Drama", cast: str = "",
                          budget: str = "", target_demo: str = "") -> str:
    """Analyze target audience, predict demographics, and recommend marketing strategy for a film."""
    llm = _get_llm()
    prompt = f"""You are a film marketing and audience analytics expert. Analyze the target audience for this project.

Project: {title} | Genre: {genre} | Cast: {cast} | Budget: {budget} | Target: {target_demo}

Return ONLY valid JSON:
{{
  "segments": [
    {{"name": "...", "age_range": "...", "percentage": <int>, "description": "..."}},
    ...
  ],
  "marketing_plan": {{
    "total_spend_estimate": <number>,
    "channels": [{{"channel": "Social Media", "percentage": <int>, "rationale": "...", "estimated_spend": <number>, "projected_reach": <number>, "roi_percentage": <number>}}],
    "release_window": "...",
    "p_and_a_ratio": "<ratio of P&A to production budget>"
  }},
  "release_strategy": {{
    "domestic_release": "...",
    "international_rollout": "...",
    "platform_strategy": "...",
    "festival_strategy": "..."
  }},
  "strategy_reasoning": "<2-3 sentence explanation of overall marketing strategy rationale>",
  "summary": "..."
}}

Provide 3-5 audience segments and 4-6 marketing channels."""
    try:
        resp = llm.invoke(prompt)
        content = resp.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(content)
        segments = data.get("segments", [])
        marketing = data.get("marketing_plan", {})
        release = data.get("release_strategy", {})
        strategy_reasoning = data.get("strategy_reasoning", "")
        summary = data.get("summary", "")

        lines = [f"## Audience Analysis: {title}\n", summary, "\n### Audience Segments\n",
                 "| Segment | Age | Share | Description |", "|---------|-----|-------|-------------|"]
        for seg in segments:
            lines.append(f"| {seg.get('name', '')} | {seg.get('age_range', '')} | {seg.get('percentage', 0)}% | {seg.get('description', '')} |")
        lines.append(f"\n### Marketing Plan\n")
        lines.append(f"**Estimated Spend:** ${marketing.get('total_spend_estimate', 0):,.0f}")
        lines.append(f"**Release Window:** {marketing.get('release_window', 'TBD')}")
        lines.append(f"\n| Channel | Share | Est. Spend | Proj. Reach | ROI % | Rationale |")
        lines.append(f"|---------|-------|------------|-------------|-------|-----------|")
        for ch in marketing.get("channels", []):
            lines.append(f"| {ch.get('channel', '')} | {ch.get('percentage', 0)}% | ${ch.get('estimated_spend', 0):,.0f} | {ch.get('projected_reach', 0):,.0f} | {ch.get('roi_percentage', 0)}% | {ch.get('rationale', '')} |")
        if strategy_reasoning:
            lines.append(f"\n### Strategy Rationale\n{strategy_reasoning}")
        lines.append(f"\n### Release Strategy")
        lines.append(f"- **Domestic:** {release.get('domestic_release', '')}")
        lines.append(f"- **International:** {release.get('international_rollout', '')}")
        lines.append(f"- **Platform:** {release.get('platform_strategy', '')}")
        lines.append(f"- **Festivals:** {release.get('festival_strategy', '')}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error analyzing audience: {e}"


def register_routes(rt):

    @rt("/module/audience")
    def module_audience(session):
        pool = get_pool()
        with pool.get_session() as s:
            reports = s.execute(text("""
                SELECT report_id, title, created_at FROM ahmf.audience_reports ORDER BY created_at DESC LIMIT 20
            """)).fetchall()
        rows = [Div(
            Div(Span(r[1], cls="deal-card-title"), style="display:flex;justify-content:space-between;"),
            Div(r[2].strftime('%b %d, %Y') if r[2] else '', cls="deal-card-meta"),
            cls="deal-card", hx_get=f"/module/audience/{r[0]}", hx_target="#center-content", hx_swap="innerHTML",
        ) for r in reports]

        return Div(
            Div(H1("Audience & Marketing Intelligence"),
                Button("+ New Analysis", cls="auth-btn", hx_get="/module/audience/new", hx_target="#center-content", hx_swap="innerHTML"),
                style="display:flex;justify-content:space-between;align-items:center;"),
            P("AI-powered audience segmentation, marketing ROI prediction, and release strategy.", style="color:#64748b;margin-bottom:1.5rem;"),
            Div(*rows) if rows else P("No reports yet.", style="color:#94a3b8;text-align:center;padding:2rem;"),
            cls="module-content",
        )

    @rt("/module/audience/new")
    def audience_new(session):
        return Div(
            H1("New Audience Analysis"),
            Form(
                Div(Div(Label("Project Title", Input(type="text", name="title", required=True)), style="flex:1"),
                    Div(Label("Genre", Select(*[Option(g, value=g) for g in GENRES], name="genre")), style="flex:1"),
                    style="display:flex;gap:1rem;"),
                Div(Div(Label("Cast", Input(type="text", name="cast", placeholder="Key cast members")), style="flex:1"),
                    Div(Label("Budget", Input(type="text", name="budget", placeholder="e.g. $20M")), style="flex:1"),
                    style="display:flex;gap:1rem;"),
                Label("Target Demographic", Input(type="text", name="target_demo", placeholder="e.g. Males 18-34, families, arthouse")),
                Button("Analyze Audience", type="submit", cls="auth-btn"),
                cls="auth-form", hx_post="/module/audience/analyze", hx_target="#center-content", hx_swap="innerHTML",
            ),
            cls="module-content",
        )

    @rt("/module/audience/analyze", methods=["POST"])
    def audience_analyze(session, title: str, genre: str = "Drama", cast: str = "",
                         budget: str = "", target_demo: str = ""):
        llm = _get_llm()
        prompt = f"""You are a film marketing expert. Analyze the target audience.

Project: {title} | Genre: {genre} | Cast: {cast} | Budget: {budget} | Target: {target_demo}

Return ONLY valid JSON:
{{"segments": [{{"name": "...", "age_range": "...", "percentage": <int>, "description": "..."}}], "marketing_plan": {{"total_spend_estimate": <number>, "channels": [{{"channel": "...", "percentage": <int>, "rationale": "...", "estimated_spend": <number>, "projected_reach": <number>, "roi_percentage": <number>}}], "release_window": "...", "p_and_a_ratio": "..."}}, "release_strategy": {{"domestic_release": "...", "international_rollout": "...", "platform_strategy": "...", "festival_strategy": "..."}}, "strategy_reasoning": "<2-3 sentence explanation of overall marketing strategy rationale>", "summary": "..."}}"""
        try:
            resp = llm.invoke(prompt)
            content = resp.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            data = json.loads(content)
        except Exception as e:
            return Div(H1("Error"), P(f"AI analysis failed: {e}"), cls="module-content")

        segments = data.get("segments", [])
        marketing = data.get("marketing_plan", {})
        release = data.get("release_strategy", {})
        strategy_reasoning = data.get("strategy_reasoning", "")
        summary = data.get("summary", "")

        pool = get_pool()
        with pool.get_session() as s:
            s.execute(text("""
                INSERT INTO ahmf.audience_reports (title, project_params, segments, marketing_plan, release_strategy, analysis_text, created_by)
                VALUES (:title, :params, :seg, :mkt, :rel, :summary, :uid)
            """), {"title": title, "params": json.dumps({"genre": genre, "cast": cast, "budget": budget, "target_demo": target_demo}),
                   "seg": json.dumps(segments), "mkt": json.dumps(marketing), "rel": json.dumps(release),
                   "summary": summary, "uid": session.get("user_id")})

        seg_cards = [Div(
            Div(Span(seg.get("name", ""), style="font-weight:600;"), Span(f" — {seg.get('age_range', '')}", style="color:#64748b;")),
            Div(
                Div(style=f"width:{seg.get('percentage', 0)}%;height:8px;background:#0066cc;border-radius:4px;"),
                style="width:100%;height:8px;background:#e2e8f0;border-radius:4px;margin:0.3rem 0;",
            ),
            Div(f"{seg.get('percentage', 0)}% — {seg.get('description', '')}", style="font-size:0.8rem;color:#475569;"),
            style="padding:0.75rem;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:0.5rem;",
        ) for seg in segments]

        channel_rows = [Tr(Td(ch.get("channel", "")), Td(f"{ch.get('percentage', 0)}%"),
                           Td(f"${ch.get('estimated_spend', 0):,.0f}"), Td(f"{ch.get('projected_reach', 0):,.0f}"),
                           Td(f"{ch.get('roi_percentage', 0)}%"), Td(ch.get("rationale", "")))
                        for ch in marketing.get("channels", [])]

        return Div(
            H1(f"Audience Analysis: {title}"),
            P(summary, style="color:#475569;margin-bottom:1rem;"),
            Div(
                Div(Div("Est. Marketing Spend", cls="stat-label"),
                    Div(f"${marketing.get('total_spend_estimate', 0):,.0f}", cls="stat-value", style="color:#0066cc;"), cls="stat-card"),
                Div(Div("Release Window", cls="stat-label"),
                    Div(marketing.get("release_window", "TBD"), cls="stat-value", style="font-size:1rem;"), cls="stat-card"),
                Div(Div("Segments", cls="stat-label"), Div(str(len(segments)), cls="stat-value"), cls="stat-card"),
                cls="stats-grid",
            ),
            H2("Audience Segments"), *seg_cards,
            H2("Marketing Channels", style="margin-top:1.5rem;"),
            Table(Thead(Tr(Th("Channel"), Th("Share"), Th("Est. Spend"), Th("Proj. Reach"), Th("ROI %"), Th("Rationale"))), Tbody(*channel_rows),
                  style="width:100%;border-collapse:collapse;font-size:0.85rem;"),
            H2("Strategy Rationale", style="margin-top:1.5rem;"),
            P(strategy_reasoning, style="color:#475569;font-size:0.9rem;padding:1rem;background:#f0f9ff;border-radius:8px;border:1px solid #bae6fd;"),
            H2("Release Strategy", style="margin-top:1.5rem;"),
            Ul(Li(f"Domestic: {release.get('domestic_release', '')}"),
               Li(f"International: {release.get('international_rollout', '')}"),
               Li(f"Platform: {release.get('platform_strategy', '')}"),
               Li(f"Festivals: {release.get('festival_strategy', '')}"),
               style="color:#475569;"),
            Button("Back", cls="auth-btn", style="margin-top:1.5rem;", onclick="loadModule('/module/audience', 'Audience Intel')"),
            cls="module-content",
        )

    @rt("/module/audience/{report_id}")
    def audience_detail(report_id: str, session):
        pool = get_pool()
        with pool.get_session() as s:
            row = s.execute(text("""
                SELECT title, segments, marketing_plan, release_strategy, analysis_text
                FROM ahmf.audience_reports WHERE report_id = :rid
            """), {"rid": report_id}).fetchone()
        if not row:
            return Div(P("Report not found."), cls="module-content")
        title, segments_json, mkt_json, rel_json, summary = row
        segments = segments_json if isinstance(segments_json, list) else json.loads(segments_json or "[]")
        marketing = mkt_json if isinstance(mkt_json, dict) else json.loads(mkt_json or "{}")
        release = rel_json if isinstance(rel_json, dict) else json.loads(rel_json or "{}")

        seg_cards = [Div(
            Div(Span(seg.get("name", ""), style="font-weight:600;"), Span(f" {seg.get('percentage', 0)}%", style="color:#0066cc;")),
            Div(seg.get("description", ""), style="font-size:0.8rem;color:#475569;"),
            style="padding:0.5rem;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:0.4rem;",
        ) for seg in segments]

        return Div(
            H1(f"Audience: {title}"), P(summary or "", style="color:#475569;margin-bottom:1rem;"),
            H2("Segments"), *seg_cards,
            H2("Release Strategy", style="margin-top:1rem;"),
            Ul(Li(f"Domestic: {release.get('domestic_release', '')}"),
               Li(f"International: {release.get('international_rollout', '')}"),
               Li(f"Platform: {release.get('platform_strategy', '')}"),
               style="color:#475569;"),
            Button("Back", cls="auth-btn", style="margin-top:1.5rem;", onclick="loadModule('/module/audience', 'Audience Intel')"),
            cls="module-content",
        )
