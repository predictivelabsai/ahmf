# AHMF User Stories Questionnaire

**Platform**: Ashland Hill Media Finance — Film Financing Operating System
**Version**: v1.0 (April 2026)
**Purpose**: Validate current features, discover gaps, and prioritize roadmap items with users.

---

## How to Use This Document

Each section maps to an AHMF product module. For every user story:

- **Priority** — Your ranking: Critical / High / Medium / Low / Not Needed
- **Status** — Current state: Built / Partial / Planned / Not Started
- **Your Notes** — Free-form feedback: pain points, missing fields, workflow changes, edge cases

Answer the **Open Questions** at the end of each section to help us understand your real-world workflows.

---

## 1. Deal Pipeline (Film Financing OS)

| # | User Story | Priority | Status | Your Notes |
|---|-----------|----------|--------|------------|
| 1.1 | As a **deal originator**, I want to create a new deal with title, project type, genre, loan amount, interest rate, and term so that I can track it through the pipeline. | | Built | |
| 1.2 | As a **deal originator**, I want to set deal status (pipeline, active, closed, declined) so that I can track deal lifecycle. | | Built | |
| 1.3 | As a **portfolio manager**, I want to see a dashboard with deal counts and total committed capital by status so that I have a real-time portfolio snapshot. | | Built | |
| 1.4 | As a **deal originator**, I want to attach producer, director, and cast summary to a deal so that creative packages are tracked alongside financial terms. | | Built | |
| 1.5 | As a **deal originator**, I want to search and filter deals by title, borrower, status, or genre so that I can quickly find specific deals. | | Built | |
| 1.6 | As a **portfolio manager**, I want to see a deal aging report (days in pipeline, days active) so that I can identify stalled deals. | | Not Started | |
| 1.7 | As a **deal originator**, I want to edit an existing deal's terms (amount, rate, maturity) so that I can reflect renegotiated terms. | | Partial | |
| 1.8 | As a **compliance officer**, I want deal approval workflows (submitted, under review, approved, rejected) so that no deal proceeds without proper sign-off. | | Planned | |
| 1.9 | As a **portfolio manager**, I want to export deal lists to CSV/Excel so that I can share reports with stakeholders. | | Not Started | |
| 1.10 | As a **deal originator**, I want to clone an existing deal as a template for similar transactions so that I save data entry time. | | Not Started | |

### Open Questions — Deal Pipeline

1. What deal statuses do you actually use beyond pipeline/active/closed/declined?
2. What fields are missing from the current deal form that you need for your workflow?
3. How many deals does your team typically manage concurrently?
4. Do you need multi-currency deal amounts (e.g., EUR deal with USD reporting)?
5. What does your current deal approval process look like (number of approvers, stages)?
6. Do you track deal-level P&L (revenue vs. costs) — if so, what line items matter?

---

## 2. Contacts & Relationships

| # | User Story | Priority | Status | Your Notes |
|---|-----------|----------|--------|------------|
| 2.1 | As a **relationship manager**, I want to add contacts with name, company, role, email, phone, and type (distributor, producer, sales agent, investor, legal, talent, crew) so that I have a centralized directory. | | Built | |
| 2.2 | As a **deal originator**, I want to link contacts to deals with a relationship type so that I can see who is involved in each transaction. | | Built | |
| 2.3 | As a **relationship manager**, I want to search contacts by name, company, or type so that I can quickly look up counterparties. | | Built | |
| 2.4 | As a **relationship manager**, I want to see an activity log per contact (deals, interactions, notes) so that I have full relationship history. | | Partial | |
| 2.5 | As a **relationship manager**, I want to import contacts from a CSV so that I can bulk-load my existing CRM data. | | Not Started | |
| 2.6 | As a **deal originator**, I want to see all deals associated with a contact so that I understand the depth of the relationship. | | Partial | |
| 2.7 | As a **relationship manager**, I want to tag contacts with custom labels (e.g., "key account", "new relationship") so that I can segment my network. | | Not Started | |
| 2.8 | As a **compliance officer**, I want to flag contacts requiring KYC/AML refresh so that we stay compliant. | | Not Started | |

