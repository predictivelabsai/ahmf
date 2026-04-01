"""
Communications Module

Deal-linked messaging, task assignment with deadlines,
version-controlled notes, and milestone notifications.
"""

import logging
from fasthtml.common import *
from sqlalchemy import text
from utils.db import get_pool

logger = logging.getLogger(__name__)

MSG_TYPES = ["note", "task", "notification"]


def _type_color(msg_type):
    return {"note": "#0066cc", "task": "#f59e0b", "notification": "#8b5cf6"}.get(msg_type, "#64748b")


def search_messages(query: str = "") -> str:
    """Search messages, tasks, and notes by deal title, subject, or content."""
    pool = get_pool()
    with pool.get_session() as s:
        if query:
            rows = s.execute(text("""
                SELECT m.message_id, d.title, m.subject, m.message_type, m.status, m.due_date, m.created_at
                FROM ahmf.messages m
                LEFT JOIN ahmf.deals d ON d.deal_id = m.deal_id
                WHERE d.title ILIKE :q OR m.subject ILIKE :q OR m.body ILIKE :q
                ORDER BY m.created_at DESC LIMIT 20
            """), {"q": f"%{query}%"}).fetchall()
        else:
            rows = s.execute(text("""
                SELECT m.message_id, d.title, m.subject, m.message_type, m.status, m.due_date, m.created_at
                FROM ahmf.messages m
                LEFT JOIN ahmf.deals d ON d.deal_id = m.deal_id
                ORDER BY m.created_at DESC LIMIT 20
            """)).fetchall()
    if not rows:
        return "No messages found."
    lines = ["## Messages & Tasks\n", "| Deal | Subject | Type | Status | Due |",
             "|------|---------|------|--------|-----|"]
    for r in rows:
        lines.append(f"| {r[1] or '—'} | {r[2] or '—'} | {r[3]} | {r[4]} | {r[5] or '—'} |")
    return "\n".join(lines)


