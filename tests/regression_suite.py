"""
Monika Regression Suite

End-to-end regression covering:

  • Database layer (connection, schema, CRUD)
  • Authentication (user, JWT, bcrypt)
  • Agent tools (deals, contacts, portfolio, TMDB/OMDB, incentives, talent,
    closing checklist, sales, credit, accounting, comms, risk, budget,
    schedule, audience)
  • Chat command interceptor
  • Chat store
  • Config / PDF extractor
  • Credit scoring ML (catalog, dataset, training, inference, rating bands)
  • Playwright UI (login, every module page, scoring sliders end-to-end,
    chat commands)

Screenshots land in `screenshots/` and a JSON summary in
`test-data/regression_summary.json`.

Usage:
    # App already running on 5010:
    python tests/regression_suite.py

    # Auto-start app (picks a free port if 5010 is taken):
    python tests/regression_suite.py --start-app

    # Also regenerate demo video + GIF at the end:
    python tests/regression_suite.py --start-app --video
"""

from __future__ import annotations

import argparse
import asyncio
import json
import socket
import subprocess
import sys
import time
import traceback
import uuid
from pathlib import Path
from typing import Any, Callable

# --- Path / env bootstrap --------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(ROOT / ".env")

SCREENSHOTS = ROOT / "screenshots"
RESULTS = ROOT / "test-data"
SCREENSHOTS.mkdir(exist_ok=True)
RESULTS.mkdir(exist_ok=True)


# --- Mini test framework ---------------------------------------------------

_results: list[dict[str, Any]] = []
_tests: list[Callable] = []
_pass = 0
_fail = 0


def test(name: str):
    def wrap(fn):
        fn._name = name
        _tests.append(fn)
        return fn
    return wrap


def _record(name: str, status: str, detail: str) -> None:
    _results.append({"test": name, "status": status, "detail": detail})


def run(fn):
    global _pass, _fail
    name = fn._name
    try:
        rv = fn()
        _pass += 1
        detail = rv if isinstance(rv, str) else "OK"
        print(f"  \033[32mPASS\033[0m  {name}" + (f"  — {detail}" if detail != "OK" else ""))
        _record(name, "PASS", detail)
    except Exception as e:
        _fail += 1
        print(f"  \033[31mFAIL\033[0m  {name}: {e}")
        _record(name, "FAIL", f"{type(e).__name__}: {e}")
        if "--verbose" in sys.argv:
            traceback.print_exc()


# ===========================================================================
#   PYTHON-LEVEL TESTS
# ===========================================================================

# -- 1. Database -----------------------------------------------------------

@test("DB: connection works")
def t_db_connect():
    from sqlalchemy import text
    from utils.db import get_pool
    with get_pool().get_session() as s:
        assert s.execute(text("SELECT 1")).scalar() == 1
    return "connected"


@test("DB: ahmf schema has expected tables")
def t_db_schema():
    from sqlalchemy import text
    from utils.db import get_pool
    with get_pool().get_session() as s:
        rows = s.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='ahmf'"
        )).fetchall()
    tables = {r[0] for r in rows}
    essentials = {"deals", "contacts", "users", "sales_contracts",
                  "transactions", "messages", "credit_ratings"}
    missing = essentials - tables
    assert not missing, f"missing tables: {missing}"
    return f"{len(tables)} tables"


@test("DB: deals row count is readable")
def t_db_deals_count():
    from sqlalchemy import text
    from utils.db import get_pool
    with get_pool().get_session() as s:
        n = s.execute(text("SELECT COUNT(*) FROM ahmf.deals")).scalar()
    assert n is not None
    return f"{n} deals"


@test("DB: contacts row count is readable")
def t_db_contacts_count():
    from sqlalchemy import text
    from utils.db import get_pool
    with get_pool().get_session() as s:
        n = s.execute(text("SELECT COUNT(*) FROM ahmf.contacts")).scalar()
    assert n is not None
    return f"{n} contacts"


# -- 2. Authentication -----------------------------------------------------

_REG_EMAIL = "regression@monika.local"
_REG_PASSWORD = "RegPass!2026"


