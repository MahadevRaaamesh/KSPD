from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# ──── Entity Models ────

class FIR(BaseModel):
    CaseMasterID: int
    CrimeNo: str
    CaseNo: Optional[str] = None
    CrimeRegisteredDate: Optional[str] = None
    BriefFacts: Optional[str] = None
    CrimeGroupName: Optional[str] = None  # Joined from CrimeHead
    CrimeHeadName: Optional[str] = None   # Joined from CrimeSubHead
    DistrictName: Optional[str] = None    # Joined from District
    UnitName: Optional[str] = None        # Joined from Unit (Police Station)
    CaseStatusName: Optional[str] = None  # Joined from CaseStatusMaster
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    ipc_sections: List[str] = []

class AccusedPerson(BaseModel):
    AccusedMasterID: int
    AccusedName: str
    AgeYear: Optional[int] = None
    GenderID: Optional[int] = None
    CaseMasterID: Optional[int] = None

class Victim(BaseModel):
    VictimMasterID: int
    VictimName: str
    AgeYear: Optional[int] = None
    CaseMasterID: Optional[int] = None

class PoliceStation(BaseModel):
    UnitID: int
    UnitName: str
    DistrictName: Optional[str] = None
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