### Open Questions — Contacts

1. What CRM or system do you currently use for contact management?
2. Do you need to track organizational hierarchies (parent company, subsidiaries)?
3. What contact types are missing from the current list?
4. How important is deduplication (same person at multiple companies)?
5. Do you track contact sentiment or relationship health scores?

---

## 3. Sales & Collections

| # | User Story | Priority | Status | Your Notes |
|---|-----------|----------|--------|------------|
| 3.1 | As a **sales manager**, I want to create sales contracts per deal, territory, and distributor with MG amounts so that I can track distribution commitments. | | Built | |
| 3.2 | As a **collections analyst**, I want to record collections against contracts (amount due, received, status) so that I can track cash inflows. | | Built | |
| 3.3 | As a **sales manager**, I want to see contracts by territory across 19 markets so that I have a global sales map. | | Built | |
| 3.4 | As a **collections analyst**, I want to flag overdue collections automatically so that I can prioritize follow-ups. | | Built | |
| 3.5 | As a **sales manager**, I want to compare projected vs. actual collections per contract so that I can identify variance early. | | Partial | |
| 3.6 | As a **finance director**, I want a waterfall report showing how collections flow from gross to net (commissions, fees, holdbacks) so that I can model true cash receipts. | | Not Started | |
| 3.7 | As a **sales manager**, I want to attach contract PDFs and delivery schedules to sales contracts so that I have a complete record. | | Not Started | |
| 3.8 | As a **finance director**, I want multi-currency collection tracking with FX conversion to a base currency so that I can report in USD. | | Partial | |
| 3.9 | As a **sales manager**, I want to generate territory-by-territory sales reports for investor updates so that I can share distribution progress. | | Not Started | |

### Open Questions — Sales & Collections

1. How many territories do you typically sell per film?
2. What collection payment terms are standard (30/60/90 days, milestone-based)?
3. Do you need to track holdbacks, reserves, or escrow amounts?
4. What does your waterfall structure look like (commission splits, priority of payments)?
5. How do you currently handle FX risk on international collections?

---

## 4. Credit Rating

| # | User Story | Priority | Status | Your Notes |
|---|-----------|----------|--------|------------|
| 4.1 | As a **risk analyst**, I want AI-generated credit scores (0-100) for distributors and producers so that I can assess counterparty strength. | | Built | |
| 4.2 | As a **risk analyst**, I want risk tier classifications (AAA through CCC) so that I can quickly categorize counterparties. | | Built | |
| 4.3 | As a **risk analyst**, I want to see payment reliability scores and factor breakdowns so that I understand what drives the rating. | | Built | |
| 4.4 | As a **deal originator**, I want to see credit ratings inline when selecting a distributor for a deal so that I make informed decisions. | | Not Started | |
| 4.5 | As a **risk analyst**, I want to override or annotate AI-generated ratings with manual assessments so that I can incorporate offline knowledge. | | Not Started | |
| 4.6 | As a **risk analyst**, I want credit rating history over time per contact so that I can spot trends (improving or deteriorating). | | Partial | |
| 4.7 | As a **portfolio manager**, I want a portfolio-level counterparty concentration report so that I can identify exposure risks. | | Not Started | |

### Open Questions — Credit Rating