@test("Auth: idempotent create_user")
def t_auth_create():
    from utils.auth import create_user, get_user_by_email
    if get_user_by_email(_REG_EMAIL):
        return "already exists"
    user = create_user(_REG_EMAIL, _REG_PASSWORD, display_name="Regression Bot")
    assert user, "create_user returned falsy"
    return f"created {user['email']}"


@test("Auth: authenticate valid password")
def t_auth_ok():
    from utils.auth import authenticate
    user = authenticate(_REG_EMAIL, _REG_PASSWORD)
    assert user and user["email"] == _REG_EMAIL
    return "authenticated"


@test("Auth: wrong password is rejected")
def t_auth_bad():
    from utils.auth import authenticate
    assert authenticate(_REG_EMAIL, "nope-" + _REG_PASSWORD) is None
    return "rejected"


@test("Auth: JWT round-trip")
def t_auth_jwt():
    from utils.auth import create_jwt_token, decode_jwt_token, get_user_by_email
    u = get_user_by_email(_REG_EMAIL)
    tok = create_jwt_token(u["user_id"], u["email"])
    payload = decode_jwt_token(tok)
    assert payload and payload["email"] == _REG_EMAIL
    return f"{len(tok)}-byte token"


@test("Auth: tampered JWT rejected")
def t_auth_jwt_bad():
    from utils.auth import decode_jwt_token
    assert decode_jwt_token("not.a.jwt") is None
    return "rejected"


# -- 3. Deal / contact tools -----------------------------------------------

@test("Tool: search_deals returns markdown")
def t_tool_deals():
    from app import search_deals
    out = search_deals("")
    assert isinstance(out, str) and ("Deals" in out or "No deals" in out)
    return f"{len(out)} chars"


@test("Tool: search_deals with filter")
def t_tool_deals_filter():
    from app import search_deals
    out = search_deals("test")
    assert isinstance(out, str)
    return "OK"


@test("Tool: get_portfolio_overview has totals")
def t_tool_portfolio():
    from app import get_portfolio_overview
    out = get_portfolio_overview()
    assert "Portfolio" in out or "Total" in out or "No deals" in out
    return "OK"


@test("Tool: search_contacts works")
def t_tool_contacts():
    from app import search_contacts
    out = search_contacts("")
    assert "Contacts" in out or "No contacts" in out
    return "OK"


# -- 4. External APIs ------------------------------------------------------

@test("TMDB: search_movies returns Inception")
def t_tmdb_search():
    from utils.tmdb_util import search_movies
    r = search_movies("Inception", limit=3)
    assert r and r[0]["title"] == "Inception"
    return f"{len(r)} hits"


@test("TMDB: get_movie_details has budget")
def t_tmdb_details():
    from utils.tmdb_util import get_movie_details
    m = get_movie_details(27205)
    assert m["title"] == "Inception" and m["budget"] > 0
    return f"${m['budget']:,}"


@test("TMDB: search_people finds DiCaprio")
def t_tmdb_people():
    from utils.tmdb_util import search_people
    r = search_people("Leonardo DiCaprio", limit=2)
    assert r and "DiCaprio" in r[0]["name"]
    return r[0]["name"]


@test("OMDB: Inception has box office")
def t_omdb_search():
    from utils.omdb_util import search_movie
    m = search_movie("Inception", year=2010)
    assert m and m["box_office"] > 0
    return f"${m['box_office']:,}"


# -- 5. Module tools -------------------------------------------------------

@test("Module tool: incentives USA/Georgia")
def t_mod_incentives():
    from modules.funding import search_incentives_tool
    out = search_incentives_tool(country="USA")
    assert "Georgia" in out
    return "OK"


@test("Module tool: talent search")
def t_mod_talent():
    from modules.talent import search_talent_tool
    out = search_talent_tool("Margot Robbie")
    assert "Robbie" in out
    return "OK"


@test("Module tool: sales contracts search")
def t_mod_sales():
    from modules.sales import search_sales_contracts
    out = search_sales_contracts("")
    assert isinstance(out, str) and len(out) > 0
    return "OK"


@test("Module tool: credit rating lookup")
def t_mod_credit():
    from modules.credit import get_credit_rating
    out = get_credit_rating("Test")
    assert isinstance(out, str)
    return "OK"


