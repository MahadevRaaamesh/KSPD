# KSPD — Architecture v3: Optimized for Zoho Catalyst

> **Major revision**: Complete re-architecture for mandatory Catalyst deployment
> **Rule**: If Catalyst has a service for a capability, you MUST use it or risk submission penalty

---

## The Catalyst Constraint — What It Means For You

This is **not optional**. The hackathon rules say:

> *"Using a third-party alternative when a Catalyst service is available may affect the validity of your submission."*
> *"Deployment via Catalyst is mandatory for all submissions, without exception."*

This means we need to remap the entire tech stack. Here's the before/after:

---

## Technology Remapping: What Changes

| Capability | Previous Choice | Catalyst Replacement | Why Switch |
|---|---|---|---|
| **Relational Database** | MySQL | **Catalyst Data Store** | Rule #6 — mandatory |
| **LLM** | Ollama (self-hosted) | **Catalyst QuickML LLM Serving** (Qwen 2.5 14B) | Rule #11 — mandatory. Also: *better model* (14B vs 7B), zero infra |
| **RAG / Knowledge Base** | ChromaDB | **Catalyst QuickML RAG** (for doc-level search) | Rule #11 — mandatory |
| **Vector Search (programmatic)** | ChromaDB / FAISS | **FAISS in-process** on AppSail | No Catalyst equivalent for programmatic vector search — third-party allowed |
| **Backend hosting** | Docker (self-hosted) | **Catalyst AppSail** (custom Docker runtime) | Rule #2 — mandatory |
| **Frontend hosting** | Self-hosted React | **Catalyst Web Client Hosting** or **AppSail** | Rule #4 — mandatory |
| **Graph Database** | Neo4j | ❌ **Dropped** — build graph from Data Store | No Catalyst graph DB; can't justify running Neo4j externally |
| **Caching** | None / in-memory | **Catalyst Cache** | Rule #9 — use it for dashboard aggregates |
| **Authentication** | None | **Catalyst Authentication** (optional) | Rule #17 — nice-to-have for demo |
| **Embeddings** | Sentence Transformers (local) | **Sentence Transformers on AppSail** | No Catalyst embedding service — in-process is fine |
| **Copilot framework** | LangGraph | **LangGraph on AppSail** | No Catalyst equivalent — third-party allowed |

---

## Critical Constraint: Catalyst Data Store Limits

> [!CAUTION]
> **Development environment limits**: 5,000 records per table, 25,000 records total per project. No DDL via code — tables must be created manually in the Catalyst Console. Production has no limits, but you'll be demoing from dev unless you deploy to production.

### Data Strategy

Your Karnataka Police database likely has tens of thousands of FIRs. You have two options:

| Option | Approach | Risk |
|---|---|---|
| **Option A: Subset** | Load ~4,000 representative FIRs + related entities into Data Store | Safe, stays within limits. Demo with "this is a representative dataset." |
| **Option B: Deploy to production** | Push to Catalyst production where there are no record limits | Requires production deployment, more setup time |

> [!IMPORTANT]
> **Recommendation: Use Option A for development, deploy to production for the final submission.** Start with a curated 4,000-record subset for development speed, then load the full dataset into production on Day 4.

### Table Design for Catalyst Data Store (Expanded Flattened Schema)

Tables must be created manually in the Catalyst Console. Plan these upfront. 
*Note: We are using an "expanded flattened" schema to capture all granular ER diagram fields (like religion, blood group, etc.) within the 8 core tables.*

