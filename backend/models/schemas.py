from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# ──── Entity Models ────

class FIR(BaseModel):
    ROWID: int
    fir_number: str
    date_reported: Optional[str] = None
    brief_facts: Optional[str] = None
    crime_major_head: Optional[str] = None
    crime_minor_head: Optional[str] = None
    district: Optional[str] = None
    police_station: Optional[str] = None
    status: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    ipc_sections: List[str] = []

class AccusedPerson(BaseModel):
    ROWID: int
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    fir_rowid: Optional[int] = None

class Victim(BaseModel):
    ROWID: int
    name: str
    age: Optional[int] = None
    fir_rowid: Optional[int] = None

class PoliceStation(BaseModel):
    ROWID: int
    station_name: str
    district: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

# ──── Analytics Response Models ────

class OverviewStats(BaseModel):
    total_firs: int
    total_accused: int
    total_victims: int
    cases_solved: int
    cases_pending: int
    chargesheets_filed: int

class TrendDataPoint(BaseModel):
    period: str
    count: int

class DistrictStat(BaseModel):
    district: str
    total_cases: int
    solved: int
    pending: int

class IPCStat(BaseModel):
    section: str
    count: int
    description: Optional[str] = None

class StationStat(BaseModel):
    station_name: str
    district: str
    total_cases: int
    solved: int

# ──── Map Models ────

class HeatmapPoint(BaseModel):
    latitude: float
    longitude: float
    intensity: float

class CrimeCluster(BaseModel):
    latitude: float
    longitude: float
    count: int
    crime_category: Optional[str] = None

# ──── Graph Models ────

class GraphNode(BaseModel):
    id: str
    label: str
    type: str
    properties: Dict[str, Any]

class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str

class GraphData(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]

# ──── Search Models ────

class SimilarFIRResult(BaseModel):
    fir: FIR
    similarity_score: float

class SimilaritySearchRequest(BaseModel):
    text: str
    top_k: int = 10
    district: Optional[str] = None
    crime_category: Optional[str] = None

class SimilaritySearchResponse(BaseModel):
    query_text: str
    results: List[SimilarFIRResult]
    total_firs_indexed: int

# ──── Copilot Models ────

class CopilotRequest(BaseModel):
    question: str

class CopilotResponse(BaseModel):
    answer: str
    sources: List[str] = []
    visualization_hint: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