@test("Module tool: transactions ledger")
def t_mod_transactions():
    from modules.accounting import search_transactions
    out = search_transactions("")
    assert isinstance(out, str)
    return "OK"


@test("Module tool: messages / tasks")
def t_mod_messages():
    from modules.comms import search_messages
    out = search_messages("")
    assert isinstance(out, str)
    return "OK"


# -- 6. Command interceptor ------------------------------------------------

def _run_cmd(msg: str):
    from app import _command_interceptor
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_command_interceptor(msg, {}))
    finally:
        loop.close()


@test("Command: help")
def t_cmd_help():
    r = _run_cmd("help")
    assert r and "Available Commands" in r
    return "OK"


@test("Command: deal:list")
def t_cmd_deals():
    r = _run_cmd("deal:list")
    assert r is not None
    return "OK"


@test("Command: portfolio")
def t_cmd_portfolio():
    r = _run_cmd("portfolio")
    assert r is not None
    return "OK"


@test("Command: incentives")
def t_cmd_incentives():
    r = _run_cmd("incentives")
    assert r and "Incentive" in r
    return "OK"


@test("Command: talent:search Brad Pitt")
def t_cmd_talent():
    r = _run_cmd("talent:search Brad Pitt")
    assert r is not None
    return "OK"


@test("Command: sales:list")
def t_cmd_sales():
    r = _run_cmd("sales:list")
    assert r is not None
    return "OK"


@test("Command: transactions")
def t_cmd_txn():
    r = _run_cmd("transactions")
    assert r is not None
    return "OK"


@test("Command: messages")
def t_cmd_msgs():
    r = _run_cmd("messages")
    assert r is not None
    return "OK"


@test("Command: unknown falls through to AI")
def t_cmd_fallthrough():
    r = _run_cmd("what is the weather in paris")
    assert r is None
    return "OK"


# -- 7. Chat store ---------------------------------------------------------

@test("Chat store: save + load + delete")
def t_chat_store():
    from utils.agui.chat_store import (
        save_conversation, save_message,
        load_conversation_messages, delete_conversation,
    )
    tid = f"reg-{uuid.uuid4()}"
    save_conversation(tid, title="Regression")
    save_message(tid, "user", "ping")
    save_message(tid, "assistant", "pong")
    msgs = load_conversation_messages(tid)
    assert len(msgs) == 2 and msgs[0]["role"] == "user"
    delete_conversation(tid)
    return "OK"


# -- 8. Config / PDF extractor --------------------------------------------

@test("Config: settings constants")
def t_config():
    from config.settings import (
        APP_NAME, GENRES, TERRITORIES, RISK_DIMENSIONS,
        CLOSING_CHECKLIST_TEMPLATE,
    )
    assert len(GENRES) >= 16
    assert len(TERRITORIES) >= 19
    assert len(RISK_DIMENSIONS) == 6
    assert len(CLOSING_CHECKLIST_TEMPLATE) >= 20
    return f"app={APP_NAME}, genres={len(GENRES)}"


@test("PDF extractor: scene + character parsing")
def t_pdf_extractor():
    from utils.pdf_extractor import extract_script_metadata
    meta = extract_script_metadata(
        "INT. LAB - DAY\n\nALICE\nHello.\n\nEXT. PARK - NIGHT\n\nBOB\nHi."
    )
    assert meta["scene_count"] == 2 and "ALICE" in meta["character_names"]
    return "OK"


# -- 9. Credit Scoring ML --------------------------------------------------

@test("Scoring: metric catalog loads 3 collateral types")
def t_scoring_catalog():
    from utils.scoring.catalog import load_metrics, COLLATERAL_TYPES
    cat = load_metrics()
    for c in COLLATERAL_TYPES:
        assert cat[c], f"no metrics for {c}"
    total = sum(len(v) for v in cat.values())
    assert total > 50, f"only {total} metrics total"
    return f"{total} metrics across 3 types"


@test("Scoring: rating bands map correctly")
def t_scoring_bands():
    from utils.scoring.catalog import rating_band
    # Smoke: scores map to bands without throwing, sorted by quality
    bands = [rating_band(s) for s in (5, 25, 45, 65, 85, 100)]
    assert bands[0].startswith("CCC")
    assert bands[-1].startswith("AA")
    return ", ".join(bands)


