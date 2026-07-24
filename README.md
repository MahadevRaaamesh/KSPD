# KSPD — Crime Intelligence Platform

> **Karnataka State Police Department (KSPD)** Intelligence Platform built for automated crime analysis, map clustering, 2-hop criminal network visualization, vector similarity search, and AI-powered copilot.
> 
> Optimized for deployment on **Zoho Catalyst** (AppSail, Data Store, QuickML, Cache, and Web Client Hosting).

---

## 🏗️ Architecture Overview

* **Backend Engine**: FastAPI (Python 3.11) running on **Catalyst AppSail**.
* **Database Pipeline**: Dual-mode abstraction layer supporting **SQLite (local dev)** and **Catalyst Data Store / ZCQL (production)**.
* **Vector Similarity**: FAISS in-process index (`IndexFlatIP`) using `SentenceTransformers` (`all-MiniLM-L6-v2`) for semantic search over FIR brief facts.
* **AI Copilot Agent**: **LangGraph** workflow with router node, tool execution nodes, synthesizer node, and **Server-Sent Events (SSE)** streaming.
* **AI LLM Integration**: Dual-mode LLM adapter supporting mock responses in dev and **Catalyst QuickML (Qwen 2.5 14B)** in production.

---

## ⚡ Quickstart — Local Setup Pipeline

Follow these steps to set up and run the backend locally:

### 1. Clone & Set Up Virtual Environment

```bash
git clone <your-repo-url>
cd KSPD/backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # On Linux/macOS
# .venv\Scripts\activate          # On Windows PowerShell
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Copy Environment Configuration

```bash
cp .env.example .env
```

### 4. Run Data & Embedding Pipeline

Initialize the local SQLite database (`kspd.db`) with 500 mock FIR records and build the FAISS vector index:

```bash
# Step 1: Generate Mock FIR Records, Accused, Victims, Stations & Districts
python scripts/generate_mock_data.py

# Step 2: Pre-compute 384-dimensional FAISS embeddings
python scripts/build_embeddings.py
```

### 5. Launch FastAPI Backend

```bash
uvicorn main:app --reload --port 8000
```

* **Swagger API Docs**: `http://localhost:8000/docs`
* **Health Check**: `http://localhost:8000/health`

---

## 📡 API Endpoints Summary

| Module | Method | Endpoint | Description |
|---|---|---|---|
| **Analytics** | `GET` | `/api/analytics/overview` | Total FIRs, solved/pending cases, accused & victim counts |
| | `GET` | `/api/analytics/trends` | Time-series crime trends filtered by district/category |
| | `GET` | `/api/analytics/districts` | District-wise case totals and clearance metrics |
| | `GET` | `/api/analytics/ipc-sections` | Top IPC sections by frequency |
| | `GET` | `/api/analytics/stations` | Police station level case statistics |
| **Map** | `GET` | `/api/map/heatmap` | Geolocated intensity points for heatmap layers |
| | `GET` | `/api/map/clusters` | Spatial clusters with crime category tags |
| | `GET` | `/api/map/stations` | Police station marker coordinates & case counts |
| **Graph** | `GET` | `/api/graph/case/{fir_id}` | Case-centric graph (FIR ↔ Accused ↔ Station ↔ IPC) |
| | `GET` | `/api/graph/accused/{accused_id}` | 2-hop criminal network graph (Accused ↔ Co-Accused) |
| | `GET` | `/api/graph/network?name={name}` | Criminal network search by accused person name |
| **Search** | `POST`| `/api/search/similar` | FAISS vector similarity search using text description |
| | `GET` | `/api/search/similar/{fir_id}` | Find similar cases given an existing FIR ID |
| **Copilot** | `POST`| `/api/copilot/query` | LangGraph agent endpoint returning JSON answer & sources |
| | `GET` | `/api/copilot/stream?question={q}` | Server-Sent Events (SSE) streaming token output |
| | `GET` | `/api/copilot/suggestions` | Suggested sample questions for the UI |

---

## 🐳 Docker Deployment (Catalyst AppSail)

Build and run using Docker (which automatically executes data generation & embedding pre-computation during container build):

```bash
cd backend
docker build -t kspd-backend .
docker run -p 9000:9000 kspd-backend
```

---

## 🚀 GitHub Actions CI Pipeline

The project includes an automated GitHub Actions workflow (`.github/workflows/ci.yml`) that triggers on every `push` and `pull_request` to:
1. Set up Python 3.11 and system C++ libraries (`libopenblas-dev`, `libomp-dev`).
2. Install dependencies from `requirements.txt`.
3. Run `generate_mock_data.py` to create test data.
4. Run `build_embeddings.py` to test vector generation.
5. Verify FastAPI router loading & module integrity.
