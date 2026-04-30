"""Unit tests for the AI Copilot text-to-SQL pipeline.

Tests every shortcut button query to ensure:
1. SQL generation succeeds (no LLM errors)
2. Generated SQL is valid and executes without DB errors
3. Results are formatted properly
"""

import os
import sys
import asyncio
import logging
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from agents.copilot import copilot_query, COPILOT_SHORTCUTS, AHMF_SCHEMA, _execute_sql, SQL_SYSTEM

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def test_schema_loads():
    """Schema should load from db_schema.json without 'priority' column."""
    assert AHMF_SCHEMA, "AHMF_SCHEMA is empty"
    assert "priority" not in AHMF_SCHEMA, "Schema still references non-existent 'priority' column"
    assert "sender" not in AHMF_SCHEMA, "Schema still references non-existent 'sender' column"
    assert "from_user" in AHMF_SCHEMA, "Schema missing 'from_user' column for messages"
    assert "to_user" in AHMF_SCHEMA, "Schema missing 'to_user' column for messages"
    assert "amount_due" in AHMF_SCHEMA, "Schema missing 'amount_due' column for collections"
    assert "amount_received" in AHMF_SCHEMA, "Schema missing 'amount_received' column for collections"
    print("PASS: Schema loads correctly from db_schema.json")


def test_schema_json_valid():
    """db_schema.json should be valid JSON with expected structure."""
    schema_path = os.path.join(os.path.dirname(__file__), "..", "sql", "db_schema.json")
    with open(schema_path) as f:
        schema = json.load(f)
    assert "schema" in schema, "Missing 'schema' key"
    assert schema["schema"] == "ahmf", "Schema name should be 'ahmf'"
    assert "tables" in schema, "Missing 'tables' key"
    required_tables = ["users", "deals", "contacts", "sales_contracts",
                       "collections", "credit_ratings", "transactions", "messages"]
    for t in required_tables:
        assert t in schema["tables"], f"Missing table: {t}"
        assert "columns" in schema["tables"][t], f"Missing columns for table: {t}"
    print(f"PASS: db_schema.json valid with {len(schema['tables'])} tables")


def test_sql_system_prompt():
    """SQL system prompt should include schema and safety rules."""
    assert "ahmf" in SQL_SYSTEM
    assert "SELECT" in SQL_SYSTEM
    assert "Never INSERT" in SQL_SYSTEM or "ONLY generate SELECT" in SQL_SYSTEM
    print("PASS: SQL system prompt includes schema and safety rules")


async def test_shortcut_query(label: str, module_id: str):
    """Test a single copilot shortcut query end-to-end."""
    try:
        result = await copilot_query(label, module_id)
        if "Query error:" in result:
            return False, f"SQL execution error: {result}"
        if "Error generating" in result:
            return False, f"LLM error: {result}"
        if "I can only run SELECT" in result:
            return False, f"Non-SELECT generated: {result}"
        return True, result[:150]
    except Exception as e:
        return False, f"Exception: {str(e)[:150]}"


async def test_all_shortcuts():
    """Test every shortcut across all modules."""
    results = {"passed": 0, "failed": 0, "errors": []}

    for module_id, shortcuts in COPILOT_SHORTCUTS.items():
        for label, desc in shortcuts:
            ok, msg = await test_shortcut_query(label, module_id)
            status = "PASS" if ok else "FAIL"
            print(f"  {status}: [{module_id}] {label}")
            if ok:
                results["passed"] += 1
            else:
                results["failed"] += 1
                results["errors"].append({
                    "module": module_id,
                    "query": label,
                    "error": msg,
                })
            if not ok:
                logger.warning(f"    -> {msg}")

    return results


def main():
    print("=" * 60)
    print("Copilot Text-to-SQL Unit Tests")
    print("=" * 60)

    print("\n--- Schema Tests ---")
    test_schema_loads()
    test_schema_json_valid()
    test_sql_system_prompt()

    print("\n--- Shortcut Query Tests ---")
    results = asyncio.run(test_all_shortcuts())

    print("\n" + "=" * 60)
    total = results["passed"] + results["failed"]
    print(f"Results: {results['passed']}/{total} passed, {results['failed']} failed")

    if results["errors"]:
        print("\nFailed queries:")
        for e in results["errors"]:
            print(f"  [{e['module']}] {e['query']}: {e['error'][:100]}")

    out_path = os.path.join(os.path.dirname(__file__), "..", "test-data", "copilot_test_results.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {out_path}")

    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