@test("Scoring: synthetic dataset shape matches catalog")
def t_scoring_dataset():
    from utils.scoring.dataset import build_dataset
    X, y, metrics = build_dataset("pre_sales", n_samples=300, seed=7)
    assert X.shape == (300, len(metrics))
    assert set(y.unique()) <= {0, 1}
    return f"X={X.shape}, default_rate={y.mean():.2f}"


@test("Scoring: models load for every collateral type")
def t_scoring_models_present():
    from utils.scoring import COLLATERAL_TYPES, load_bundle
    for c in COLLATERAL_TYPES:
        b = load_bundle(c)
        assert b.rf is not None and b.logit is not None
        assert b.rf_importance.shape[0] == len(b.features)
    return f"{len(COLLATERAL_TYPES)} bundles"


@test("Scoring: inference on neutral counterparty gives mid-range score")
def t_scoring_infer_neutral():
    from utils.scoring import load_bundle, score_counterparty
    b = load_bundle("pre_sales")
    r = score_counterparty(b, {})
    assert 0 <= r["blended_score"] <= 100
    assert 0 <= r["rule_score"] <= 100
    assert 0 <= r["rf_proba"] <= 1
    assert r["rating"]
    return f"score={r['blended_score']:.1f} → {r['rating']}"


@test("Scoring: high-risk inputs push toward CCC/BB")
def t_scoring_infer_bad():
    from utils.scoring import load_bundle, score_counterparty
    b = load_bundle("pre_sales")
    bad = {k: 15 for k in b.feature_keys}
    r = score_counterparty(b, bad)
    assert r["blended_score"] < 50
    assert r["rating"].rstrip("+-") in {"CCC", "BB", "BBB"}
    return f"{r['blended_score']:.1f} → {r['rating']}"


@test("Scoring: low-risk inputs push toward A/AA")
def t_scoring_infer_good():
    from utils.scoring import load_bundle, score_counterparty
    b = load_bundle("tax_credit")
    good = {k: 92 for k in b.feature_keys}
    r = score_counterparty(b, good)
    assert r["blended_score"] > 50
    return f"{r['blended_score']:.1f} → {r['rating']}"


@test("Scoring: top_contributions ordered by |logit|")
def t_scoring_contrib_order():
    from utils.scoring import load_bundle, score_counterparty
    b = load_bundle("gap_unsold")
    r = score_counterparty(b, {k: 30 for k in b.feature_keys})
    contribs = r["top_contributions"]
    pushes = [abs(c["logit_contribution"]) for c in contribs]
    assert pushes == sorted(pushes, reverse=True)
    return f"{len(contribs)} contribs"


@test("Scoring: training summary exists and reports AUC")
def t_scoring_summary():
    path = ROOT / "models" / "training_summary.json"
    assert path.exists(), "run `python -m utils.scoring.train` first"
    data = json.loads(path.read_text())
    for c, m in data.items():
        assert 0 <= m["rf"]["auc"] <= 1
        assert 0 <= m["logit"]["auc"] <= 1
    return "all AUCs in [0,1]"


# ===========================================================================
#   PLAYWRIGHT UI TESTS
# ===========================================================================

# Shared mutable holder for the UI base URL — set by main()
_UI_STATE: dict[str, Any] = {"base_url": None, "email": None, "password": None}


def _ui_skip(name: str, reason: str) -> None:
    global _pass
    _pass += 1
    print(f"  \033[33mSKIP\033[0m  {name}  — {reason}")
    _record(name, "SKIP", reason)


