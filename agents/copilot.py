"""AI Copilot — context-aware text-to-SQL for dashboard interrogation.

Uses a two-step approach: LLM generates SQL, we execute it, LLM formats results.
"""

import os
import logging

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

logger = logging.getLogger(__name__)

def _load_schema() -> str:
    """Load schema from db_schema.json and format as text for the LLM."""
    import json
    schema_path = os.path.join(os.path.dirname(__file__), "..", "sql", "db_schema.json")
    try:
        with open(schema_path) as f:
            schema = json.load(f)
    except FileNotFoundError:
        logger.warning("db_schema.json not found, using empty schema")
        return ""
    lines = ["PostgreSQL schema 'ahmf' tables:\n"]
    for table, info in schema["tables"].items():
        cols = ", ".join(f"{col} {dtype}" for col, dtype in info["columns"].items())
        lines.append(f"{table} ({cols})\n")
    return "\n".join(lines)

AHMF_SCHEMA = _load_schema()

SQL_SYSTEM = f"""You are a SQL assistant for Ashland Hill Media Finance. Generate PostgreSQL SELECT queries against the 'ahmf' schema.

{AHMF_SCHEMA}

Rules:
- ONLY generate SELECT queries. Never INSERT, UPDATE, DELETE, DROP, ALTER.
- Always prefix table names with 'ahmf.' (e.g. ahmf.deals, ahmf.contacts)
- Return ONLY the SQL query, no explanation, no markdown fences.
- Use appropriate aggregations, JOINs, and ORDER BY as needed.
- Limit results to 20 rows unless the user asks for more.
"""

FORMAT_SYSTEM = """You are a data analyst for Ashland Hill Media Finance. Format query results into clear, concise answers.
- Use markdown tables for multi-row data
- Format monetary values with $ and commas (e.g. $1,500,000)
- Format percentages with % sign
- Be concise — no preamble, just the answer
- If the data is empty, say "No matching data found."
"""

MODULE_CONTEXT_PROMPTS = {
    "home": "The user is on the Home dashboard showing portfolio KPIs (IRR, Gross Yield, EP Fees, Profit Splits), a To-Do task list, and a deals carousel.",
    "deals": "The user is on the Deals page showing all deals with title, status, loan amount, borrower, and genre.",
    "deal": "The user is viewing a specific Live Deal detail page with loan terms, collateral breakdown, sales contracts, and communication log.",
    "sales": "The user is on Sales & Collections showing aggregate loan balance, sold/unsold values, sales accuracy, top sellers, and collections.",
    "accounting": "The user is on Accounting & Transactions showing multi-currency balances, cashflow trends, income/expenses, and loan statements.",
    "contacts": "The user is on Contacts showing a list of distributors, producers, sales agents, talent agencies with credit ratings.",
    "contact": "The user is viewing a specific contact's details, deals, communications, and analytics.",
    "tasks": "The user is on Tasks showing messages, tasks, and internal communications.",
    "reporting": "The user is on Reporting showing report templates, favorite charts, and saved reports.",
}

COPILOT_SHORTCUTS = {
    "home": [
        ("What's our total loan exposure?", "Sum of all active deal loan amounts"),
        ("Overdue tasks", "Show all tasks past their due date"),
        ("Portfolio IRR breakdown", "Average interest rate by deal status"),
        ("Deals closing this quarter", "Deals with maturity dates this quarter"),
    ],
    "deals": [
        ("Deals by genre", "Count and total loan by genre"),
        ("Largest deals", "Top 5 deals by loan amount"),
        ("Pipeline vs Active", "Compare pipeline and active deal counts"),
        ("Average deal size", "Mean loan amount across all deals"),
    ],
    "deal": [
        ("Show all contracts", "Sales contracts for this deal"),
        ("Transaction history", "All transactions for this deal"),
        ("Collection status", "Outstanding collections on this deal"),
    ],
    "sales": [
        ("Overdue collections", "Collections past due date"),
        ("MG by territory", "Total MG amounts grouped by territory"),
        ("Top distributors", "Distributors with highest total MG value"),
        ("Sales coverage ratio", "Percentage of loan covered by sales"),
    ],
    "accounting": [
        ("Cash in vs out", "Total disbursements vs repayments"),
        ("Recent transactions", "Last 10 transactions"),
        ("Interest accrued YTD", "Sum of interest payments this year"),
        ("Expenses by type", "Transaction totals grouped by type"),
    ],
    "contacts": [
        ("Credit ratings overview", "All contacts with credit ratings"),
        ("Top distributors by deals", "Contacts with most sales contracts"),
        ("Contact types breakdown", "Count of contacts by type"),
    ],
    "contact": [
        ("Deal history", "All deals linked to this contact"),
        ("Payment reliability", "Credit rating and payment history"),
        ("Total MG value", "Sum of MG amounts for this contact"),
    ],
    "tasks": [
        ("Open tasks", "All incomplete tasks"),
        ("Overdue items", "Tasks past their due date"),
        ("Recent messages", "Latest 10 messages"),
    ],
    "reporting": [
        ("Deals closed this quarter", "Recently closed deals"),
        ("Portfolio summary", "Aggregate stats across all deals"),
        ("Revenue forecast", "Projected collections by quarter"),
    ],
}


def _get_llm():
    return ChatOpenAI(
        api_key=os.getenv("XAI_API_KEY"),
        base_url="https://api.x.ai/v1",
        model="grok-3-mini",
        temperature=0,
    )


def _execute_sql(sql: str) -> str:
    from sqlalchemy import text
    from utils.db import get_pool
    pool = get_pool()
    with pool.get_session() as s:
        rows = s.execute(text(sql)).fetchall()
        if not rows:
            return "No results."
        cols = rows[0]._fields if hasattr(rows[0], '_fields') else [f"col{i}" for i in range(len(rows[0]))]
        lines = [" | ".join(str(c) for c in cols)]
        lines.append(" | ".join("---" for _ in cols))
        for r in rows[:20]:
            lines.append(" | ".join(str(v) for v in r))
        return "\n".join(lines)


async def copilot_query(question: str, module_id: str, extra_context: str = "") -> str:
    context = MODULE_CONTEXT_PROMPTS.get(module_id, "")
    llm = _get_llm()

    # Step 1: Generate SQL
    sql_prompt = f"{context}\n\nUser question: {question}"
    try:
        sql_response = await llm.ainvoke([
            SystemMessage(content=SQL_SYSTEM),
            HumanMessage(content=sql_prompt),
        ])
        sql = sql_response.content.strip()
        sql = sql.replace("```sql", "").replace("```", "").strip()
    except Exception as e:
        logger.error(f"Copilot SQL generation error: {e}")
        return f"Error generating query: {str(e)[:200]}"

    if not sql.upper().startswith("SELECT"):
        return f"I can only run SELECT queries. Generated: {sql[:100]}"

    # Step 2: Execute SQL
    try:
        result_table = _execute_sql(sql)
    except Exception as e:
        logger.error(f"Copilot SQL execution error: {e}")
        return f"Query error: {str(e)[:200]}"

    # Step 3: Format results
    try:
        format_response = await llm.ainvoke([
            SystemMessage(content=FORMAT_SYSTEM),
            HumanMessage(content=f"Question: {question}\n\nQuery results:\n{result_table}\n\nFormat this data as a clear answer."),
        ])
        return format_response.content.strip()
    except Exception as e:
        return f"Raw results:\n\n{result_table}"