```
Table: FIRs
  - ROWID (auto, bigint — Catalyst provides this)
  - fir_number (text)
  - brief_facts (text)
  - crime_category (text)
  - date_reported (text — store as ISO string)
  - district (text)
  - police_station (text)
  - status (text)
  - latitude (double)
  - longitude (double)
  - gravity (text)
  - crime_major_head (text)
  - crime_minor_head (text)
  - court_name (text)
  - incident_from_date (text)
  - incident_to_date (text)
  - info_received_date (text)

Table: Accused
  - ROWID (auto)
  - name (text)
  - age (int)
  - address (text)
  - fir_rowid (bigint — reference to FIRs.ROWID)
  - gender (text)
  - person_id (text)
  - arrest_date (text)
  - arrest_state (text)
  - arrest_district (text)
  - arrest_station (text)
  - arrest_officer_name (text)

Table: Victims
  - ROWID (auto)
  - name (text)
  - age (int)
  - fir_rowid (bigint)
  - gender (text)
  - is_police (boolean)
  - is_complainant (boolean)
  - occupation (text)
  - religion (text)
  - caste (text)

Table: IPCSections
  - ROWID (auto)
  - section_number (text)
  - description (text)
  - act_name (text)
  - act_short_name (text)
  - is_active (boolean)

Table: FIR_IPC_Map
  - ROWID (auto)
  - fir_rowid (bigint)
  - ipc_rowid (bigint)

Table: PoliceStations
  - ROWID (auto)
  - station_name (text)
  - district (text)
  - latitude (double)
  - longitude (double)
  - unit_type (text)
  - state (text)

Table: Officers
  - ROWID (auto)
  - name (text)
  - rank (text)
  - station_rowid (bigint)
  - designation (text)
  - kgid (text)
  - dob (text)
  - gender (text)
  - blood_group (text)
  - is_physically_challenged (boolean)
  - appointment_date (text)

Table: Chargesheets
  - ROWID (auto)
  - fir_rowid (bigint)
  - filing_date (text)
  - status (text)
  - charge_sheet_type (text)
  - filing_officer_name (text)
```

> [!TIP]
> **Flatten where possible.** Notice that we are storing many demographic and logistical properties (like `religion`, `district`, `police_station`) as text directly in the core tables rather than as foreign keys. This reduces JOINs in ZCQL (which is less powerful than full SQL) and guarantees we capture all ER diagram data without hitting Catalyst limits.
>
> **Data Generation & Sharing:** The fake data generator script will output `.db` and `.csv` files into `backend/data/mock_data/`. Make sure this directory is explicitly **not ignored** in `.gitignore` so your teammates can pull the generated mock data!

---

## Revised Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                    CATALYST WEB CLIENT HOSTING                      │
│                        React + Vite SPA                              │
│  Dashboard │ Map │ Knowledge Graph │ FIR Search │ Copilot Chat       │
└───────────────────────────┬──────────────────────────────────────────┘
                            │ REST API + SSE (streaming)
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    CATALYST APPSAIL (Python Docker)                  │
│                         FastAPI Backend                               │
│                                                                      │
│  ┌───────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌────────────┐ │
│  │ Analytics │ │   Map   │ │  Graph  │ │  Search  │ │  Copilot   │ │
│  │ Router    │ │ Router  │ │ Router  │ │  Router  │ │  Router    │ │
│  └─────┬─────┘ └────┬────┘ └────┬────┘ └─────┬────┘ └──────┬─────┘ │
│        │            │           │             │             │       │
│  ┌─────┴─────┐ ┌────┴────┐ ┌────┴────┐ ┌─────┴────┐ ┌──────┴─────┐ │
│  │ Analytics │ │  Map    │ │  Graph  │ │Similarity│ │ LangGraph  │ │
│  │ Service   │ │ Service │ │ Service │ │ Service  │ │ Agent      │ │
│  └─────┬─────┘ └────┬────┘ └────┬────┘ └─────┬────┘ └──────┬─────┘ │
│        │            │           │             │             │       │
│        ▼            ▼           ▼             │             │       │
│  ┌──────────────────────────────────────┐     │             │       │
│  │      CATALYST DATA STORE (ZCQL)     │     │             │       │
│  │  FIRs │ Accused │ Victims │ IPC...  │     │             │       │
│  └──────────────────────────────────────┘     │             │       │
│                                               │             │       │
│  ┌────────────────────┐                       │             │       │
│  │  CATALYST CACHE    │ ◄── dashboard aggs    │             │       │
│  └────────────────────┘                       │             │       │
│                                               ▼             │       │
│  ┌──────────────────────────────────────┐                   │       │
│  │  FAISS (in-process, on AppSail)     │                   │       │
│  │  FIR embeddings + similarity search  │                   │       │
│  │  Built from Data Store at startup    │                   │       │
│  └──────────────────────────────────────┘                   │       │
│                                                             ▼       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │           CATALYST QUICKML LLM SERVING                       │   │
│  │           Qwen 2.5 14B Instruct (via API)                    │   │
│  │  - Intent classification for copilot                         │   │
│  │  - Response synthesis / summarization                        │   │
│  │  - Insight narration for dashboard                           │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │           CATALYST QUICKML RAG (optional bonus)              │   │
│  │  - Upload FIR documents to Knowledge Base via Console        │   │
│  │  - Natural language Q&A over FIR corpus                      │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Neo4j Decision: Dropped (Again)