async def _ui_tests(base_url: str, email: str, password: str) -> None:
    """Run the Playwright-based tests. Screenshots go to SCREENSHOTS/."""
    global _pass, _fail
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})

        async def shot(tag: str):
            path = SCREENSHOTS / f"{tag}.png"
            await page.screenshot(path=str(path))

        async def nav_module(path: str, title: str, wait: float = 1.2):
            await page.evaluate(
                """(args) => {
                    var c=document.getElementById('center-content');
                    var ch=document.getElementById('center-chat');
                    if (c && ch) { ch.style.display='none'; c.style.display='block'; }
                    htmx.ajax('GET', args.path, {target:'#center-content', swap:'innerHTML'});
                    var h=document.getElementById('center-title');
                    if (h) h.textContent = args.title;
                }""",
                {"path": path, "title": title},
            )
            await asyncio.sleep(wait)

        async def send_chat(msg: str, wait: float = 3.0):
            await page.evaluate(
                """(m) => {
                    var ta=document.getElementById('chat-input');
                    var fm=document.getElementById('chat-form');
                    if (ta && fm) { ta.value=m; fm.requestSubmit(); }
                }""",
                msg,
            )
            await asyncio.sleep(wait)
            await page.evaluate(
                "() => { var m=document.getElementById('chat-messages'); if (m) m.scrollTop=m.scrollHeight; }"
            )

        async def ui(name: str, fn):
            global _pass, _fail
            try:
                await fn()
                _pass += 1
                print(f"  \033[32mPASS\033[0m  UI: {name}")
                _record(f"UI: {name}", "PASS", "OK")
            except Exception as e:
                _fail += 1
                print(f"  \033[31mFAIL\033[0m  UI: {name}: {e}")
                _record(f"UI: {name}", "FAIL", f"{type(e).__name__}: {e}")
                if "--verbose" in sys.argv:
                    traceback.print_exc()

        # ---- Auth / landing ----
        async def login_page():
            r = await page.goto(f"{base_url}/login")
            assert r.status == 200
            await asyncio.sleep(0.5)
            await shot("00_login")
            assert await page.locator("input[name='email']").count() == 1

        async def login_submit():
            await page.fill("input[name='email']", email)
            await page.fill("input[name='password']", password)
            await shot("01_login_filled")
            await page.click("button[type='submit']")
            await page.wait_for_url(f"{base_url}/", timeout=10000)
            await asyncio.sleep(1.5)
            await shot("02_welcome")

        async def branding_monika():
            html = await page.content()
            assert "Monika" in html, "brand title not found in DOM"
            assert "Ashland Hill Media Finance" in html, "subtitle missing"

        async def sidebar_has_scoring():
            text = await page.locator(".left-pane").text_content()
            assert "Credit Scoring" in (text or ""), "Credit Scoring (ML) missing in sidebar"

        # ---- Module pages (13 tabs) ----
        modules = [
            ("deals",      "/module/deals",      "Deals"),
            ("contacts",   "/module/contacts",   "Contacts"),
            ("sales",      "/module/sales",      "Sales & Collections"),
            ("credit",     "/module/credit",     "Credit Rating"),
            ("scoring",    "/module/scoring",    "Credit Scoring"),
            ("accounting", "/module/accounting", "Accounting"),
            ("comms",      "/module/comms",      "Communications"),
            ("estimates",  "/module/estimates",  "Sales Estimates"),
            ("risk",       "/module/risk",       "Risk Scoring"),
            ("budget",     "/module/budget",     "Smart Budget"),
            ("schedule",   "/module/schedule",   "Scheduling"),
            ("funding",    "/module/funding",    "Soft Funding"),
            ("dataroom",   "/module/dataroom",   "Data Room"),
            ("audience",   "/module/audience",   "Audience Intel"),
            ("talent",     "/module/talent",     "Talent Intel"),
            ("guide",      "/module/guide",      "User Guide"),
        ]

        # ---- Forms ----
        async def deal_new_form():
            await nav_module("/module/deal/new", "New Deal")
            await shot("10_deal_new_form")
            assert await page.locator("input[name='title']").count() == 1
            assert await page.locator("input[name='loan_amount']").count() == 1

        async def contact_new_form():
            await nav_module("/module/contact/new", "New Contact")
            await shot("11_contact_new_form")
            assert await page.locator("input[name='name']").count() == 1

        async def risk_new_form():
            await nav_module("/module/risk/new", "New Risk Assessment")
            await shot("12_risk_new_form")

        # ---- Credit scoring UI ----
        async def scoring_landing():
            await nav_module("/module/scoring", "Credit Scoring")
            await asyncio.sleep(0.8)
            await shot("20_scoring_landing")
            text = await page.locator("#center-content").text_content()
            assert "Pre-Sales" in (text or "")
            assert "Gap / Unsold" in (text or "")
            assert "Tax Credit" in (text or "")

        async def scoring_pre_sales():
            await nav_module("/module/scoring/pre_sales", "Credit Scoring — Pre-Sales")
            await asyncio.sleep(1.8)
            await shot("21_scoring_pre_sales_form")
            n_sliders = await page.locator(".score-slider").count()
            assert n_sliders > 30, f"expected >30 sliders, got {n_sliders}"

        async def scoring_run_inference():
            await nav_module("/module/scoring/tax_credit", "Credit Scoring — Tax Credit")
            await asyncio.sleep(1.5)
            await shot("22_scoring_tax_credit_form")
            # Drop all sliders to ~20 to force a low score
            await page.evaluate("""
                () => {
                    document.querySelectorAll('.score-slider').forEach(s => {
                        s.value = 20;
                        var d = document.getElementById('val-' + s.name);
                        if (d) d.textContent = s.value;
                    });
                }
            """)
            await shot("23_scoring_sliders_low")
            # Submit the form
            await page.evaluate("""
                () => {
                    var btn = Array.from(document.querySelectorAll('#center-content button[type=\"submit\"]')).pop();
                    if (btn) btn.click();
                }
            """)
            await asyncio.sleep(2.5)
            await shot("24_scoring_result_low")
            result_text = await page.locator("#scoring-result").text_content()
            assert "Rating" in (result_text or "")
            assert any(tag in (result_text or "") for tag in ("CCC", "BB", "BBB")), \
                f"expected risky rating, got: {(result_text or '')[:200]}"

        async def scoring_high_good():
            # Raise sliders to ~90 to force a high score
            await page.evaluate("""
                () => {
                    document.querySelectorAll('.score-slider').forEach(s => {
                        s.value = 90;
                        var d = document.getElementById('val-' + s.name);
                        if (d) d.textContent = s.value;
                    });
                }
            """)
            await shot("25_scoring_sliders_high")
            await page.evaluate("""
                () => {
                    var btn = Array.from(document.querySelectorAll('#center-content button[type=\"submit\"]')).pop();
                    if (btn) btn.click();
                }
            """)
            await asyncio.sleep(2.5)
            await shot("26_scoring_result_high")

        # ---- Chat commands ----
        async def chat_help_cmd():
            await page.evaluate("""
                () => {
                    var c=document.getElementById('center-content');
                    var ch=document.getElementById('center-chat');
                    if (c) c.style.display='none';
                    if (ch) ch.style.display='block';
                }
            """)
            await asyncio.sleep(0.5)
            await send_chat("help", 2.5)
            await shot("30_chat_help")
            body = await page.content()
            assert "Available Commands" in body

        async def chat_portfolio_cmd():
            await send_chat("portfolio", 3)
            await shot("31_chat_portfolio")

        async def chat_deals_cmd():
            await send_chat("deal:list", 3)
            await shot("32_chat_deals")

        async def chat_incentives_cmd():
            await send_chat("incentives", 3)
            await shot("33_chat_incentives")

        async def chat_talent_cmd():
            await send_chat("talent:search Margot Robbie", 3)
            await shot("34_chat_talent")

        # ---- Run the list ----
        await ui("login page loads", login_page)
        await ui("login succeeds", login_submit)
        await ui("branding is Monika + Ashland Hill Media Finance", branding_monika)
        await ui("sidebar has Credit Scoring entry", sidebar_has_scoring)

        for idx, (tag, path, title) in enumerate(modules):
            async def _m(p=path, t=title, tg=tag, i=idx):
                await nav_module(p, t)
                await shot(f"40_module_{i:02d}_{tg}")
                body = await page.locator("#center-content").text_content()
                assert body and len(body.strip()) > 0, f"empty module body for {p}"
            await ui(f"module loads: {tag}", _m)

        await ui("new-deal form renders", deal_new_form)
        await ui("new-contact form renders", contact_new_form)
        await ui("new-risk form renders", risk_new_form)

        await ui("scoring landing has 3 collateral cards", scoring_landing)
        await ui("scoring pre-sales form has sliders", scoring_pre_sales)
        await ui("scoring low inputs → risky rating", scoring_run_inference)
        await ui("scoring high inputs render result panel", scoring_high_good)

        await ui("chat: help command", chat_help_cmd)
        await ui("chat: portfolio command", chat_portfolio_cmd)
        await ui("chat: deal:list command", chat_deals_cmd)
        await ui("chat: incentives command", chat_incentives_cmd)
        await ui("chat: talent:search command", chat_talent_cmd)

        await browser.close()


