"""
Product 5: Automated Production Scheduling Tool

AI generates optimized shooting schedules with location clustering and day-by-day plans.
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
                      model="grok-3-mini", temperature=0.3)


def generate_schedule_tool(title: str, genre: str = "Drama", locations: str = "",
                           shoot_days: str = "20", scenes: str = "",
                           constraints: str = "") -> str:
    """Generate an optimized shooting schedule with location clustering for a film project."""
    llm = _get_llm()
    prompt = f"""You are a film production scheduler. Generate a day-by-day shooting schedule.

Project: {title} | Genre: {genre}
Locations: {locations} | Shoot Days: {shoot_days}
Key Scenes: {scenes}
Constraints: {constraints}

Optimize for: location clustering (minimize company moves), actor availability, day/night grouping.

Return ONLY valid JSON:
{{
  "total_days": <int>,
  "days": [
    {{"day": 1, "location": "...", "scenes": "...", "call_time": "6:00 AM", "wrap_time": "6:00 PM", "notes": "..."}},
    ...
  ],
  "summary": "<2-3 sentence schedule overview>"
}}

Generate {shoot_days} days of schedule."""
    try:
        resp = llm.invoke(prompt)
        content = resp.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(content)
        days = data.get("days", [])
        summary = data.get("summary", "")

        lines = [f"## Schedule: {title}\n", summary, "",
                 "| Day | Location | Scenes | Call | Wrap | Notes |",
                 "|-----|----------|--------|------|------|-------|"]
        for d in days:
            lines.append(f"| {d.get('day','')} | {d.get('location','')} | {d.get('scenes','')} | {d.get('call_time','')} | {d.get('wrap_time','')} | {d.get('notes','')} |")
        return "\n".join(lines)
    except Exception as e:
        return f"Error generating schedule: {e}"


def register_routes(rt):

    @rt("/module/schedule")
    def module_schedule(session):
        pool = get_pool()
        with pool.get_session() as s:
            schedules = s.execute(text("""
                SELECT schedule_id, title, total_days, created_at
                FROM ahmf.schedules ORDER BY created_at DESC LIMIT 20
            """)).fetchall()

        rows = [Div(
            Div(Span(sc[1], cls="deal-card-title"),
                Span(f"{sc[2] or 0} days", style="font-weight:600;color:#0066cc;font-size:0.85rem;"),
                style="display:flex;justify-content:space-between;align-items:center;"),
            Div(sc[3].strftime('%b %d, %Y') if sc[3] else '', cls="deal-card-meta"),
            cls="deal-card", hx_get=f"/module/schedule/{sc[0]}", hx_target="#center-content", hx_swap="innerHTML",
        ) for sc in schedules]

        return Div(
            Div(H1("Production Scheduling"),
                Button("+ Generate Schedule", cls="auth-btn",
                       hx_get="/module/schedule/new", hx_target="#center-content", hx_swap="innerHTML"),
                style="display:flex;justify-content:space-between;align-items:center;"),
            P("AI-optimized shooting schedules with location clustering.", style="color:#64748b;margin-bottom:1.5rem;"),
            Div(*rows) if rows else P("No schedules yet.", style="color:#94a3b8;text-align:center;padding:2rem;"),
            cls="module-content",
        )

    @rt("/module/schedule/new")
    def schedule_new(session):
        return Div(
            H1("Generate Shooting Schedule"),
            Form(
                Div(Div(Label("Project Title", Input(type="text", name="title", required=True)), style="flex:1"),
                    Div(Label("Genre", Select(*[Option(g, value=g) for g in GENRES], name="genre")), style="flex:1"),
                    Div(Label("Shoot Days", Input(type="number", name="shoot_days", value="20")), style="flex:1"),
                    style="display:flex;gap:1rem;"),
                Label("Locations", Input(type="text", name="locations", placeholder="e.g. Studio A, Downtown LA, Desert Ext.")),
                Label("Key Scenes / Script Notes", Textarea(name="scenes", rows="3", placeholder="e.g. Big action sequence at docks, Night exterior chase, Courtroom interior",
                      style="width:100%;padding:0.5rem;border:1px solid #e2e8f0;border-radius:8px;font-family:inherit;")),
                Label("Constraints", Input(type="text", name="constraints", placeholder="e.g. Lead actor unavailable week 3, night permits required")),
                Button("Generate Schedule", type="submit", cls="auth-btn"),
                cls="auth-form", hx_post="/module/schedule/generate", hx_target="#center-content", hx_swap="innerHTML",
            ),
            cls="module-content",
        )

    @rt("/module/schedule/generate", methods=["POST"])
    def schedule_generate(session, title: str, genre: str = "Drama", shoot_days: str = "20",
                          locations: str = "", scenes: str = "", constraints: str = ""):
        llm = _get_llm()
        prompt = f"""You are a film production scheduler. Generate a day-by-day shooting schedule.

