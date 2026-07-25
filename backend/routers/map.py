from fastapi import APIRouter, Query
from typing import List, Optional
from models.schemas import HeatmapPoint, CrimeCluster
from services.map_service import get_heatmap_data, get_crime_clusters, get_station_markers

router = APIRouter()

TOD_DESC = "Time of day: night (22-05), morning (06-11), afternoon (12-17), evening (18-21)"

@router.get("/heatmap", response_model=List[HeatmapPoint])
async def heatmap_data(
    crime_category: Optional[str] = Query(None, description="Filter by crime major head"),
    district: Optional[str] = Query(None, description="Filter by district"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    tod: Optional[str] = Query(None, pattern="^(night|morning|afternoon|evening)$", description=TOD_DESC),
):
    return await get_heatmap_data(crime_category, district, date_from, date_to, tod)

@router.get("/clusters", response_model=List[CrimeCluster])
async def crime_clusters(
    district: Optional[str] = Query(None, description="Filter by district"),
    crime_category: Optional[str] = Query(None, description="Filter by crime major head"),
    tod: Optional[str] = Query(None, pattern="^(night|morning|afternoon|evening)$", description=TOD_DESC),
):
    return await get_crime_clusters(district, crime_category, tod)

@router.get("/stations", response_model=List[dict])
async def station_markers():
    return await get_station_markers()