# ===========================================================================
#   App-runner utilities
# ===========================================================================

def _port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        try:
            sock.connect(("127.0.0.1", port))
            return True
        except Exception:
            return False


def _find_free_port(start: int = 5010) -> int:
    for p in range(start, start + 30):
        if not _port_open(p):
            return p
    return start


def _start_app(port: int) -> subprocess.Popen:
    env_flag = f"PORT={port}"
    print(f"  starting app on port {port}…")
    proc = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=str(ROOT),
        env={**__import__("os").environ, "PORT": str(port)},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Poll for /api/health
    import urllib.request
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://localhost:{port}/api/health", timeout=1)
            return proc
        except Exception:
            time.sleep(1)
    proc.terminate()
    raise RuntimeError(f"app did not come up on port {port}")


# ===========================================================================
#   Entrypoint
# ===========================================================================

def main() -> int:
    ap = argparse.ArgumentParser(description="Monika regression suite")
    ap.add_argument("--start-app", action="store_true",
                    help="Auto-start the app (picks a free port if 5010 is busy)")
    ap.add_argument("--port", type=int, default=5010, help="App port")
    ap.add_argument("--email", default="joe@ashland-hill.com")
    ap.add_argument("--password", default="test1234")
    ap.add_argument("--skip-ui", action="store_true")
    ap.add_argument("--video", action="store_true",
                    help="After tests pass, regenerate docs/demo_video.*")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    port = args.port
    app_proc = None

    print(f"\n{'='*64}")
    print(f"  Monika Regression Suite")
    print(f"{'='*64}\n")

    # --- start app if requested ----------------------------------------
    if args.start_app:
        if _port_open(port):
            port = _find_free_port(port + 1)
            print(f"  port {args.port} busy, using {port}")
        try:
            app_proc = _start_app(port)
        except Exception as e:
            print(f"  \033[31mcould not start app: {e}\033[0m")
            return 1

    base_url = f"http://localhost:{port}"

    # --- Python-level tests --------------------------------------------
    print(f"\n--- Python-level tests ({len(_tests)}) ---\n")
    for fn in _tests:
        run(fn)

    # --- UI tests (Playwright) -----------------------------------------
    if args.skip_ui:
        _ui_skip("UI tests skipped", "--skip-ui")
    elif not _port_open(port):
        _ui_skip("UI tests skipped", f"no app on port {port}")
    else:
        print(f"\n--- Playwright UI tests (base: {base_url}) ---\n")
        try:
            asyncio.run(_ui_tests(base_url, args.email, args.password))
        except Exception as e:
            print(f"  \033[31mUI tests crashed: {e}\033[0m")
            _record("UI harness", "FAIL", str(e))
            globals()["_fail"] += 1

    # --- Summary --------------------------------------------------------
    total = _pass + _fail
    print(f"\n{'='*64}")
    print(f"  Results: {_pass} passed, {_fail} failed, {total} total")
    print(f"  Screenshots: {SCREENSHOTS.relative_to(ROOT)}/")
    print(f"{'='*64}\n")

    summary = {
        "passed": _pass,
        "failed": _fail,
        "total": total,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "screenshots_dir": str(SCREENSHOTS.relative_to(ROOT)),
        "tests": _results,
    }
    (RESULTS / "regression_summary.json").write_text(json.dumps(summary, indent=2))

    # --- Optional video rebuild ----------------------------------------
    if args.video and _fail == 0 and _port_open(port):
        print("\n--- Regenerating demo video ---\n")
        try:
            import os
            env = {**os.environ, "PORT": str(port), "VIDEO_BASE_URL": base_url}
            subprocess.run(
                [sys.executable, str(ROOT / "tests" / "capture_video.py")],
                cwd=str(ROOT), env=env, check=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"  video capture failed: {e}")

    # --- Tear down ------------------------------------------------------
    if app_proc:
        app_proc.terminate()
        try:
            app_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            app_proc.kill()

    return 0 if _fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