With Catalyst, you **cannot run Neo4j**. There's no Catalyst graph database, and running Neo4j as an external third-party service when you're supposed to use Catalyst services would look bad to judges.

**The same solution from the original plan applies**: Build graph JSON from Data Store JOINs, render with Cytoscape.js.

ZCQL supports JOINs, GROUP BY, and subqueries — enough for 2-hop graph traversals:

```
// Conceptual ZCQL — find co-accused
SELECT a2.name, a2.ROWID, f2.fir_number, f2.crime_category
FROM Accused a1
JOIN FIRs f1 ON a1.fir_rowid = f1.ROWID
JOIN Accused a2 ON a2.fir_rowid = f1.ROWID
WHERE a1.ROWID = {accused_id} AND a2.ROWID != a1.ROWID

// Then for each co-accused, find THEIR other cases
SELECT f.fir_number, f.crime_category, f.date_reported
FROM FIRs f
JOIN Accused a ON a.fir_rowid = f.ROWID
WHERE a.name = {co_accused_name}
```

The Graph Service makes 2-3 cascading ZCQL queries and assembles the `{nodes, edges}` JSON. Cytoscape.js renders it identically to how it would look with Neo4j.

---

## Similar FIR Search: Dual Approach

### Primary: FAISS In-Process (for programmatic search)

Since Catalyst QuickML RAG is console-based (no programmatic upload API), use **FAISS in-process on AppSail** for your similarity search feature:

```
Startup Flow:
1. AppSail container starts
2. Load Sentence Transformer model (bundled in Docker image)
3. Query all FIR brief_facts from Data Store
4. Generate embeddings in batch
5. Build FAISS IndexFlatIP
6. Hold in memory

Query Flow:
1. User submits text → encode with same model
2. FAISS returns top-K nearest neighbors
3. Map indices → FIR ROWIDs
4. Fetch full FIR details from Data Store
5. Return results with similarity scores
```

