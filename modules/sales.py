"""
Sales & Collections Module

Territory-based sales contract tracking, collection management,
variance analysis, and receivable monitoring.
"""

import json, logging
from fasthtml.common import *
from sqlalchemy import text
from utils.db import get_pool
from config.settings import TERRITORIES, CURRENCIES

logger = logging.getLogger(__name__)


def _status_color(status):
    return {"pending": "#f59e0b", "received": "#16a34a", "overdue": "#dc2626", "draft": "#94a3b8", "active": "#0066cc", "completed": "#16a34a"}.get(status, "#64748b")


def search_sales_contracts(query: str = "") -> str:
    """Search sales contracts by territory, deal title, or distributor name."""
    pool = get_pool()
    with pool.get_session() as s:
        if query:
            rows = s.execute(text("""
                SELECT sc.contract_id, d.title, sc.territory, c.name AS distributor,
                       sc.mg_amount, sc.currency, sc.status
                FROM ahmf.sales_contracts sc
                LEFT JOIN ahmf.deals d ON d.deal_id = sc.deal_id
                LEFT JOIN ahmf.contacts c ON c.contact_id = sc.distributor_id
                WHERE sc.territory ILIKE :q OR d.title ILIKE :q OR c.name ILIKE :q
                ORDER BY sc.created_at DESC LIMIT 20
            """), {"q": f"%{query}%"}).fetchall()
        else:
            rows = s.execute(text("""
                SELECT sc.contract_id, d.title, sc.territory, c.name AS distributor,
                       sc.mg_amount, sc.currency, sc.status
                FROM ahmf.sales_contracts sc
                LEFT JOIN ahmf.deals d ON d.deal_id = sc.deal_id
                LEFT JOIN ahmf.contacts c ON c.contact_id = sc.distributor_id
                ORDER BY sc.created_at DESC LIMIT 20
            """)).fetchall()
    if not rows:
        return "No sales contracts found."
    lines = ["## Sales Contracts\n", "| Deal | Territory | Distributor | MG | Status |",
             "|------|-----------|-------------|-----|--------|"]
    for r in rows:
        mg = f"${r[4]:,.0f}" if r[4] else "—"
        lines.append(f"| {r[1] or '—'} | {r[2] or '—'} | {r[3] or '—'} | {mg} | {r[6] or '—'} |")
    return "\n".join(lines)