1. Do you currently rate counterparties? If so, what methodology (internal scoring, external ratings, references)?
2. What factors matter most when assessing a distributor's creditworthiness?
3. Would you integrate external credit data (D&B, Moody's) or rely on internal scoring?
4. How often do you re-rate a counterparty?
5. Do you set credit limits per counterparty?

---

## 5. Accounting & Transactions

| # | User Story | Priority | Status | Your Notes |
|---|-----------|----------|--------|------------|
| 5.1 | As a **finance analyst**, I want to record disbursements, repayments, fees, and interest by deal so that I maintain a transaction ledger. | | Built | |
| 5.2 | As a **finance analyst**, I want summary metrics (total disbursed, repaid, fees, interest, net position) so that I have a financial overview. | | Built | |
| 5.3 | As a **finance analyst**, I want to search transactions by deal, type, counterparty, or reference so that I can audit specific entries. | | Built | |
| 5.4 | As a **finance director**, I want to reconcile expected vs. actual cash flows by deal so that I can spot discrepancies. | | Not Started | |
| 5.5 | As a **finance director**, I want to generate a P&L statement per deal (revenue, costs, net) so that I can assess deal profitability. | | Not Started | |
| 5.6 | As a **auditor**, I want full audit trail with timestamps, user IDs, and before/after values on all transaction edits so that I can trace changes. | | Partial | |
| 5.7 | As a **finance analyst**, I want to export the transaction ledger to CSV for import into our accounting system so that I avoid double-entry. | | Not Started | |
| 5.8 | As a **finance director**, I want automated interest accrual calculations based on deal terms so that I don't compute manually. | | Not Started | |

### Open Questions — Accounting

1. What accounting system do you use (QuickBooks, Xero, SAP, custom)?
2. Do you need journal entry format (debit/credit) or is a simple ledger sufficient?
3. What reporting periods matter (monthly, quarterly, annual)?
4. Do you accrue interest daily, monthly, or at maturity?
5. Do you need GL account mapping for transactions?

---

## 6. Communications & Tasks

| # | User Story | Priority | Status | Your Notes |
|---|-----------|----------|--------|------------|
| 6.1 | As a **deal originator**, I want to create notes, tasks, and notifications linked to deals so that I track action items. | | Built | |
| 6.2 | As a **team member**, I want to set due dates on tasks and see overdue items flagged so that nothing falls through the cracks. | | Built | |
| 6.3 | As a **team member**, I want to mark tasks as complete with a checkbox so that I track progress. | | Built | |
| 6.4 | As a **manager**, I want to assign tasks to specific team members so that responsibilities are clear. | | Not Started | |
| 6.5 | As a **team member**, I want email or in-app notifications when a task is assigned to me or approaching its deadline so that I stay on top of deadlines. | | Not Started | |
| 6.6 | As a **deal originator**, I want to attach files to messages (e.g., markup PDFs, term sheets) so that communications have full context. | | Not Started | |
| 6.7 | As a **manager**, I want a team task board (kanban or list view) showing all open tasks across deals so that I can manage workload. | | Not Started | |

### Open Questions — Communications

1. Do you use email, Slack, or another tool for deal-related communications today?
2. How many people are typically involved in a deal (internal team)?
3. Do you need recurring tasks (e.g., quarterly compliance checks)?
4. Would you want to send emails directly from the platform or just track internal notes?

---

## 7. Sales Estimates (AI)

| # | User Story | Priority | Status | Your Notes |
|---|-----------|----------|--------|------------|
| 7.1 | As a **sales agent**, I want AI-generated territory-by-territory MG projections based on comparable films so that I can set realistic pricing. | | Built | |
| 7.2 | As a **sales agent**, I want to search TMDB/OMDB for comparable films and see their actual box office and budget data so that I have market benchmarks. | | Built | |
| 7.3 | As a **deal originator**, I want to generate a sales estimate for a new project by providing genre, budget, and cast so that I can evaluate deal viability. | | Built | |
| 7.4 | As a **sales agent**, I want to manually adjust AI-generated estimates per territory so that I can incorporate my market knowledge. | | Not Started | |
| 7.5 | As a **sales agent**, I want to save and version sales estimates so that I can track how projections evolve. | | Partial | |
| 7.6 | As a **investor**, I want to see estimate confidence ranges (low/mid/high) per territory so that I understand the risk band. | | Partial | |
| 7.7 | As a **sales agent**, I want to select specific comp films rather than relying only on AI selection so that I control the benchmarking set. | | Not Started | |

### Open Questions — Sales Estimates

1. How many comp films do you typically use when building a sales estimate?
2. What data sources do you trust for actual sales figures (Gower Street, Comscore, internal)?
3. Do you estimate by territory, by platform (theatrical, SVOD, AVOD), or both?
4. How often do estimates get revised during a deal lifecycle?
5. Do you share estimates with investors or distributors — if so, what format?

---

## 8. Production Risk Scoring (AI)

| # | User Story | Priority | Status | Your Notes |
|---|-----------|----------|--------|------------|
| 8.1 | As a **risk analyst**, I want AI-generated risk scores across 6 dimensions (script complexity, budget feasibility, schedule, jurisdiction, crew/talent, completion) so that I have a structured risk view. | | Built | |
| 8.2 | As a **risk analyst**, I want an overall risk tier (Low, Moderate, Elevated, High) so that I can quickly classify projects. | | Built | |
| 8.3 | As a **risk analyst**, I want AI-suggested mitigations for each risk factor so that I can build a risk management plan. | | Built | |
| 8.4 | As a **risk analyst**, I want to attach a risk assessment to a deal so that underwriting files include the analysis. | | Partial | |
| 8.5 | As a **risk analyst**, I want to weight risk dimensions differently based on deal type (e.g., VFX-heavy vs. indie drama) so that scoring reflects actual risk profile. | | Not Started | |
| 8.6 | As a **portfolio manager**, I want an aggregate risk heatmap across the portfolio so that I can see concentration of high-risk deals. | | Not Started | |
| 8.7 | As a **risk analyst**, I want to compare risk scores across deals side-by-side so that I can benchmark relative risk. | | Not Started | |

### Open Questions — Risk Scoring

1. What risk dimensions are missing from the current six?
2. How do you quantify production risk today (spreadsheet, gut feel, external consultant)?
3. Do you share risk reports with insurers or completion guarantors?
4. What risk score threshold would trigger a deal rejection or additional due diligence?
5. Are there regulatory requirements for risk documentation in your jurisdiction?

---

## 9. Smart Budget (AI)

| # | User Story | Priority | Status | Your Notes |
|---|-----------|----------|--------|------------|
| 9.1 | As a **producer**, I want AI-generated budgets in 3 scenarios (low/mid/high) with line-item breakdowns so that I can evaluate budget ranges. | | Built | |
| 9.2 | As a **producer**, I want budget categories (ATL, BTL-Production, BTL-Post, Insurance, Financing, Contingency) so that I get an industry-standard breakdown. | | Built | |
| 9.3 | As a **producer**, I want to adjust individual line items after generation so that I can refine the AI estimate. | | Not Started | |
| 9.4 | As a **finance director**, I want to compare generated budgets to actual costs as production progresses so that I can track cost overruns. | | Not Started | |
| 9.5 | As a **producer**, I want to import an existing budget (CSV or Movie Magic format) so that I can use the platform for tracking, not just generation. | | Not Started | |
| 9.6 | As a **producer**, I want to export budgets to PDF or Excel so that I can share with financiers. | | Not Started | |

### Open Questions — Smart Budget

1. What budgeting tool do you use today (Movie Magic, Excel, Hot Budget)?
2. What level of line-item detail do you need (top-sheet only, or account-level)?
3. How important is it for AI budgets to follow a specific chart of accounts?
4. Do you track actual vs. budget during production (cost reports)?
5. What contingency percentage is standard for your projects?

---

## 10. Production Scheduling (AI)

| # | User Story | Priority | Status | Your Notes |
|---|-----------|----------|--------|------------|
| 10.1 | As a **line producer**, I want AI-generated day-by-day shooting schedules with location clustering so that I minimize company moves. | | Built | |
| 10.2 | As a **line producer**, I want schedules to include call time, wrap time, scenes, and location per day so that I have a complete stripboard. | | Built | |
| 10.3 | As a **line producer**, I want to manually reorder or adjust schedule days after generation so that I can handle real-world constraints. | | Not Started | |
| 10.4 | As a **AD (assistant director)**, I want to flag weather-dependent or night-shoot days so that I can plan contingencies. | | Not Started | |
| 10.5 | As a **line producer**, I want to link schedule to budget so that daily burn rate is visible so that I can track cost per shoot day. | | Not Started | |
| 10.6 | As a **line producer**, I want to export schedules to PDF or industry formats (Gorilla, StudioBinder) so that I can share with crew. | | Not Started | |

### Open Questions — Production Scheduling

1. What scheduling tool do you use today (Movie Magic, StudioBinder, Gorilla, Excel)?
2. How detailed does the schedule need to be (scenes, setups, cast availability per day)?
3. Do you need to track actor availability / hold days?
4. How often does the schedule change once shooting begins?
5. Who consumes the schedule (director, AD, department heads)?

---

## 11. Soft Funding / Tax Incentives

| # | User Story | Priority | Status | Your Notes |
|---|-----------|----------|--------|------------|
| 11.1 | As a **producer**, I want to search a global database of film tax incentive programs by country and type so that I can identify funding opportunities. | | Built | |
| 11.2 | As a **producer**, I want a rebate calculator (spend x rebate %) so that I can estimate the tax benefit. | | Built | |
| 11.3 | As a **finance director**, I want to link incentive programs to deals so that I can track applied vs. approved amounts. | | Partial | |
| 11.4 | As a **producer**, I want alerts when incentive programs change (new programs, sunset dates, rule changes) so that I don't miss opportunities. | | Not Started | |
| 11.5 | As a **finance director**, I want to stack multiple incentive programs per deal (e.g., federal + state + regional) so that I can maximize soft funding. | | Not Started | |
| 11.6 | As a **producer**, I want to see eligibility requirements (minimum spend, cultural tests, residency) per program so that I can assess qualification. | | Partial | |
| 11.7 | As a **finance director**, I want to model the impact of incentive timing on cash flow (processing days, payment schedule) so that I can plan liquidity. | | Not Started | |

### Open Questions — Soft Funding

1. How many incentive programs do you typically evaluate per project?
2. Do you use consultants or brokers for incentive applications?
3. What countries/regions are most important for your slate?
4. How critical is stacking (combining multiple programs)?
5. Do you need to track application status and deadlines?

---

## 12. Deal Closing & Data Room

| # | User Story | Priority | Status | Your Notes |
|---|-----------|----------|--------|------------|
| 12.1 | As a **deal originator**, I want an auto-generated 20-item closing checklist per deal (Legal, Insurance, Financial, Distribution, Tax, Compliance) so that I have a structured closing process. | | Built | |
| 12.2 | As a **deal originator**, I want to check off items as completed and see a visual progress bar so that I track closing progress. | | Built | |
| 12.3 | As a **deal originator**, I want to upload and version documents per deal so that I have a complete data room. | | Partial | |
| 12.4 | As a **legal counsel**, I want to customize the checklist items per deal (add, remove, reorder) so that it reflects the specific transaction structure. | | Not Started | |
| 12.5 | As a **deal originator**, I want to assign checklist items to specific team members with deadlines so that closing tasks are delegated. | | Not Started | |
| 12.6 | As a **investor**, I want read-only data room access with audit trail (who viewed what, when) so that I can review deal documents securely. | | Not Started | |
| 12.7 | As a **deal originator**, I want automated reminders for incomplete checklist items approaching a deadline so that closing stays on track. | | Not Started | |
| 12.8 | As a **legal counsel**, I want document templates (loan agreement, security agreement, inter-party agreement) so that I can generate first drafts quickly. | | Not Started | |

### Open Questions — Deal Closing

1. What items are missing from the current 20-item checklist?
2. Do you use a virtual data room today (Intralinks, Datasite, Google Drive)?
3. How many parties typically need data room access per deal?
4. Do you need watermarking, download controls, or DRM on documents?
5. How long does a typical deal closing take (weeks, months)?

---

## 13. Audience & Marketing Intelligence (AI)

| # | User Story | Priority | Status | Your Notes |
|---|-----------|----------|--------|------------|
| 13.1 | As a **marketing exec**, I want AI-predicted audience segments (3-5 demographics with age ranges and percentages) so that I can target campaigns. | | Built | |
| 13.2 | As a **marketing exec**, I want a marketing channel plan with estimated spend per channel so that I can build a P&A budget. | | Built | |
| 13.3 | As a **marketing exec**, I want a release strategy (domestic timing, international rollout, platform strategy) so that I can plan distribution. | | Built | |
| 13.4 | As a **marketing exec**, I want to adjust AI-generated audience segments based on test screening data so that I refine targeting. | | Not Started | |
| 13.5 | As a **marketing exec**, I want to benchmark P&A spend against comparable films so that I can justify the budget. | | Not Started | |
| 13.6 | As a **sales agent**, I want to include audience analysis in territory sales packages so that distributors see the marketing support plan. | | Not Started | |

### Open Questions — Audience Intelligence

1. Do you currently use audience research tools (NRG, Screen Engine, PostTrak)?
2. At what stage do you typically start marketing planning (development, pre-production, post)?
3. What P&A-to-production-budget ratio is standard for your films?
4. Do you need social media analytics integration (Instagram, TikTok, X/Twitter)?
5. How do you measure marketing effectiveness (tracking studies, social engagement, ticket pre-sales)?

---

## 14. Talent Intelligence (AI)

| # | User Story | Priority | Status | Your Notes |
|---|-----------|----------|--------|------------|
| 14.1 | As a **casting director**, I want to search actors and directors by name with popularity scores and known-for credits so that I can evaluate talent. | | Built | |
| 14.2 | As a **producer**, I want AI-recommended cast with heat scores, genre fit, salary tier, and international sales impact so that I can optimize the package. | | Built | |
| 14.3 | As a **producer**, I want package simulations (2-3 cast combinations with projected domestic/international returns) so that I can model different packages. | | Built | |
| 14.4 | As a **sales agent**, I want to see which actors drive value in specific territories so that I can tailor sales pitches. | | Partial | |
| 14.5 | As a **producer**, I want to track actor availability and scheduling conflicts so that I can plan casting around real constraints. | | Not Started | |
| 14.6 | As a **producer**, I want to link talent recommendations to deals so that cast-finance analysis is connected. | | Not Started | |
| 14.7 | As a **sales agent**, I want to compare talent value by territory (e.g., Actor A strong in Asia vs. Actor B strong in Europe) so that I can optimize the global package. | | Not Started | |

### Open Questions — Talent Intelligence

1. What talent databases do you use today (IMDB Pro, agency submissions, internal)?
2. How do you currently assess an actor's "bankability" or sales value?
3. Do you need to track talent relationships (agent, manager, lawyer, publicist)?
4. How important is social media following as a talent valuation metric?
5. Do you package talent before or after securing financing?

---

## 15. Platform & UX (Cross-Cutting)

| # | User Story | Priority | Status | Your Notes |
|---|-----------|----------|--------|------------|
| 15.1 | As a **user**, I want to register and log in with email and password so that my data is secure and isolated. | | Built | |
| 15.2 | As a **user**, I want a 3-pane layout (navigation, content, inspector) so that I can work efficiently without page reloads. | | Built | |
| 15.3 | As a **user**, I want to chat with an AI assistant that can access all platform tools so that I can work conversationally. | | Built | |
| 15.4 | As a **user**, I want structured chat commands (deal:list, portfolio, help) for quick access so that I can work faster than clicking through menus. | | Built | |
| 15.5 | As a **user**, I want chat history preserved across sessions so that I can resume previous conversations. | | Built | |
| 15.6 | As a **admin**, I want role-based access control (admin, analyst, viewer) so that I can restrict sensitive data. | | Not Started | |
| 15.7 | As a **user**, I want SSO login (Google, Microsoft) so that I don't manage another password. | | Not Started | |
| 15.8 | As a **user**, I want the platform to work on mobile/tablet so that I can check deals on the go. | | Partial | |
| 15.9 | As a **admin**, I want an audit log of all user actions (logins, edits, views) so that I have a compliance trail. | | Partial | |
| 15.10 | As a **user**, I want to customize my dashboard with widgets (deal pipeline, overdue tasks, portfolio snapshot) so that I see what matters most. | | Not Started | |
| 15.11 | As a **user**, I want dark mode so that I can work comfortably in low-light environments. | | Not Started | |
| 15.12 | As a **team lead**, I want multi-user collaboration on the same deal (shared notes, live status) so that the team stays aligned. | | Not Started | |

### Open Questions — Platform & UX

1. How many users would typically access the platform per organization?
2. What user roles exist in your team (originator, analyst, legal, admin)?
3. What devices/browsers do you primarily use?
4. Do you need offline access or is always-online acceptable?
5. What integrations matter most (email, Slack, accounting software, cloud storage)?
6. How important is white-labeling (custom branding for your firm)?

---

## 16. Reporting & Analytics (Cross-Cutting)

| # | User Story | Priority | Status | Your Notes |
|---|-----------|----------|--------|------------|
| 16.1 | As a **portfolio manager**, I want a portfolio dashboard with charts (deal volume over time, status distribution, capital deployed) so that I can present to stakeholders. | | Not Started | |
| 16.2 | As a **finance director**, I want to generate quarterly investor reports (deal summaries, collections, P&L) so that I meet reporting obligations. | | Not Started | |
| 16.3 | As a **analyst**, I want to build custom reports by selecting fields, filters, and groupings so that I can answer ad hoc questions. | | Not Started | |
| 16.4 | As a **portfolio manager**, I want scheduled report delivery (email PDF weekly/monthly) so that stakeholders get updates without logging in. | | Not Started | |
| 16.5 | As a **analyst**, I want data export to CSV/Excel across all modules so that I can do deeper analysis externally. | | Not Started | |

### Open Questions — Reporting

1. What reports do you produce today and how often?
2. Who are the primary report consumers (board, investors, internal team)?
3. What format do stakeholders prefer (PDF, Excel, online dashboard)?
4. Do you need comparison across time periods (QoQ, YoY)?
5. What KPIs matter most for your business?

---

## Summary

| Module | Stories | Built | Partial | Not Started |
|--------|---------|-------|---------|-------------|
| Deal Pipeline | 10 | 5 | 1 | 4 |
| Contacts | 8 | 3 | 1 | 4 |
| Sales & Collections | 9 | 4 | 1 | 4 |
| Credit Rating | 7 | 3 | 1 | 3 |
| Accounting | 8 | 3 | 1 | 4 |
| Communications | 7 | 3 | 0 | 4 |
| Sales Estimates | 7 | 3 | 2 | 2 |
| Risk Scoring | 7 | 3 | 1 | 3 |
| Smart Budget | 6 | 2 | 0 | 4 |
| Scheduling | 6 | 2 | 0 | 4 |
| Soft Funding | 7 | 2 | 2 | 3 |
| Data Room | 8 | 2 | 1 | 5 |
| Audience Intel | 6 | 3 | 0 | 3 |
| Talent Intel | 7 | 3 | 1 | 3 |
| Platform & UX | 12 | 5 | 2 | 5 |
| Reporting | 5 | 0 | 0 | 5 |
| **Total** | **120** | **46** | **14** | **60** |

---

**Next Steps**: Please review each section and fill in Priority and Your Notes columns. Return to the AHMF team for roadmap prioritization.
