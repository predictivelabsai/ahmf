# AHMF Architecture

## System Overview

```mermaid
graph TB
    subgraph Browser["Browser (Client)"]
        UI_3P["3-Pane Layout"]
        HTMX["HTMX Engine"]
        WS["WebSocket"]
        Marked["marked.js (Markdown)"]
        Plotly["Plotly.js (Charts)"]
    end

    subgraph FastHTML["FastHTML Server (app.py)"]
        Routes["Route Handler"]
        Auth["Auth Middleware"]
        AGUI["AGUI Engine"]
        CMD["Command Interceptor"]
        Modules["Module Routes (12)"]
    end

    subgraph AI["AI Layer"]
        LG["LangGraph React Agent"]
        Grok["XAI Grok-3-mini"]
        Tools["18 Agent Tools"]
    end

    subgraph Data["Data Layer"]
        PG[("PostgreSQL<br/>ahmf schema<br/>28 tables")]
        TMDB["TMDB API"]
        OMDB["OMDB API"]
    end

    Browser -->|"HTMX GET/POST"| Routes
    Browser -->|"WebSocket"| AGUI
    Routes --> Auth
    Auth --> Modules
    AGUI --> CMD
    CMD -->|"structured commands"| Tools
    CMD -->|"free-form"| LG
    LG --> Grok
    LG --> Tools
    Tools --> PG
    Tools --> TMDB
    Tools --> OMDB
    Modules --> PG
```

---

## 3-Pane Layout

```mermaid
graph LR
    subgraph Left["Left Pane (260px)"]
        Logo["AH Logo"]
        Nav_Intel["Intelligence<br/>• AI Chat<br/>• User Guide"]
        Nav_P1["Film Financing OS<br/>• Deals<br/>• Contacts<br/>• Sales & Collections<br/>• Credit Rating<br/>• Accounting<br/>• Communications"]
        Nav_AI["AI Tools<br/>• Sales Estimates<br/>• Risk Scoring<br/>• Smart Budget<br/>• Scheduling<br/>• Soft Funding<br/>• Data Room<br/>• Audience Intel<br/>• Talent Intel"]
        UserInfo["User / Logout"]
    end

    subgraph Center["Center Pane (1fr)"]
        Header["Header + Inspector Toggle"]
        Chat["AI Chat (WebSocket)"]
        ModuleView["Module Content (HTMX swap)"]
    end

    subgraph Right["Right Pane (380px, toggleable)"]
        Trace["AI Thinking Trace"]
        Detail["Deal Detail Canvas"]
    end

    Nav_Intel --> Chat
    Nav_P1 --> ModuleView
    Nav_AI --> ModuleView
```

---

## Chat Message Flow

```mermaid
sequenceDiagram
    participant U as User
    participant B as Browser (WebSocket)
    participant A as AGUIThread
    participant CI as Command Interceptor
    participant LG as LangGraph Agent
    participant G as Grok-3 LLM
    participant T as Tools (18)
    participant DB as PostgreSQL

    U->>B: Type message + Enter
    B->>A: WebSocket send (msg)
    A->>A: Remove welcome screen
    A->>CI: _command_interceptor(msg)

    alt Structured command (e.g. "deal:list")
        CI->>T: search_deals()
        T->>DB: SELECT FROM ahmf.deals
        DB-->>T: rows
        T-->>CI: markdown table
        CI-->>A: result string
        A->>B: User bubble + Assistant bubble (OOB swap)
        A->>B: Suggestion pills
    else Free-form (e.g. "What horror films had the best ROI?")
        CI-->>A: None (fall through)
        A->>LG: astream_events(messages)
        LG->>G: LLM reasoning
        G-->>LG: tool_call decision
        LG->>T: invoke tool
        T->>DB: query
        DB-->>T: data
        T-->>LG: tool result
        LG->>G: final response
        loop Token streaming
            G-->>A: token
            A->>B: Span (OOB append)
        end
        A->>B: Remove cursor, render markdown
    end

    A->>DB: Save message to chat_messages
```

---

## Module View Flow

```mermaid
sequenceDiagram
    participant U as User
    participant S as Sidebar Button
    participant H as HTMX Engine
    participant R as Module Route
    participant DB as PostgreSQL

    U->>S: Click "Deals"
    S->>H: loadModule('/module/deals', 'Deals')
    H->>H: Hide chat, show center-content
    H->>R: GET /module/deals
    R->>DB: SELECT deals, stats
    DB-->>R: rows
    R-->>H: HTML partial (Div cls="module-content")
    H->>H: Swap into #center-content
    Note over H: Stats grid + deal cards rendered
    U->>H: Click deal card
    H->>R: GET /module/deal/{id}
    R->>DB: SELECT deal details
    DB-->>R: row
    R-->>H: Detail view HTML
```