def register_routes(rt):

    @rt("/module/sales")
    def module_sales(session):
        pool = get_pool()
        with pool.get_session() as s:
            contracts = s.execute(text("""
                SELECT sc.contract_id, d.title, sc.territory, c.name AS distributor,
                       sc.mg_amount, sc.currency, sc.status, sc.created_at
                FROM ahmf.sales_contracts sc
                LEFT JOIN ahmf.deals d ON d.deal_id = sc.deal_id
                LEFT JOIN ahmf.contacts c ON c.contact_id = sc.distributor_id
                ORDER BY sc.created_at DESC LIMIT 30
            """)).fetchall()
            stats = s.execute(text("""
                SELECT COUNT(*), COALESCE(SUM(mg_amount), 0) FROM ahmf.sales_contracts
            """)).fetchone()
            coll_stats = s.execute(text("""
                SELECT
                    COALESCE(SUM(amount_received), 0),
                    COALESCE(SUM(CASE WHEN status = 'overdue' THEN amount_due - amount_received ELSE 0 END), 0),
                    COUNT(CASE WHEN status = 'overdue' THEN 1 END)
                FROM ahmf.collections
            """)).fetchone()

        total_contracts = stats[0] if stats else 0
        total_mg = stats[1] if stats else 0
        total_collected = coll_stats[0] if coll_stats else 0
        total_overdue = coll_stats[1] if coll_stats else 0

        rows = []
        for c in contracts:
            color = _status_color(c[6] or "draft")
            mg = f"${c[4]:,.0f}" if c[4] else "—"
            rows.append(Div(
                Div(Span(f"{c[1] or 'Untitled'} — {c[2] or '?'}", cls="deal-card-title"),
                    Span((c[6] or "draft").title(), cls="status-pill", style=f"background:{color}20;color:{color};"),
                    style="display:flex;justify-content:space-between;align-items:center;"),
                Div(f"{c[3] or 'No distributor'} | {mg}", cls="deal-card-meta"),
                cls="deal-card", hx_get=f"/module/sales/{c[0]}", hx_target="#center-content", hx_swap="innerHTML",
            ))

        return Div(
            Div(H1("Sales & Collections"),
                Button("+ New Contract", cls="auth-btn", hx_get="/module/sales/new", hx_target="#center-content", hx_swap="innerHTML"),
                style="display:flex;justify-content:space-between;align-items:center;"),
            Div(
                Div(Div("Contracts", cls="stat-label"), Div(str(total_contracts), cls="stat-value"), cls="stat-card"),
                Div(Div("Total MG", cls="stat-label"), Div(f"${total_mg:,.0f}", cls="stat-value", style="color:#0066cc;"), cls="stat-card"),
                Div(Div("Collected", cls="stat-label"), Div(f"${total_collected:,.0f}", cls="stat-value", style="color:#16a34a;"), cls="stat-card"),
                Div(Div("Overdue", cls="stat-label"), Div(f"${total_overdue:,.0f}", cls="stat-value", style="color:#dc2626;"), cls="stat-card"),
                cls="stats-grid",
            ),
            H2("Contracts"),
            Div(*rows) if rows else P("No contracts yet. Create your first sales contract.", style="color:#94a3b8;text-align:center;padding:2rem;"),
            cls="module-content",
        )

    @rt("/module/sales/new")
    def sales_new(session):
        pool = get_pool()
        with pool.get_session() as s:
            deals = s.execute(text("SELECT deal_id, title FROM ahmf.deals ORDER BY title")).fetchall()
            distributors = s.execute(text("SELECT contact_id, name FROM ahmf.contacts WHERE contact_type IN ('distributor','sales_agent') ORDER BY name")).fetchall()
        deal_opts = [Option(d[1], value=str(d[0])) for d in deals]
        dist_opts = [Option("— None —", value="")] + [Option(d[1], value=str(d[0])) for d in distributors]
        terr_opts = [Option(t, value=t) for t in TERRITORIES]
        curr_opts = [Option(c, value=c) for c in CURRENCIES]

        return Div(
            H1("New Sales Contract"),
            Form(
                Div(Div(Label("Deal", Select(*deal_opts, name="deal_id", required=True)), style="flex:1"),
                    Div(Label("Territory", Select(*terr_opts, name="territory")), style="flex:1"),
                    style="display:flex;gap:1rem;"),
                Div(Div(Label("Distributor", Select(*dist_opts, name="distributor_id")), style="flex:1"),
                    Div(Label("Status", Select(Option("Draft", value="draft"), Option("Active", value="active"),
                                                Option("Completed", value="completed"), name="status")), style="flex:1"),
                    style="display:flex;gap:1rem;"),
                Div(Div(Label("MG Amount", Input(type="number", name="mg_amount", placeholder="0", step="0.01")), style="flex:1"),
                    Div(Label("Currency", Select(*curr_opts, name="currency")), style="flex:1"),
                    style="display:flex;gap:1rem;"),
                Button("Create Contract", type="submit", cls="auth-btn"),
                cls="auth-form", hx_post="/module/sales/create", hx_target="#center-content", hx_swap="innerHTML",
            ),
            cls="module-content",
        )

    @rt("/module/sales/create", methods=["POST"])
    def sales_create(session, deal_id: str, territory: str = "", distributor_id: str = "",
                     mg_amount: float = 0, currency: str = "USD", status: str = "draft"):
        pool = get_pool()
        with pool.get_session() as s:
            s.execute(text("""
                INSERT INTO ahmf.sales_contracts (deal_id, territory, distributor_id, mg_amount, currency, status, created_by)
                VALUES (:did, :terr, :dist, :mg, :curr, :status, :uid)
            """), {"did": deal_id, "terr": territory, "dist": distributor_id or None,
                   "mg": mg_amount or None, "curr": currency, "status": status, "uid": session.get("user_id")})
        return module_sales(session)

    @rt("/module/sales/{contract_id}")
    def sales_detail(contract_id: str, session):
        pool = get_pool()
        with pool.get_session() as s:
            row = s.execute(text("""
                SELECT sc.contract_id, d.title, sc.territory, c.name, sc.mg_amount, sc.currency, sc.status, sc.created_at
                FROM ahmf.sales_contracts sc
                LEFT JOIN ahmf.deals d ON d.deal_id = sc.deal_id
                LEFT JOIN ahmf.contacts c ON c.contact_id = sc.distributor_id
                WHERE sc.contract_id = :cid
            """), {"cid": contract_id}).fetchone()
            collections = s.execute(text("""
                SELECT collection_id, amount_due, amount_received, due_date, received_date, status
                FROM ahmf.collections WHERE contract_id = :cid ORDER BY due_date
            """), {"cid": contract_id}).fetchall()
        if not row:
            return Div(P("Contract not found."), cls="module-content")

        mg = f"${row[4]:,.0f}" if row[4] else "—"
        total_due = sum(c[1] or 0 for c in collections)
        total_recv = sum(c[2] or 0 for c in collections)
        variance = total_recv - total_due

        coll_rows = []
        for c in collections:
            color = _status_color(c[5] or "pending")
            coll_rows.append(Tr(
                Td(f"${c[1]:,.0f}" if c[1] else "—"), Td(f"${c[2]:,.0f}" if c[2] else "—"),
                Td(str(c[3]) if c[3] else "—"), Td(str(c[4]) if c[4] else "—"),
                Td(Span((c[5] or "pending").title(), style=f"color:{color};font-weight:600;")),
            ))

        return Div(
            H1(f"{row[1] or 'Contract'} — {row[2] or '?'}"),
            Div(
                Div(Div("MG Amount", cls="stat-label"), Div(mg, cls="stat-value", style="color:#0066cc;"), cls="stat-card"),
                Div(Div("Collected", cls="stat-label"), Div(f"${total_recv:,.0f}", cls="stat-value", style="color:#16a34a;"), cls="stat-card"),
                Div(Div("Variance", cls="stat-label"), Div(f"${variance:,.0f}", cls="stat-value",
                    style=f"color:{'#16a34a' if variance >= 0 else '#dc2626'};"), cls="stat-card"),
                cls="stats-grid",
            ),
            Div(P(f"Distributor: {row[3] or '—'} | Currency: {row[5]} | Status: {(row[6] or 'draft').title()}"),
                style="color:#475569;margin:1rem 0;"),
            H2("Collections"),
            Table(Thead(Tr(Th("Due"), Th("Received"), Th("Due Date"), Th("Received Date"), Th("Status"))),
                  Tbody(*coll_rows) if coll_rows else Tbody(Tr(Td("No collections recorded.", colspan="5", style="color:#94a3b8;text-align:center;"))),
                  style="width:100%;border-collapse:collapse;font-size:0.85rem;"),
            Div(
                H3("Record Payment", style="font-size:0.95rem;margin-top:1.5rem;"),
                Form(
                    Div(Div(Input(type="number", name="amount_due", placeholder="Amount due", step="0.01"), style="flex:1"),
                        Div(Input(type="number", name="amount_received", placeholder="Amount received", step="0.01"), style="flex:1"),
                        Div(Input(type="date", name="due_date"), style="flex:1"),
                        Button("Add", type="submit", cls="auth-btn"),
                        style="display:flex;gap:0.5rem;align-items:end;"),
                    hx_post=f"/module/sales/collection/{contract_id}", hx_target="#center-content", hx_swap="innerHTML",
                ),
                style="padding:1rem;background:#f8fafc;border-radius:12px;border:1px solid #e2e8f0;margin-top:1rem;",
            ),
            Button("Back", cls="auth-btn", style="margin-top:1.5rem;", onclick="loadModule('/module/sales', 'Sales & Collections')"),
            cls="module-content",
        )

    @rt("/module/sales/collection/{contract_id}", methods=["POST"])
    def sales_add_collection(contract_id: str, session, amount_due: float = 0,
                             amount_received: float = 0, due_date: str = ""):
        pool = get_pool()
        status = "received" if amount_received >= amount_due and amount_due > 0 else "pending"
        with pool.get_session() as s:
            s.execute(text("""
                INSERT INTO ahmf.collections (contract_id, amount_due, amount_received, due_date, status)
                VALUES (:cid, :due, :recv, :ddate, :status)
            """), {"cid": contract_id, "due": amount_due or None, "recv": amount_received or None,
                   "ddate": due_date or None, "status": status})
        return sales_detail(contract_id, session)
