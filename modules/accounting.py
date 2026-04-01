"""
Accounting Module

Transaction ledger, multi-account balance tracking,
payment audit trail, and reconciliation.
"""

import logging
from fasthtml.common import *
from sqlalchemy import text
from utils.db import get_pool
from config.settings import CURRENCIES

logger = logging.getLogger(__name__)

TXN_TYPES = ["disbursement", "repayment", "fee", "interest", "adjustment"]


def _txn_color(txn_type):
    return {"disbursement": "#dc2626", "repayment": "#16a34a", "fee": "#f59e0b",
            "interest": "#f97316", "adjustment": "#64748b"}.get(txn_type, "#475569")


def search_transactions(query: str = "") -> str:
    """Search accounting transactions by deal title, type, or counterparty."""
    pool = get_pool()
    with pool.get_session() as s:
        if query:
            rows = s.execute(text("""
                SELECT t.txn_id, d.title, t.txn_type, t.amount, t.currency, c.name, t.posted_date
                FROM ahmf.transactions t
                LEFT JOIN ahmf.deals d ON d.deal_id = t.deal_id
                LEFT JOIN ahmf.contacts c ON c.contact_id = t.counterparty_id
                WHERE d.title ILIKE :q OR t.txn_type ILIKE :q OR c.name ILIKE :q OR t.reference ILIKE :q
                ORDER BY t.posted_date DESC LIMIT 20
            """), {"q": f"%{query}%"}).fetchall()
        else:
            rows = s.execute(text("""
                SELECT t.txn_id, d.title, t.txn_type, t.amount, t.currency, c.name, t.posted_date
                FROM ahmf.transactions t
                LEFT JOIN ahmf.deals d ON d.deal_id = t.deal_id
                LEFT JOIN ahmf.contacts c ON c.contact_id = t.counterparty_id
                ORDER BY t.posted_date DESC LIMIT 20
            """)).fetchall()
    if not rows:
        return "No transactions found."
    lines = ["## Transactions\n", "| Deal | Type | Amount | Counterparty | Date |",
             "|------|------|--------|--------------|------|"]
    for r in rows:
        amt = f"{r[4]} {r[3]:,.2f}" if r[3] else "—"
        lines.append(f"| {r[1] or '—'} | {r[2]} | {amt} | {r[5] or '—'} | {r[6] or '—'} |")
    return "\n".join(lines)


