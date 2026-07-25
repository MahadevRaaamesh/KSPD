from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize FAISS and other lifespan dependencies here
    from services.similarity_service import similarity_service
    await similarity_service.initialize()
    app.state.similarity_service = similarity_service
    yield
    # Cleanup resources here later

app = FastAPI(
    title="DRISHTI — Karnataka Police Crime Intelligence API",
    description="AI-driven crime analytics, mapping, network intelligence and copilot for Karnataka State Police.",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/api/health")
async def api_health():
    from adapters.database import execute_query
    from services.similarity_service import similarity_service
    res = await execute_query("SELECT COUNT(*) as cnt FROM FIRs")
    return {
        "status": "ok",
        "firs_indexed": res[0]["cnt"],
        "faiss_ready": similarity_service.index is not None,
    }

from routers.analytics import router as analytics_router
app.include_router(analytics_router, prefix="/api/analytics", tags=["Analytics"])

from routers.map import router as map_router
app.include_router(map_router, prefix="/api/map", tags=["Map"])

from routers.graph import router as graph_router
app.include_router(graph_router, prefix="/api/graph", tags=["Graph"])

from routers.search import router as search_router
app.include_router(search_router, prefix="/api/search", tags=["Search"])

from routers.copilot import router as copilot_router
app.include_router(copilot_router, prefix="/api/copilot", tags=["Copilot"])

from routers.auth import router as auth_router
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
