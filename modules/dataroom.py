"""
Product 7: Deal Closing & Data Room Automation

Per-deal closing dashboards with auto-generated checklists,
document tracking, and milestone management.
"""

import json, logging
from fasthtml.common import *
from sqlalchemy import text
from utils.db import get_pool
from config.settings import CLOSING_CHECKLIST_TEMPLATE

logger = logging.getLogger(__name__)


def generate_closing_checklist_tool(deal_id: str) -> str:
    """Generate a closing checklist for a deal and return its status."""
    pool = get_pool()
    with pool.get_session() as s:
        deal = s.execute(text("SELECT title FROM ahmf.deals WHERE deal_id = :did"), {"did": deal_id}).fetchone()
        if not deal:
            return f"Deal {deal_id} not found."
        existing = s.execute(text("SELECT checklist_id FROM ahmf.closing_checklists WHERE deal_id = :did"), {"did": deal_id}).fetchone()
        if existing:
            return f"Checklist already exists for **{deal[0]}**. Use `closing:{deal_id[:8]}` to view it."

        result = s.execute(text("""
            INSERT INTO ahmf.closing_checklists (deal_id, title) VALUES (:did, :title) RETURNING checklist_id
        """), {"did": deal_id, "title": f"Closing Checklist — {deal[0]}"})
        checklist_id = str(result.scalar())
        for i, (cat, desc) in enumerate(CLOSING_CHECKLIST_TEMPLATE):
            s.execute(text("""
                INSERT INTO ahmf.checklist_items (checklist_id, category, description, sort_order)
                VALUES (:cid, :cat, :desc, :order)
            """), {"cid": checklist_id, "cat": cat, "desc": desc, "order": i})

    return f"Closing checklist created for **{deal[0]}** with {len(CLOSING_CHECKLIST_TEMPLATE)} items."