---

## Authentication Flow

```mermaid
sequenceDiagram
    participant U as User
    participant B as Browser
    participant FH as FastHTML
    participant Auth as utils/auth.py
    participant DB as PostgreSQL

    U->>B: Navigate to /
    B->>FH: GET /
    FH->>FH: Check session['user_id']
    FH-->>B: 303 Redirect to /login

    U->>B: Enter email + password
    B->>FH: POST /login
    FH->>Auth: authenticate(email, password)
    Auth->>DB: SELECT FROM ahmf.users WHERE email
    DB-->>Auth: user row
    Auth->>Auth: bcrypt.verify(password, hash)
    Auth-->>FH: user dict (or None)

    alt Success
        FH->>FH: session[user_id, email, display_name]
        FH-->>B: 303 Redirect to /
        B->>FH: GET /
        FH-->>B: 3-Pane Layout
    else Failure
        FH-->>B: Login page with error
    end
```

---

## Agent Tools Architecture

```mermaid
graph TB
    subgraph Agent["LangGraph React Agent"]
        LLM["XAI Grok-3-mini"]
    end

    subgraph CoreTools["Core Tools (app.py)"]
        T1["search_deals"]
        T2["get_deal_detail"]
        T3["get_portfolio_overview"]
        T4["search_contacts"]
        T5["search_movies (TMDB)"]
        T6["get_movie_details (TMDB)"]
    end

    subgraph AITools["AI Analysis Tools (modules/)"]
        T7["analyze_production_risk"]
        T8["generate_budget_tool"]
        T9["generate_schedule_tool"]
        T10["analyze_audience_tool"]
        T11["analyze_talent_tool"]
        T12["search_talent_tool"]
    end

    subgraph OpsTools["Operations Tools (modules/)"]
        T13["search_incentives_tool"]
        T14["generate_closing_checklist_tool"]
        T15["search_sales_contracts"]
        T16["get_credit_rating"]
        T17["search_transactions"]
        T18["search_messages"]
    end

    Agent --> CoreTools
    Agent --> AITools
    Agent --> OpsTools

    CoreTools -->|SQL| DB[("PostgreSQL")]
    AITools -->|SQL + LLM| DB
    AITools -->|HTTP| TMDB["TMDB API"]
    OpsTools -->|SQL| DB

    T5 -->|HTTP| TMDB
    T6 -->|HTTP| TMDB
    T12 -->|HTTP| TMDB

    style AITools fill:#e0f2fe
    style OpsTools fill:#f0fdf4
    style CoreTools fill:#fef3c7
```

---

## Database Schema

```mermaid
erDiagram
    users ||--o{ deals : creates
    users ||--o{ contacts : creates
    users ||--o{ chat_conversations : owns

    deals ||--o{ deal_documents : has
    deals ||--o{ deal_approvals : has
    deals ||--o{ deal_balances : has
    deals ||--o{ sales_contracts : has
    deals ||--o{ transactions : has
    deals ||--o{ messages : about
    deals ||--o{ closing_checklists : has

    contacts ||--o{ deal_contacts : linked
    contacts ||--o{ credit_ratings : rated
    contacts ||--o{ contact_activities : logs

    sales_contracts ||--o{ collections : tracks
    closing_checklists ||--o{ checklist_items : contains
    budgets ||--o{ budget_items : contains
    schedules ||--o{ schedule_days : contains

    chat_conversations ||--o{ chat_messages : contains

    users {
        uuid user_id PK
        string email
        string password_hash
        string display_name
        string role
    }

    deals {
        uuid deal_id PK
        string title
        string genre
        string status
        numeric loan_amount
        numeric budget
        string borrower_name
        string producer
        string director
    }

    contacts {
        uuid contact_id PK
        string name
        string company
        string contact_type
        string email
    }

    sales_contracts {
        uuid contract_id PK
        uuid deal_id FK
        string territory
        uuid distributor_id FK
        numeric mg_amount
        string status
    }

    collections {
        uuid collection_id PK
        uuid contract_id FK
        numeric amount_due
        numeric amount_received
        date due_date
        string status
    }

    credit_ratings {
        uuid rating_id PK
        uuid contact_id FK
        numeric score
        numeric payment_reliability
        string risk_tier
        jsonb factors
    }

    transactions {
        uuid txn_id PK
        uuid deal_id FK
        string txn_type
        numeric amount
        string currency
        uuid counterparty_id FK
    }

    messages {
        uuid message_id PK
        uuid deal_id FK
        string subject
        string message_type
        string status
        date due_date
    }

    risk_assessments {
        uuid assessment_id PK
        string title
        jsonb scores
        numeric overall_score
        string risk_tier
    }

    budgets {
        uuid budget_id PK
        string title
        string scenario
        numeric total_amount
        jsonb breakdown
    }

    schedules {
        uuid schedule_id PK
        string title
        integer total_days
    }

    incentive_programs {
        uuid program_id PK
        string name
        string country
        numeric rebate_percent
    }

    audience_reports {
        uuid report_id PK
        string title
        jsonb segments
        jsonb marketing_plan
    }

    talent_reports {
        uuid report_id PK
        string title
        jsonb recommendations
        jsonb package_sims
    }
```