def register_routes(rt):

    @rt("/module/comms")
    def module_comms(session):
        pool = get_pool()
        with pool.get_session() as s:
            msgs = s.execute(text("""
                SELECT m.message_id, d.title AS deal_title, m.subject, m.body,
                       m.message_type, m.status, m.due_date, m.created_at
                FROM ahmf.messages m
                LEFT JOIN ahmf.deals d ON d.deal_id = m.deal_id
                ORDER BY m.created_at DESC LIMIT 50
            """)).fetchall()
            stats = s.execute(text("""
                SELECT COUNT(*),
                    COUNT(CASE WHEN message_type = 'task' AND status = 'open' THEN 1 END),
                    COUNT(CASE WHEN status = 'completed' THEN 1 END),
                    COUNT(CASE WHEN message_type = 'task' AND due_date < CURRENT_DATE AND status = 'open' THEN 1 END)
                FROM ahmf.messages
            """)).fetchone()

        total = stats[0] if stats else 0
        open_tasks = stats[1] if stats else 0
        completed = stats[2] if stats else 0
        overdue = stats[3] if stats else 0

        rows = []
        for m in msgs:
            color = _type_color(m[4])
            is_task = m[4] == "task"
            is_done = m[5] == "completed"
            due_str = f" | Due: {m[6]}" if m[6] else ""
            overdue_flag = m[6] and str(m[6]) < str(m[7])[:10] if m[6] and m[5] == "open" else False

            rows.append(Div(
                Div(
                    Div(
                        Input(type="checkbox", checked=is_done,
                              hx_post=f"/module/comms/toggle/{m[0]}", hx_target="#center-content", hx_swap="innerHTML",
                              style="margin-right:0.5rem;cursor:pointer;") if is_task else
                        Span(m[4].title(), style=f"color:{color};font-weight:600;font-size:0.75rem;margin-right:0.5rem;"),
                        Span(m[2] or "No subject", cls="deal-card-title",
                             style=f"{'text-decoration:line-through;color:#94a3b8;' if is_done else ''}"),
                        style="display:flex;align-items:center;",
                    ),
                    Span((m[5] or "open").title(),
                         style=f"font-size:0.7rem;font-weight:600;color:{'#16a34a' if is_done else '#f59e0b' if not overdue_flag else '#dc2626'};"),
                    style="display:flex;justify-content:space-between;align-items:center;",
                ),
                Div(f"{m[1] or 'No deal'}{due_str}", cls="deal-card-meta"),
                cls="deal-card",
                hx_get=f"/module/comms/{m[0]}", hx_target="#center-content", hx_swap="innerHTML",
            ))

        return Div(
            Div(H1("Communications"),
                Button("+ New Message", cls="auth-btn", hx_get="/module/comms/new", hx_target="#center-content", hx_swap="innerHTML"),
                style="display:flex;justify-content:space-between;align-items:center;"),
            Div(
                Div(Div("Total", cls="stat-label"), Div(str(total), cls="stat-value"), cls="stat-card"),
                Div(Div("Open Tasks", cls="stat-label"), Div(str(open_tasks), cls="stat-value", style="color:#f59e0b;"), cls="stat-card"),
                Div(Div("Completed", cls="stat-label"), Div(str(completed), cls="stat-value", style="color:#16a34a;"), cls="stat-card"),
                Div(Div("Overdue", cls="stat-label"), Div(str(overdue), cls="stat-value", style="color:#dc2626;"), cls="stat-card"),
                cls="stats-grid",
            ),
            H2("Messages & Tasks"),
            Div(*rows) if rows else P("No messages yet.", style="color:#94a3b8;text-align:center;padding:2rem;"),
            cls="module-content",
        )

    @rt("/module/comms/new")
    def comms_new(session):
        pool = get_pool()
        with pool.get_session() as s:
            deals = s.execute(text("SELECT deal_id, title FROM ahmf.deals ORDER BY title")).fetchall()
        deal_opts = [Option("— No Deal —", value="")] + [Option(d[1], value=str(d[0])) for d in deals]
        type_opts = [Option(t.title(), value=t) for t in MSG_TYPES]

        return Div(
            H1("New Message / Task"),
            Form(
                Div(Div(Label("Deal", Select(*deal_opts, name="deal_id")), style="flex:1"),
                    Div(Label("Type", Select(*type_opts, name="message_type")), style="flex:1"),
                    style="display:flex;gap:1rem;"),
                Label("Subject", Input(type="text", name="subject", required=True, placeholder="Subject line")),
                Label("Body", Textarea(name="body", rows="4", placeholder="Message content or task description...",
                      style="width:100%;padding:0.5rem;border:1px solid #e2e8f0;border-radius:8px;font-family:inherit;")),
                Div(Div(Label("Due Date (for tasks)", Input(type="date", name="due_date")), style="flex:1"),
                    Div(Label("Assigned To", Input(type="text", name="assigned_to", placeholder="Name or email")), style="flex:1"),
                    style="display:flex;gap:1rem;"),
                Button("Send", type="submit", cls="auth-btn"),
                cls="auth-form", hx_post="/module/comms/create", hx_target="#center-content", hx_swap="innerHTML",
            ),
            cls="module-content",
        )

    @rt("/module/comms/create", methods=["POST"])
    def comms_create(session, deal_id: str = "", message_type: str = "note",
                     subject: str = "", body: str = "", due_date: str = "", assigned_to: str = ""):
        pool = get_pool()
        with pool.get_session() as s:
            s.execute(text("""
                INSERT INTO ahmf.messages (deal_id, from_user, subject, body, message_type, due_date, status)
                VALUES (:did, :uid, :subj, :body, :type, :due, 'open')
            """), {"did": deal_id or None, "uid": session.get("user_id"), "subj": subject,
                   "body": body, "type": message_type, "due": due_date or None})
        return module_comms(session)

    @rt("/module/comms/toggle/{message_id}", methods=["POST"])
    def comms_toggle(message_id: str, session):
        pool = get_pool()
        with pool.get_session() as s:
            s.execute(text("""
                UPDATE ahmf.messages
                SET status = CASE WHEN status = 'completed' THEN 'open' ELSE 'completed' END
                WHERE message_id = :mid
            """), {"mid": message_id})
        return module_comms(session)

    @rt("/module/comms/{message_id}")
    def comms_detail(message_id: str, session):
        pool = get_pool()
        with pool.get_session() as s:
            row = s.execute(text("""
                SELECT m.subject, m.body, m.message_type, m.status, m.due_date, m.created_at,
                       d.title AS deal_title
                FROM ahmf.messages m
                LEFT JOIN ahmf.deals d ON d.deal_id = m.deal_id
                WHERE m.message_id = :mid
            """), {"mid": message_id}).fetchone()
        if not row:
            return Div(P("Message not found."), cls="module-content")

        color = _type_color(row[2])
        return Div(
            H1(row[0] or "No Subject"),
            Div(
                Span(row[2].title(), style=f"color:{color};font-weight:600;margin-right:1rem;"),
                Span(f"Status: {(row[3] or 'open').title()}", style="margin-right:1rem;"),
                Span(f"Deal: {row[6] or 'None'}", style="color:#64748b;"),
                style="margin-bottom:1rem;font-size:0.85rem;",
            ),
            Div(P(row[1] or "No content.", style="white-space:pre-wrap;color:#475569;line-height:1.6;"),
                style="padding:1rem;background:#f8fafc;border-radius:12px;border:1px solid #e2e8f0;"),
            Div(
                Span(f"Due: {row[4]}" if row[4] else "", style="color:#f59e0b;margin-right:1rem;"),
                Span(f"Created: {row[5].strftime('%b %d, %Y %H:%M') if row[5] else ''}", style="color:#94a3b8;"),
                style="margin-top:1rem;font-size:0.8rem;",
            ),
            Button("Back", cls="auth-btn", style="margin-top:1.5rem;", onclick="loadModule('/module/comms', 'Communications')"),
            cls="module-content",
        )
