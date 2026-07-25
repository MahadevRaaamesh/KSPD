# Daily Changelog

---

## Rebuild — DRISHTI v2.0 (July 25, 2026, later session)

The platform was rebranded **DRISHTI** and hardened end-to-end for submission.

### Data — the foundation everything else stood on
- **Replaced the corpus.** The shipped DB held **10 FIRs with worldwide-random
  coordinates** (Pacific/Antarctic) and non-Karnataka districts, so the "Karnataka
  crime map" was empty at any sane viewport. New `backend/scripts/generate_data.py`
  (stdlib-only, seeded, deterministic) builds **2,412 FIRs / 58 stations across the
  14 real districts**, 24 months, with hour-of-day crime signatures, 8 gang
  structures, 73 repeat offenders, and deliberately injected spikes for the alert
  engine. Exports CSV mirrors so the DB and the committed CSVs never drift.
- **Deleted `scripts/generate_mock_data.py`** — it wrote a second, incompatible
  schema into the *same* file, corrupting the DB and then crashing mid-write.
- **Fixed `build_embeddings.py`**, which queried a table (`CaseMaster`) that does not
  exist — the FAISS index could never be built, so similarity search was dead code.
  The index now builds; semantic search returns real cosine-ranked matches.

### Backend
- Real **spike detection** replaced the hardcoded `/insights` text; added
  `/risk-scores` (explainable district risk with drivers), `/time-patterns`
  (day × hour), `/categories`, `/graph/repeat-offenders`, and `/api/auth/login`.
- **Copilot now answers with real numbers** computed from live queries (it previously
  replied `Mock response based on: User Question: ...`). Intent routing, param
  extraction, hotspot/network/comparison synthesis, SSE token streaming.
- **Link analysis fixed:** accused nodes are collapsed **one node per person**
  (`person_id`), so a repeat offender no longer fragments into duplicate nodes and
  the shared-case links he exists to reveal actually appear (30 nodes → 14, same 29 edges).
- Month-aligned trend windows (a mid-month cut-off rendered as a phantom dip),
  CWD-independent paths, pinned requirements, CORS/credentials corrected.

### Frontend
- Rebuilt on a **"tactical console" design system** (gold-on-navy, hairline grids,
  corner-tick panels, mono readouts) with a **CVD-validated chart palette**.
- **New Case Matcher page** — the FAISS feature previously had *no UI at all*.
- Hardened API layer (status checks, timeouts, encoded params), error boundaries,
  **persistent login** (session survived nothing before — every refresh logged you out),
  loading/empty/error states, and **all fabricated fallback data deleted** — the old
  dashboard silently rendered invented crime statistics when the backend was down.
- Route-level code splitting: initial bundle **2.98 MB → 250 kB**.
- Restored `optimizeDeps.exclude: ['maplibre-gl']` after confirming its removal
  reproduced the WebWorker crash noted below — the map rendered blank without it.

**Verified:** every endpoint returns 2xx (401 only where intended), full browser
walkthrough of all five modules with **zero runtime console errors**, lint clean,
production build green.

---

**Date:** July 25, 2026

Here is a summary of all the major development work accomplished today to build out the KSP Analytics platform for the hackathon:

### 1. Database & Backend Architecture
- **Schema Refactor:** Transitioned the database architecture to a flattened 8-table SQLite schema, optimizing for analytics and graph querying.
- **Data Generation:** Successfully ran the fake data generator to seed the local database with 10,000 realistic mock records.
- **FastAPI Core:** Configured all primary routing services (`analytics.py`, `map.py`, `graph.py`, `copilot.py`) and successfully installed heavy ML dependencies (`torch`, `sentence-transformers`).

### 2. Frontend Infrastructure & Authentication
- **Vite Setup:** Initialized the React frontend using Vite and React Router.
- **Design System:** Implemented a stunning, custom glassmorphic dark-mode CSS system without relying on Tailwind.
- **Secure Portal:** Added a full Login Page (`Login.jsx`) with route-guarding in `App.jsx`. (Current local credentials: `admin` / `password`).

### 3. Dashboard & Analytics
- **Echarts Integration:** Built the `Dashboard.jsx` view to pull data dynamically from the SQLite backend and visualize crime trends and district performance.

### 4. Geospatial Mapping (`CrimeMap.jsx`)
- **MapLibre Integration:** Successfully built the Crime Map using `maplibre-gl`, integrating heatmap layers and station markers.
- **Performance Fix:** Optimized the loading sequence so the dark-matter basemap renders instantly, while the massive geographic data sets stream in asynchronously in the background.
- **Vite Fix:** Patched the `vite.config.js` to exclude `maplibre-gl` from optimization, fixing the local development WebWorker crash.

### 5. Criminal Network Graph (`NetworkGraph.jsx`)
- **Dual-Pane Layout:** Overhauled the Knowledge Graph page into a split-pane design.
- **Data Table:** Added a scrollable, filterable list of Accused persons that pulls directly from a newly created backend endpoint (`GET /api/graph/accused`).
- **Cytoscape Polish:** Fixed severe label-overlapping issues by adjusting `text-margin-y` and adding semi-transparent backgrounds to text nodes, making the physics-based graph highly readable and interactive.

### 6. AI Copilot Chat (`CopilotChat.jsx`)
- **Chat Interface:** Built a full LLM chat interface capable of rendering markdown responses.
- **Mock LLM Architecture:** Engineered a local "Mock LLM" interceptor in `backend/adapters/llm.py`. This detects keywords (like "trends" or "network") and simulates an AI response locally, avoiding the need for paid API keys during hackathon development.
- **Zoho Readiness:** Wired the backend logic to automatically seamlessly switch over to the Zoho QuickML endpoint via environment variables (`QUICKML_LLM_ENDPOINT`) upon production deployment to Catalyst.