---

## Product Modules

```mermaid
graph LR
    subgraph P1["Product 1: Film Financing OS"]
        Deals["Deals<br/>CRUD + Pipeline"]
        Contacts["Contacts<br/>CRUD + Types"]
        Sales["Sales & Collections<br/>Contracts + MG + Collections"]
        Credit["Credit Rating<br/>AI Scoring (AAA-CCC)"]
        Accounting["Accounting<br/>Transaction Ledger"]
        Comms["Communications<br/>Messages + Tasks"]
    end

    subgraph P2["Product 2: Sales Estimates"]
        Estimates["Revenue Projections<br/>TMDB/OMDB Comps"]
    end

    subgraph P3_9["Products 3-9: AI Tools"]
        Risk["Risk Scoring<br/>6-Dimension Analysis"]
        Budget["Smart Budget<br/>3 Scenarios"]
        Schedule["Scheduling<br/>Location Clustering"]
        Funding["Soft Funding<br/>16 Incentive Programs"]
        DataRoom["Data Room<br/>20-Item Checklists"]
        Audience["Audience Intel<br/>Segment Prediction"]
        Talent["Talent Intel<br/>Cast Recommendations"]
    end

    style P1 fill:#dbeafe
    style P2 fill:#fef3c7
    style P3_9 fill:#f0fdf4
```

---

## Deployment Architecture

```mermaid
graph TB
    subgraph Coolify["Coolify (Docker Host)"]
        Traefik["Traefik Reverse Proxy<br/>SSL Termination"]
        subgraph Container["Docker Container"]
            App["python app.py<br/>FastHTML + Uvicorn<br/>Port 5010"]
        end
    end

    subgraph External["External Services"]
        PG[("PostgreSQL<br/>72.62.114.124:5432<br/>ahmf schema")]
        XAI["XAI API<br/>Grok-3-mini"]
        TMDBe["TMDB API"]
        OMDBe["OMDB API"]
    end

    Client["Browser"] -->|"HTTPS"| Traefik
    Traefik -->|"HTTP :5010"| App
    App --> PG
    App --> XAI
    App --> TMDBe
    App --> OMDBe

    subgraph GitHub["GitHub"]
        Repo["predictivelabsai/monika"]
    end

    Repo -->|"push → auto-deploy"| Coolify
```

---

## File Structure

```
ahmf/
├── app.py                    # Main FastHTML app (routes, agent, layout)
├── CLAUDE.md                 # Project documentation
├── Dockerfile                # Multi-stage Docker build
├── docker-compose.yml        # Coolify deployment config
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables (gitignored)
│
├── modules/                  # Product module routes
│   ├── sales.py              # Sales & Collections
│   ├── credit.py             # Credit Rating (AI scoring)
│   ├── accounting.py         # Transaction ledger
│   ├── comms.py              # Messages & tasks
│   ├── risk.py               # Production Risk Scoring
│   ├── budget.py             # Smart Budgeting
│   ├── schedule.py           # Production Scheduling
│   ├── funding.py            # Soft Funding Discovery
│   ├── dataroom.py           # Deal Closing & Data Room
│   ├── audience.py           # Audience Intelligence
│   ├── talent.py             # Talent Intelligence
│   └── guide.py              # In-app User Guide
│
├── utils/
│   ├── db.py                 # SQLAlchemy pool (singleton)
│   ├── auth.py               # bcrypt + JWT auth
│   ├── tmdb_util.py          # TMDB API client
│   ├── omdb_util.py          # OMDB API client
│   ├── pdf_extractor.py      # PDF script extraction
│   └── agui/                 # AG-UI chat engine
│       ├── core.py           # WebSocket streaming, LangGraph
│       ├── styles.py         # Chat CSS
│       └── chat_store.py     # Chat persistence
│
├── sql/                      # Database migrations (01-13)
├── config/settings.py        # Constants and configuration
├── tests/
│   ├── test_suite.py         # 30 automated tests
│   └── capture_guide.py      # Playwright screenshot capture
├── static/guide/             # User guide screenshots
└── docs/
    ├── architecture_readme.md        # This file
    ├── AHMF_Platform_Overview.md     # Presentation (markdown)
    ├── AHMF_Platform_Overview.pptx   # Presentation (PowerPoint)
    └── generate_pptx.py             # PPTX generator script
```
