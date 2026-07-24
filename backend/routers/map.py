from fastapi import APIRouter, Query
from typing import List, Optional
from models.schemas import HeatmapPoint, CrimeCluster
from services.map_service import get_heatmap_data, get_crime_clusters, get_station_markers

router = APIRouter()

@router.get("/heatmap", response_model=List[HeatmapPoint])
async def heatmap_data(
    crime_category: Optional[str] = Query(None, description="Filter by crime category"),
    district: Optional[str] = Query(None, description="Filter by district"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    return await get_heatmap_data(crime_category, district, date_from, date_to)

@router.get("/clusters", response_model=List[CrimeCluster])
async def crime_clusters(
    district: Optional[str] = Query(None, description="Filter by district")
):
    return await get_crime_clusters(district)

@router.get("/stations", response_model=List[dict])
async def station_markers():
    return await get_station_markers()