def register_routes(rt):

    @rt("/module/accounting")
    def module_accounting(session):
        pool = get_pool()
        with pool.get_session() as s:
            txns = s.execute(text("""
                SELECT t.txn_id, d.title, t.txn_type, t.amount, t.currency, c.name, t.posted_date, t.reference
                FROM ahmf.transactions t
                LEFT JOIN ahmf.deals d ON d.deal_id = t.deal_id
                LEFT JOIN ahmf.contacts c ON c.contact_id = t.counterparty_id
                ORDER BY t.posted_date DESC LIMIT 50
            """)).fetchall()
            stats = s.execute(text("""
                SELECT COUNT(*),
                    COALESCE(SUM(CASE WHEN txn_type = 'disbursement' THEN amount ELSE 0 END), 0),
                    COALESCE(SUM(CASE WHEN txn_type = 'repayment' THEN amount ELSE 0 END), 0),
                    COALESCE(SUM(CASE WHEN txn_type = 'fee' THEN amount ELSE 0 END), 0),
                    COALESCE(SUM(CASE WHEN txn_type = 'interest' THEN amount ELSE 0 END), 0)
                FROM ahmf.transactions
            """)).fetchone()

        total = stats[0] if stats else 0
        disbursed = stats[1] if stats else 0
        repaid = stats[2] if stats else 0
        fees = stats[3] if stats else 0
        interest = stats[4] if stats else 0
        net = repaid + fees + interest - disbursed

        txn_rows = []
        for t in txns:
            color = _txn_color(t[2])
            sign = "-" if t[2] == "disbursement" else "+"
            txn_rows.append(Tr(
                Td(str(t[6]) if t[6] else "—", style="font-size:0.8rem;"),
                Td(t[1] or "—"),
                Td(Span(t[2].title(), style=f"color:{color};font-weight:600;")),
                Td(f"{sign}${t[3]:,.2f}" if t[3] else "—", style=f"text-align:right;color:{color};font-weight:600;"),
                Td(t[4] or "USD"),
                Td(t[5] or "—"),
                Td(t[7] or "—", style="font-size:0.8rem;color:#94a3b8;"),
            ))

        return Div(
            Div(H1("Accounting"),
                Button("+ New Transaction", cls="auth-btn", hx_get="/module/accounting/new", hx_target="#center-content", hx_swap="innerHTML"),
                style="display:flex;justify-content:space-between;align-items:center;"),
            Div(
                Div(Div("Transactions", cls="stat-label"), Div(str(total), cls="stat-value"), cls="stat-card"),
                Div(Div("Disbursed", cls="stat-label"), Div(f"${disbursed:,.0f}", cls="stat-value", style="color:#dc2626;"), cls="stat-card"),
                Div(Div("Repaid", cls="stat-label"), Div(f"${repaid:,.0f}", cls="stat-value", style="color:#16a34a;"), cls="stat-card"),
                Div(Div("Net Position", cls="stat-label"), Div(f"${net:,.0f}", cls="stat-value",
                    style=f"color:{'#16a34a' if net >= 0 else '#dc2626'};"), cls="stat-card"),
                cls="stats-grid",
            ),
            H2("Transaction Ledger"),
            Table(
                Thead(Tr(Th("Date"), Th("Deal"), Th("Type"), Th("Amount", style="text-align:right;"), Th("Curr"), Th("Counterparty"), Th("Ref"))),
                Tbody(*txn_rows) if txn_rows else Tbody(Tr(Td("No transactions yet.", colspan="7", style="color:#94a3b8;text-align:center;padding:2rem;"))),
                style="width:100%;border-collapse:collapse;font-size:0.85rem;",
            ),
            cls="module-content",
        )

    @rt("/module/accounting/new")
    def accounting_new(session):
        pool = get_pool()
        with pool.get_session() as s:
            deals = s.execute(text("SELECT deal_id, title FROM ahmf.deals ORDER BY title")).fetchall()
            contacts = s.execute(text("SELECT contact_id, name FROM ahmf.contacts ORDER BY name")).fetchall()
        deal_opts = [Option("— Select Deal —", value="")] + [Option(d[1], value=str(d[0])) for d in deals]
        contact_opts = [Option("— None —", value="")] + [Option(c[1], value=str(c[0])) for c in contacts]
        type_opts = [Option(t.title(), value=t) for t in TXN_TYPES]
        curr_opts = [Option(c, value=c) for c in CURRENCIES]

        return Div(
            H1("New Transaction"),
            Form(
                Div(Div(Label("Deal", Select(*deal_opts, name="deal_id")), style="flex:1"),
                    Div(Label("Type", Select(*type_opts, name="txn_type")), style="flex:1"),
                    style="display:flex;gap:1rem;"),
                Div(Div(Label("Amount", Input(type="number", name="amount", step="0.01", placeholder="0.00", required=True)), style="flex:1"),
                    Div(Label("Currency", Select(*curr_opts, name="currency")), style="flex:1"),
                    style="display:flex;gap:1rem;"),
                Div(Div(Label("Counterparty", Select(*contact_opts, name="counterparty_id")), style="flex:1"),
                    Div(Label("Date", Input(type="date", name="posted_date")), style="flex:1"),
                    style="display:flex;gap:1rem;"),
                Label("Reference / Notes", Input(type="text", name="reference", placeholder="e.g. Wire transfer #12345")),
                Button("Record Transaction", type="submit", cls="auth-btn"),
                cls="auth-form", hx_post="/module/accounting/create", hx_target="#center-content", hx_swap="innerHTML",
            ),
            cls="module-content",
        )

    @rt("/module/accounting/create", methods=["POST"])
    def accounting_create(session, deal_id: str = "", txn_type: str = "disbursement",
                          amount: float = 0, currency: str = "USD", counterparty_id: str = "",
                          posted_date: str = "", reference: str = ""):
        pool = get_pool()
        with pool.get_session() as s:
            s.execute(text("""
                INSERT INTO ahmf.transactions (deal_id, txn_type, amount, currency, counterparty_id, posted_date, reference, created_by)
                VALUES (:did, :type, :amt, :curr, :cid, :date, :ref, :uid)
            """), {"did": deal_id or None, "type": txn_type, "amt": amount,
                   "curr": currency, "cid": counterparty_id or None,
                   "date": posted_date or None, "ref": reference, "uid": session.get("user_id")})
        return module_accounting(session)