def register_routes(rt):

    @rt("/module/dataroom")
    def module_dataroom(session):
        pool = get_pool()
        with pool.get_session() as s:
            deals_with_checklists = s.execute(text("""
                SELECT d.deal_id, d.title, d.status, cl.checklist_id,
                    (SELECT COUNT(*) FROM ahmf.checklist_items ci WHERE ci.checklist_id = cl.checklist_id) AS total,
                    (SELECT COUNT(*) FROM ahmf.checklist_items ci WHERE ci.checklist_id = cl.checklist_id AND ci.is_completed = TRUE) AS done
                FROM ahmf.deals d
                LEFT JOIN ahmf.closing_checklists cl ON cl.deal_id = d.deal_id
                WHERE d.status IN ('active', 'pipeline')
                ORDER BY d.created_at DESC LIMIT 20
            """)).fetchall()

        rows = []
        for d in deals_with_checklists:
            deal_id, title, status, checklist_id, total, done = d
            total = total or 0
            done = done or 0
            pct = int((done / total * 100) if total > 0 else 0)
            has_checklist = checklist_id is not None

            progress_bar = Div(
                Div(style=f"width:{pct}%;height:6px;background:#0066cc;border-radius:3px;"),
                style="width:100%;height:6px;background:#e2e8f0;border-radius:3px;margin-top:0.4rem;",
            ) if has_checklist else ""

            rows.append(Div(
                Div(
                    Span(title, cls="deal-card-title"),
                    Span(f"{done}/{total}" if has_checklist else "No checklist",
                         style=f"font-size:0.75rem;color:{'#0066cc' if has_checklist else '#94a3b8'};"),
                    style="display:flex;justify-content:space-between;align-items:center;",
                ),
                progress_bar,
                cls="deal-card",
                hx_get=f"/module/dataroom/{deal_id}" if has_checklist else f"/module/dataroom/create/{deal_id}",
                hx_target="#center-content", hx_swap="innerHTML",
            ))

        return Div(
            H1("Deal Closing & Data Room"),
            P("Manage closing workflows, checklists, and document tracking per deal.", style="color:#64748b;margin-bottom:1.5rem;"),
            Div(*rows) if rows else P("No active deals. Create a deal first.", style="color:#94a3b8;text-align:center;padding:2rem;"),
            cls="module-content",
        )

    @rt("/module/dataroom/create/{deal_id}")
    def dataroom_create(deal_id: str, session):
        pool = get_pool()
        with pool.get_session() as s:
            deal = s.execute(text("SELECT title FROM ahmf.deals WHERE deal_id = :did"), {"did": deal_id}).fetchone()
            if not deal:
                return Div(P("Deal not found."), cls="module-content")
            result = s.execute(text("""
                INSERT INTO ahmf.closing_checklists (deal_id, title, created_by) VALUES (:did, :title, :uid) RETURNING checklist_id
            """), {"did": deal_id, "title": f"Closing — {deal[0]}", "uid": session.get("user_id")})
            checklist_id = str(result.scalar())
            for i, (cat, desc) in enumerate(CLOSING_CHECKLIST_TEMPLATE):
                s.execute(text("""
                    INSERT INTO ahmf.checklist_items (checklist_id, category, description, sort_order)
                    VALUES (:cid, :cat, :desc, :order)
                """), {"cid": checklist_id, "cat": cat, "desc": desc, "order": i})
        # Redirect to the closing dashboard
        return _render_closing_dashboard(deal_id, session)

    @rt("/module/dataroom/{deal_id}")
    def dataroom_detail(deal_id: str, session):
        return _render_closing_dashboard(deal_id, session)

    @rt("/module/dataroom/toggle/{item_id}", methods=["POST"])
    def dataroom_toggle(item_id: str, session):
        pool = get_pool()
        with pool.get_session() as s:
            s.execute(text("""
                UPDATE ahmf.checklist_items
                SET is_completed = NOT is_completed,
                    completed_at = CASE WHEN is_completed THEN NULL ELSE NOW() END
                WHERE item_id = :iid
            """), {"iid": item_id})
            row = s.execute(text("""
                SELECT ci.checklist_id, cl.deal_id FROM ahmf.checklist_items ci
                JOIN ahmf.closing_checklists cl ON cl.checklist_id = ci.checklist_id
                WHERE ci.item_id = :iid
            """), {"iid": item_id}).fetchone()
        if row:
            return _render_closing_dashboard(str(row[1]), session)
        return P("Error toggling item.")

    def _render_closing_dashboard(deal_id, session):
        pool = get_pool()
        with pool.get_session() as s:
            deal = s.execute(text("SELECT title, status FROM ahmf.deals WHERE deal_id = :did"), {"did": deal_id}).fetchone()
            checklist = s.execute(text("SELECT checklist_id FROM ahmf.closing_checklists WHERE deal_id = :did"), {"did": deal_id}).fetchone()
            if not deal or not checklist:
                return Div(P("Deal or checklist not found."), cls="module-content")
            items = s.execute(text("""
                SELECT item_id, category, description, is_completed, assigned_to
                FROM ahmf.checklist_items WHERE checklist_id = :cid ORDER BY sort_order
            """), {"cid": str(checklist[0])}).fetchall()
            docs = s.execute(text("""
                SELECT doc_id, doc_type, filename, version, uploaded_at
                FROM ahmf.deal_documents WHERE deal_id = :did ORDER BY uploaded_at DESC
            """), {"did": deal_id}).fetchall()

        total = len(items)
        done = sum(1 for i in items if i[3])
        pct = int((done / total * 100) if total > 0 else 0)

        # Group items by category
        categories = {}
        for item in items:
            cat = item[1] or "General"
            categories.setdefault(cat, []).append(item)

        checklist_sections = []
        for cat, cat_items in categories.items():
            cat_done = sum(1 for i in cat_items if i[3])
            item_els = []
            for item in cat_items:
                checked = "checked" if item[3] else ""
                item_els.append(Div(
                    Input(type="checkbox", checked=item[3],
                          hx_post=f"/module/dataroom/toggle/{item[0]}", hx_target="#center-content", hx_swap="innerHTML",
                          style="margin-right:0.5rem;cursor:pointer;"),
                    Span(item[2], style=f"{'text-decoration:line-through;color:#94a3b8;' if item[3] else 'color:#1e293b;'}font-size:0.85rem;"),
                    style="display:flex;align-items:center;padding:0.4rem 0;",
                ))
            checklist_sections.append(Div(
                H3(f"{cat} ({cat_done}/{len(cat_items)})", style="font-size:0.85rem;color:#64748b;margin:0.75rem 0 0.25rem;"),
                *item_els,
            ))

        doc_rows = [Tr(Td(d[1] or "—"), Td(d[2] or "—"), Td(f"v{d[3]}"), Td(d[4].strftime('%b %d') if d[4] else ""))
                    for d in docs]

        return Div(
            H1(f"Closing: {deal[0]}"),
            Div(
                Div(Div("Progress", cls="stat-label"), Div(f"{pct}%", cls="stat-value", style="color:#0066cc;"), cls="stat-card"),
                Div(Div("Items", cls="stat-label"), Div(f"{done}/{total}", cls="stat-value"), cls="stat-card"),
                Div(Div("Documents", cls="stat-label"), Div(str(len(docs)), cls="stat-value"), cls="stat-card"),
                cls="stats-grid",
            ),
            Div(
                Div(style=f"width:{pct}%;height:8px;background:#0066cc;border-radius:4px;transition:width 0.3s;"),
                style="width:100%;height:8px;background:#e2e8f0;border-radius:4px;margin-bottom:1.5rem;",
            ),
            H2("Checklist"),
            Div(*checklist_sections, style="padding:0.5rem 0;"),
            H2("Documents", style="margin-top:1.5rem;"),
            Table(Thead(Tr(Th("Type"), Th("File"), Th("Version"), Th("Uploaded"))),
                  Tbody(*doc_rows) if doc_rows else Tbody(Tr(Td("No documents uploaded yet.", colspan="4", style="color:#94a3b8;text-align:center;"))),
                  style="width:100%;border-collapse:collapse;font-size:0.85rem;"),
            Button("Back", cls="auth-btn", style="margin-top:1.5rem;", onclick="loadModule('/module/dataroom', 'Data Room')"),
            cls="module-content",
        )