Project: {title} | Genre: {genre} | Locations: {locations} | Shoot Days: {shoot_days}
Key Scenes: {scenes} | Constraints: {constraints}

Optimize for location clustering. Return ONLY valid JSON:
{{"total_days": <int>, "days": [{{"day": 1, "location": "...", "scenes": "...", "call_time": "6:00 AM", "wrap_time": "6:00 PM", "notes": "..."}}], "summary": "..."}}"""
        try:
            resp = llm.invoke(prompt)
            content = resp.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            data = json.loads(content)
        except Exception as e:
            return Div(H1("Error"), P(f"AI analysis failed: {e}"), cls="module-content")

        days = data.get("days", [])
        summary = data.get("summary", "")
        total = data.get("total_days", len(days))

        pool = get_pool()
        with pool.get_session() as s:
            result = s.execute(text("""
                INSERT INTO ahmf.schedules (title, project_params, total_days, analysis_text, created_by)
                VALUES (:title, :params, :total, :summary, :uid) RETURNING schedule_id
            """), {"title": title, "params": json.dumps({"genre": genre, "locations": locations, "scenes": scenes, "constraints": constraints}),
                   "total": total, "summary": summary, "uid": session.get("user_id")})
            schedule_id = str(result.scalar())
            for d in days:
                s.execute(text("""
                    INSERT INTO ahmf.schedule_days (schedule_id, day_number, location, scenes, call_time, wrap_time, notes, sort_order)
                    VALUES (:sid, :day, :loc, :scenes, :call, :wrap, :notes, :order)
                """), {"sid": schedule_id, "day": d.get("day", 0), "loc": d.get("location", ""),
                       "scenes": d.get("scenes", ""), "call": d.get("call_time", ""), "wrap": d.get("wrap_time", ""),
                       "notes": d.get("notes", ""), "order": d.get("day", 0)})

        day_rows = [Tr(Td(str(d.get("day", ""))), Td(d.get("location", "")), Td(d.get("scenes", "")),
                       Td(d.get("call_time", "")), Td(d.get("wrap_time", "")), Td(d.get("notes", "")))
                    for d in days]

        return Div(
            H1(f"Schedule: {title}"),
            Div(Div(Div("Total Days", cls="stat-label"), Div(str(total), cls="stat-value"), cls="stat-card"),
                Div(Div("Locations", cls="stat-label"), Div(str(len(set(d.get("location", "") for d in days))), cls="stat-value"), cls="stat-card"),
                cls="stats-grid"),
            P(summary, style="color:#475569;margin:1rem 0;"),
            Table(Thead(Tr(Th("Day"), Th("Location"), Th("Scenes"), Th("Call"), Th("Wrap"), Th("Notes"))),
                  Tbody(*day_rows), style="width:100%;border-collapse:collapse;font-size:0.8rem;"),
            Button("Back", cls="auth-btn", style="margin-top:1.5rem;", onclick="loadModule('/module/schedule', 'Scheduling')"),
            cls="module-content",
        )

    @rt("/module/schedule/{schedule_id}")
    def schedule_detail(schedule_id: str, session):
        pool = get_pool()
        with pool.get_session() as s:
            sc = s.execute(text("SELECT title, total_days, analysis_text FROM ahmf.schedules WHERE schedule_id = :sid"),
                           {"sid": schedule_id}).fetchone()
            days = s.execute(text("""
                SELECT day_number, location, scenes, call_time, wrap_time, notes
                FROM ahmf.schedule_days WHERE schedule_id = :sid ORDER BY sort_order
            """), {"sid": schedule_id}).fetchall()
        if not sc:
            return Div(P("Schedule not found."), cls="module-content")
        day_rows = [Tr(Td(str(d[0])), Td(d[1]), Td(d[2]), Td(d[3]), Td(d[4]), Td(d[5] or "")) for d in days]
        return Div(
            H1(f"Schedule: {sc[0]}"),
            P(sc[2] or "", style="color:#475569;margin-bottom:1rem;"),
            Table(Thead(Tr(Th("Day"), Th("Location"), Th("Scenes"), Th("Call"), Th("Wrap"), Th("Notes"))),
                  Tbody(*day_rows), style="width:100%;border-collapse:collapse;font-size:0.8rem;"),
            Button("Back", cls="auth-btn", style="margin-top:1.5rem;", onclick="loadModule('/module/schedule', 'Scheduling')"),
            cls="module-content",
        )