> [!WARNING]
> **AppSail memory constraint**: The Sentence Transformer model (`all-MiniLM-L6-v2`) is ~80MB. FAISS index for 5,000 FIRs at 384 dims ≈ 7.5MB. Total in-memory footprint is ~100MB. This should fit within AppSail's limits, but test early. If it doesn't, use the smaller `all-MiniLM-L6-v2` (same model, it's already small) or pre-compute embeddings and save as a numpy file in the Docker image.

### Bonus: QuickML RAG (for knowledge base Q&A)

Separately, upload a curated set of FIR documents (as PDFs or text files) to QuickML RAG via the Console. This gives you a second AI feature:

- **FAISS**: "Find the 10 most similar FIRs to this description" (structured, returns FIR records)
- **QuickML RAG**: "What are the common patterns in chain-snatching cases in Bengaluru?" (unstructured, returns LLM-generated narrative from the FIR corpus)

This is a **bonus feature** — implement FAISS first, add RAG if time permits on Day 4.

---

## LangGraph Copilot: Adapted for Catalyst

The LangGraph architecture from the previous plan is retained, but the tools now call Catalyst services:

```
┌─────────────────┐
│  User Question  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│        Router Node                  │
│  Calls QuickML LLM Serving         │
│  (Qwen 2.5 14B) for classification │
└───┬─────────┬──────────┬───────────┘
    │         │          │
    ▼         ▼          ▼
┌────────┐ ┌────────┐ ┌──────────┐
│SQL Tool│ │Search  │ │Analytics │
│        │ │Tool    │ │Tool      │
│Queries │ │Queries │ │Aggregates│
│Catalyst│ │FAISS   │ │from      │
│Data    │ │(in-    │ │Data Store│
│Store   │ │process)│ │+ Cache   │
│via ZCQL│ │        │ │          │
└───┬────┘ └───┬────┘ └────┬─────┘
    │         │          │
    └─────┬───┴──────────┘
          │
          ▼
┌─────────────────────────────────────┐
│       Synthesizer Node              │
│  Calls QuickML LLM Serving         │
│  (Qwen 2.5 14B) to format response │
└─────────────────────────────────────┘
```

### Calling QuickML LLM Serving from LangGraph

QuickML exposes Qwen 2.5 14B via OAuth-authenticated REST API. In your LangGraph nodes:

```
Conceptual flow:

1. Get OAuth token (Catalyst SDK handles this inside AppSail)
2. POST to QuickML LLM endpoint:
   - Headers: { Authorization: "Zoho-oauthtoken ...", X-ZORG-ID: "..." }
   - Body: { messages: [...], temperature: 0.1, max_tokens: 500 }
3. Parse response

The LangGraph agent wraps this as a custom LLM class or a simple
HTTP-based tool that any node can call.
```

**Advantage**: Qwen 2.5 **14B** Instruct is a significantly better model than the 7B you'd self-host with Ollama. Better intent classification, better summarization, better response quality. And zero infrastructure to manage.

---

## Development Strategy: Local + Catalyst Parallel Track

> [!IMPORTANT]
> **Do NOT develop directly on Catalyst from Day 1.** Catalyst Data Store's console-based table creation and deployment cycles will slow you down. Instead:

### Dual-Track Approach

| Track | Purpose | Tools |
|---|---|---|
| **Local Dev** (Days 1-3) | Fast iteration, debugging | SQLite (or local MySQL), local FAISS, mock LLM responses |
| **Catalyst Deploy** (Days 3-5) | Real deployment, Catalyst services | Data Store, QuickML, AppSail, Web Client Hosting |

### How This Works

1. **Days 1-3**: Develop the entire app locally. Use SQLite (with the same schema as Catalyst Data Store) as your database. Mock LLM calls with static responses. Get all features working.

2. **Day 3-4**: Create a **Catalyst adapter layer** — swap SQLite queries for ZCQL calls, mock LLM for QuickML API calls. This is a thin abstraction:

```
Conceptual adapter pattern:

class DatabaseAdapter:
    # Local dev: uses SQLite/MySQL
    # Catalyst: uses ZCQL via Catalyst SDK

class LLMAdapter:
    # Local dev: returns mock responses (or calls local Ollama)
    # Catalyst: calls QuickML LLM Serving API

Config flag: ENVIRONMENT = "local" | "catalyst"
```

3. **Day 4-5**: Deploy to Catalyst, test with real Data Store and QuickML.

This way, you get fast development velocity AND Catalyst compliance.

---

## Revised Folder Structure (Catalyst-Compatible)

```
kspd/
├── catalyst.json                    # Catalyst project config (auto-generated by CLI)
├── app-config.json                  # Catalyst app config
├── README.md
├── .env.example
│
├── backend/                         # → Deployed to Catalyst AppSail
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                      # FastAPI entry point
│   ├── config.py                    # Env-based settings (local vs catalyst)
│   │
│   ├── adapters/                    # Abstraction layer for local vs Catalyst
│   │   ├── __init__.py
│   │   ├── database.py              # SQLite (local) ↔ ZCQL (Catalyst)
│   │   ├── llm.py                   # Mock/Ollama (local) ↔ QuickML (Catalyst)
│   │   └── cache.py                 # Dict (local) ↔ Catalyst Cache
│   │
│   ├── models/                      # Pydantic models (request/response schemas)
│   │   ├── __init__.py
│   │   ├── fir.py
│   │   ├── accused.py
│   │   ├── graph.py                 # GraphNode, GraphEdge schemas
│   │   └── copilot.py              # CopilotRequest, CopilotResponse
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── analytics.py
│   │   ├── map.py
│   │   ├── graph.py
│   │   ├── search.py
│   │   └── copilot.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── analytics_service.py
│   │   ├── map_service.py
│   │   ├── graph_service.py         # ZCQL JOINs → graph JSON
│   │   ├── similarity_service.py    # FAISS in-process
│   │   └── copilot/
│   │       ├── __init__.py
│   │       ├── agent.py             # LangGraph agent definition
│   │       ├── state.py             # Agent state schema
│   │       ├── nodes.py             # Router, tool, synthesizer nodes
│   │       └── tools.py             # Data Store tool, FAISS tool, analytics tool
│   │
│   ├── scripts/
│   │   ├── load_data_store.py       # Load police data → Catalyst Data Store
│   │   ├── load_sqlite.py           # Load police data → local SQLite (dev)
│   │   └── build_embeddings.py      # Pre-compute FAISS index
│   │
│   └── data/
│       ├── fir_index.faiss          # Pre-built FAISS index (bundled in Docker)
│       ├── fir_id_map.json          # FAISS position → FIR ROWID
│       └── karnataka_police.sql     # Source data
│
├── frontend/                        # → Deployed to Catalyst Web Client Hosting
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   │
│   ├── public/
│   │   └── karnataka.geojson
│   │
│   └── src/
│       ├── main.jsx
│       ├── App.jsx
│       ├── api/
│       │   ├── client.js
│       │   └── streaming.js         # SSE client for copilot streaming
│       ├── hooks/
│       ├── components/
│       │   ├── Layout/
│       │   ├── Dashboard/
│       │   ├── CrimeMap/
│       │   ├── KnowledgeGraph/
│       │   ├── FIRSearch/
│       │   └── Copilot/
│       ├── pages/
│       └── styles/
│           └── index.css
│
└── data/
    ├── karnataka_police.sql
    └── karnataka_districts.geojson
```

---

## Copilot Streaming: SSE instead of WebSocket

> [!WARNING]
> **Catalyst AppSail may not support WebSocket connections reliably.** Use **Server-Sent Events (SSE)** instead for copilot streaming. SSE works over standard HTTP, is supported everywhere, and is simpler to implement.

```
Frontend:
  const eventSource = new EventSource('/api/copilot/stream?q=...');
  eventSource.onmessage = (event) => {
    // Append token to response
  };

Backend (FastAPI):
  @router.get("/stream")
  async def stream_copilot(q: str):
      async def generate():
          async for token in langgraph_agent.astream(q):
              yield f"data: {json.dumps(token)}\n\n"
      return StreamingResponse(generate(), media_type="text/event-stream")
```

---

## Catalyst Services Usage Summary

| # | Catalyst Service | How You Use It | Priority |
|---|---|---|---|
| 1 | **AppSail** (custom Docker) | Host FastAPI backend + FAISS + Sentence Transformer | 🔴 Critical |
| 2 | **Web Client Hosting** | Host React SPA | 🔴 Critical |
| 3 | **Data Store** | All relational data (FIRs, Accused, Victims, etc.) | 🔴 Critical |
| 4 | **QuickML LLM Serving** | Qwen 2.5 14B for copilot intent/synthesis + insight generation | 🔴 Critical |
| 5 | **Cache** | Cache dashboard aggregates, frequent queries | 🟡 Important |
| 6 | **QuickML RAG** | Bonus: upload FIR docs for natural language Q&A | 🟢 Bonus |
| 7 | **Authentication** | Bonus: add login page | 🟢 Bonus |
| 8 | **API Gateway** | Route frontend to backend, handle CORS | 🟡 Important |
| 9 | **Stratus** | Store FAISS index file, GeoJSON, assets | 🟢 Bonus |

**Using 4-5 Catalyst services prominently shows judges you've embraced the platform.**

---

## Revised 5-Day Roadmap for Catalyst

### Day 1: Foundation + Catalyst Setup

| Time | Dev A (Backend & AI) | Dev B (Frontend) | Dev C (Catalyst & Integration) |
|---|---|---|---|
| Morning | Set up local SQLite with police data subset. Write Pydantic models for all entities. | React + Vite scaffold. TailwindCSS. 5-page routing. Dark theme layout with sidebar. | **Create Catalyst project** via CLI. Set up AppSail, Web Client Hosting. Create all 8 Data Store tables manually in Console. |
| Afternoon | Write `adapters/database.py` — SQLite implementation. Write all analytics/map/graph service functions against SQLite. | Design system: color tokens, card components, loading states. Build Layout components. | **Set up QuickML**: Deploy Qwen 2.5 14B. Test LLM endpoint with curl. Get OAuth token flow working. Document the endpoint URL + auth pattern. |
| Evening | Write `build_embeddings.py` — load FIR text, generate FAISS index. Test similarity search. | Dashboard page with placeholder chart components. | Wire `adapters/llm.py` — implement QuickML adapter. Test from Python. Write `load_data_store.py` script for Catalyst Data Store. |

**Day 1 Milestone**: App runs locally with SQLite + mock LLM. Catalyst project exists. QuickML LLM tested.

---

### Day 2: Core Features (Local Dev)

| Time | Dev A | Dev B | Dev C |
|---|---|---|---|
| Morning | Analytics service — all aggregate queries. Graph service — cascading queries for network building. | ECharts: TrendChart, DistrictBar, IPCPieChart — hooked to analytics API. StatsCards. | Analytics + Graph routers. Connect services → endpoints. Test with frontend. |
| Afternoon | Similarity service — FAISS query, metadata filtering, score normalization. | Cytoscape.js GraphCanvas — node/edge rendering, click expansion, type-based styling (color per node type). | Search + Map routers. Connect all services. |
| Evening | Map service — geo queries, heatmap data generation. | MapLibre MapView + HeatmapLayer + StationMarkers with Karnataka GeoJSON. | Full integration pass. Fix all broken connections. Every page shows real data. |

**Day 2 Milestone**: All 4 visual features (Dashboard, Map, Graph, Search) working locally with real data.

---

### Day 3: Copilot + Catalyst Migration Start

| Time | Dev A | Dev B | Dev C |
|---|---|---|---|
| Morning | LangGraph agent: state schema, graph definition, router node (intent classifier using QuickML). | FIR Search page: SearchBar, ResultCard, SimilarityBadge — polished UI. | **Start Catalyst migration**: Implement ZCQL adapter in `adapters/database.py`. Load data subset into Data Store. Test basic queries. |
| Afternoon | LangGraph tools: DataStore tool, FAISS tool, Analytics tool. Synthesizer node. | Copilot chat UI: ChatWindow, MessageBubble, SuggestedQueries, streaming display. | **Continue migration**: Swap all service queries to use adapter (auto-switches between SQLite/ZCQL based on config). Test. |
| Evening | End-to-end copilot test — classify → route → query → synthesize. Test with 10 sample questions. | ResultRenderer — renders table/chart/graph alongside copilot text response. | **Deploy backend to AppSail**: Dockerfile, push to registry, configure AppSail. Verify it starts. |

**Day 3 Milestone**: Copilot works end-to-end locally. Backend deploys to AppSail. Data Store has data.

---

### Day 4: Full Catalyst Deployment + AI Polish

| Time | Dev A | Dev B | Dev C |
|---|---|---|---|
| Morning | Risk analysis insights: SQL aggregates + QuickML narration → InsightCards data. QuickML RAG setup (upload FIR docs to Console, test). | InsightCards on dashboard. Copilot UI polish: suggested queries, error states, loading. | **Full deployment**: Frontend to Web Client Hosting. Backend to AppSail. Verify all APIs work on Catalyst. |
| Afternoon | Fine-tune copilot prompts. Ensure all 10 intents work reliably. Prepare demo queries. | Page transitions (framer-motion). Hover effects. Micro-animations on graph/map. | **Catalyst Cache**: Cache dashboard aggregates. Set up API Gateway if needed. |
| Evening | **ALL THREE**: End-to-end testing on deployed Catalyst instance. Fix all bugs. | | |

**Day 4 Milestone**: Fully deployed on Catalyst. All features working on live URL.

---

### Day 5: Polish + Demo Prep

| Time | Dev A | Dev B | Dev C |
|---|---|---|---|
| Morning | Seed compelling demo data. Ensure the demo "story" has interesting criminal networks. | Final UI polish: consistency pass, responsive checks, animation timing. | README with architecture diagram. Ensure clean `catalyst deploy`. |
| Afternoon | **ALL THREE**: Rehearse demo 3+ times. Script the narrative. Time it. | | |
| Evening | Record backup demo video. Final bug fixes. Prepare slides if needed. | | |

**Day 5 Milestone**: Polished, deployed, rehearsed. Ready to present.**

---

## Demo Script (Judge Impact)

Script your demo as a **story**, not a feature walkthrough:

```
NARRATIVE (5 minutes):

1. [DASHBOARD — 30 sec]
   "Karnataka Police handles 200,000+ FIRs annually. Our platform
   gives intelligence commanders an instant overview."
   → Show dashboard with live stats, trend charts, insight cards.

2. [MAP — 30 sec]
   "Let's drill into Bengaluru Urban, which shows elevated activity."
   → Click district on map → heatmap reveals clusters → click a station.

3. [KNOWLEDGE GRAPH — 60 sec] ← THIS IS YOUR MONEY SHOT
   "An officer investigating a robbery case wants to know: who is this
   accused connected to?"
   → Enter an accused name → graph expands showing cases, co-accused,
     victims → click a co-accused → expand their network.
   → "We just discovered a 3-person criminal network across 7 cases
     that would take an officer days to find manually."

4. [SIMILAR FIR SEARCH — 45 sec]
   "The officer wants to know: have we seen this MO before?"
   → Paste FIR brief facts → system returns 94% match to a 2023 case.
   → "Same area, same method, different accused — but look..."
   → Click to graph view → the accused in the similar case is a
     co-accused of our original suspect.

5. [COPILOT — 60 sec]
   "Instead of navigating between screens, the officer can simply ask."
   → Type: "Show robbery cases in Bengaluru Urban in the last year
     with repeat offenders"
   → Copilot returns results + renders a mini-graph.
   → Type: "Which IPC sections are most common in chain snatching?"
   → Copilot returns a table.

6. [CLOSE — 30 sec]
   "KSPD doesn't replace the existing police database. It's an
   intelligence layer that turns raw data into actionable insights.
   Built on Zoho Catalyst with QuickML, Data Store, and AppSail."
   → Show architecture slide.
```

> [!TIP]
> **End by naming the Catalyst services you used.** Judges for a Zoho hackathon want to see platform adoption. Saying "Built on Catalyst QuickML, Data Store, AppSail, Cache, and Web Client Hosting" is a strong closer.

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Data Store 5K record limit blocks development** | High | High | Use SQLite locally. Load subset. Deploy to production for full data. |
| **QuickML LLM response latency is too high** | Medium | Medium | Cache frequent copilot responses. Use low `max_tokens` for classification (50 tokens). |
| **AppSail can't handle FAISS + SentenceTransformer in memory** | Medium | High | **Test on Day 1.** Fallback: pre-embed and store vectors as a numpy file, load only the index (not the model) at runtime. Embed at build time. |
| **ZCQL doesn't support a needed query pattern** | Medium | Medium | Keep queries simple. Flatten schema. Do multi-step queries in Python if ZCQL can't do complex JOINs. |
| **Catalyst deployment fails on demo day** | Low | Critical | Record a backup demo video on Day 5 morning. |
| **LangGraph adds too much complexity** | Medium | Medium | Fallback: use direct HTTP calls to QuickML with hardcoded prompts. LangGraph is a library, not infra — it just structures your code. |

---

## Key Decisions Summary (Final)

| Decision | Choice | Rationale |
|---|---|---|
| **Database** | Catalyst Data Store (ZCQL) | Mandatory per hackathon rules |
| **LLM** | Catalyst QuickML (Qwen 2.5 14B) | Mandatory; also better than self-hosted 7B |
| **Vector Search** | FAISS in-process on AppSail | No Catalyst vector DB; FAISS is lightweight |
| **Graph DB** | ❌ None — graph viz from ZCQL JOINs | No Catalyst graph DB; Neo4j would hurt submission |
| **Frontend** | Catalyst Web Client Hosting (React + Vite) | Mandatory per rules |
| **Backend** | Catalyst AppSail (Python Docker) | Mandatory per rules |
| **Copilot** | LangGraph calling QuickML + Data Store + FAISS | Structured, debuggable, uses Catalyst services |
| **Caching** | Catalyst Cache | Shows Catalyst adoption; improves dashboard performance |
| **Streaming** | SSE (not WebSocket) | More compatible with AppSail |
| **Dev strategy** | Local (SQLite) → Catalyst (Data Store) via adapter layer | Fast dev velocity + Catalyst compliance |

> [!IMPORTANT]
> **The #1 priority is using Catalyst services visibly and prominently.** In a Zoho-sponsored hackathon, platform adoption is as important as feature quality. Every feature should trace back to a Catalyst service in your architecture diagram.
