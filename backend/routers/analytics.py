from fastapi import APIRouter, Query
from typing import List, Optional
from models.schemas import OverviewStats, TrendDataPoint, DistrictStat, IPCStat, StationStat
from services.analytics_service import (
    get_overview_stats, get_crime_trends, get_district_stats,
    get_top_ipc_sections, get_station_stats, get_insights
)

router = APIRouter()

@router.get("/overview", response_model=OverviewStats)
async def overview():
    return await get_overview_stats()

@router.get("/trends", response_model=List[TrendDataPoint])
async def crime_trends(
    district: Optional[str] = Query(None, description="Filter by district"),
    crime_category: Optional[str] = Query(None, description="Filter by crime category")
):
    return await get_crime_trends(district=district, crime_category=crime_category)

@router.get("/districts", response_model=List[DistrictStat])
async def district_stats():
    return await get_district_stats()

@router.get("/ipc-sections", response_model=List[IPCStat])
async def top_ipc_sections(limit: int = Query(15, description="Number of sections to return")):
    return await get_top_ipc_sections(limit=limit)

@router.get("/stations", response_model=List[StationStat])
async def station_stats(
    district: Optional[str] = Query(None, description="Filter by district")
):
    return await get_station_stats(district=district)

@router.get("/insights", response_model=List[dict])
async def insights():
    return await get_insights()
