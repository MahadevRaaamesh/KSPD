# DRISHTI
### AI-Driven Crime Analytics & Intelligence Platform · Karnataka State Police

> **Drishti** (Sanskrit/Kannada: *vision, sight*) turns fragmented FIR records into
> living intelligence — spatiotemporal hotspots, criminal network graphs, semantic
> case matching and an AI copilot — so the SCRB moves from **reactive reporting to
> proactive policing**.

---

## Why DRISHTI wins on the problem statement

| Challenge (KSP brief) | DRISHTI capability |
|---|---|
| Data silos & Excel-based reporting | Unified FastAPI data layer over the full FIR corpus; one live console for the entire state |
| Lack of advanced analytics | FAISS vector search over FIR narratives, network link analysis, statistical spike detection, predictive risk scoring |
| Fragmented SCRB information | Command Dashboard: statewide KPIs, district drill-down, category typology, IPC section analysis |
| Reactive policing | **Emerging Trend Alerts** (30-day spike detection with red-zone pulsing), **District Risk Index** (explainable AI risk scores), **Incident Clock** (day × hour deployment planning) |
| Hidden criminal networks | **Network Explorer**: 2-hop co-accused graphs, tap-to-expand link tracing, repeat-offender watchlist with cross-district Modus Operandi profiles |
| Undiscovered behavioral patterns | **Case Matcher**: describe an incident in natural language; MiniLM sentence embeddings + FAISS retrieve semantically similar cases across jurisdictions |
| No conversational access to data | **AI Copilot**: LangGraph agent with intent routing, live SQL/graph/vector tools and token-streamed answers (SSE) |

---

## Architecture

```
frontend/  React 19 + Vite · ECharts · MapLibre GL · Cytoscape · SSE streaming
backend/   FastAPI (Python 3.12)
           ├── adapters/    SQLite via SQLAlchemy async · LLM adapter (local NLG ⇄ QuickML)
           │                zcql.py / cache.py — Catalyst scaffolding for production
           ├── services/    analytics · map · graph · similarity (FAISS + MiniLM) · copilot (LangGraph)
           ├── routers/     /api/analytics · /api/map · /api/graph · /api/search · /api/copilot · /api/auth
           └── scripts/     generate_data.py (Karnataka-realistic corpus) · build_embeddings.py
```

- **Dataset**: ~2,400 synthetic FIRs across 14 Karnataka districts / ~60 police stations,
  24 months, with realistic narratives, gang co-offending structures, repeat offenders,
  hour-of-day crime signatures and deliberately injected crime spikes for the alert engine.
- **Vector search**: `all-MiniLM-L6-v2` (384-d) embeddings of every FIR narrative in a
  FAISS `IndexFlatIP` (cosine) index.
- **Copilot**: LangGraph state machine (router → tools → synthesizer) that answers from
  *live database queries* — works fully offline; swaps to Zoho Catalyst QuickML in production.

## Quickstart

**Fastest path — two PowerShell windows, one command each:**

```powershell
.\start-backend.ps1     # window 1 → http://localhost:8000
.\start-frontend.ps1    # window 2 → http://localhost:5173
```

Both scripts create the virtualenv, install dependencies, and build the data +
FAISS index on first run if they are missing. Sign in with **`KSP-1054` / `drishti`**.

> **Windows PowerShell note:** PowerShell 5.1 does not support `&&` between
> commands — use `;` or separate lines. The two servers are long-running, so they
> need their own terminal windows regardless.

<details>
<summary>Manual setup (equivalent to the scripts above)</summary>

### 1 — Backend (port 8000)

```powershell
cd KSPD/backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

.venv\Scripts\python scripts\generate_data.py        # build the Karnataka FIR corpus
.venv\Scripts\python scripts\build_embeddings.py     # build the FAISS semantic index

.venv\Scripts\python -m uvicorn main:app --port 8000
```

Swagger docs: <http://localhost:8000/docs> · Health: <http://localhost:8000/api/health>

### 2 — Frontend (port 5173)

```powershell
cd KSPD/frontend
npm install
npm run dev
```

Open <http://localhost:5173> and sign in:

| Badge ID | Password |
|---|---|
| `KSP-1054` | `drishti` |

</details>

## Console modules

1. **Command Dashboard** — statewide KPIs with sparklines, pulsing spike alerts,
   filterable crime trend, AI District Risk Index, category typology,
   day×hour Incident Clock, IPC analysis, district case-load table.
2. **GeoIntel Map** — MapLibre dark basemap of Karnataka with kernel-density heat
   layer, incident clusters, station markers, and district / category /
   **time-of-day** filters for patrol planning.
3. **Network Explorer** — repeat-offender priority watchlist, subject tracing by
   name, cytoscape link chart with tap-to-expand 2-hop traversal
   (accused ↔ cases ↔ stations ↔ IPC sections ↔ victims).
4. **Case Matcher** — semantic similarity search over FIR narratives with match
   scoring; "find similar to this FIR" pivots for MO linkage.
5. **AI Copilot** — streaming conversational analyst over the live data: trends,
   comparisons, hotspots, criminal histories and network retrieval with inline
   charts and FIR source citations.

## 3-minute demo script

1. **Sign in** (`KSP-1054` / `drishti`) — the console opens on the Command Dashboard.
2. **Point at the red pulsing alerts**: "The engine flagged a **Chain Snatching surge in
   Bengaluru City, +740%** over its 30-day baseline, and a synthetic-drugs spike in
   Mangaluru — nobody queried for these, the platform surfaced them."
3. **District Risk Index** — hover a district to show the *drivers* behind the score
   ("volume up 73% MoM, clearance below state average"). Explainable, not a black box.
4. **Incident Clock** — "burglary peaks 23:00–04:00; this is a patrol-roster decision."
5. **GeoIntel Map** → switch the time-of-day filter to **NIGHT**: 2,412 incidents
   collapse to the 528 that happen after dark, hotspots visibly shift.
6. **Network Explorer** → click **Ajay Shinde (8× FIR)**: one node per person reveals
   an OTP-fraud crew — Gagan Shinde and Krishna Poojary co-offend in 6 of his 8 cases.
   Tap any case node to expand the network hop by hop.
7. **Case Matcher** → run *"chain snatching near bus stop at night"*: the same modus
   operandi surfaces in Mysuru, Hubballi-Dharwad and Davanagere — cross-jurisdiction
   MO linkage that keyword search over Excel can never find.
8. **AI Copilot** → *"Show the criminal network of Ajay Shinde"*: a streamed analytical
   answer with real figures, an inline chart, and **cited FIR numbers**.

## Deployment

Backend containerises for **Zoho Catalyst AppSail** (`backend/Dockerfile`; data +
index built at image build time). Frontend is a static Vite build deployable to
Catalyst Web Client Hosting — set `VITE_API_BASE` to the AppSail URL.

---

*Built for the KSP Datathon. Synthetic data only — no real records.*
