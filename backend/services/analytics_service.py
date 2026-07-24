from adapters.database import execute_query
from models.schemas import OverviewStats, TrendDataPoint, DistrictStat, IPCStat, StationStat
from typing import List, Optional

async def get_overview_stats() -> OverviewStats:
    res = await execute_query("SELECT COUNT(*) as cnt FROM FIRs")
    total_firs = res[0]["cnt"]
    
    res = await execute_query("SELECT COUNT(*) as cnt FROM Accused")
    total_accused = res[0]["cnt"]
    
    res = await execute_query("SELECT COUNT(*) as cnt FROM Victims")
    total_victims = res[0]["cnt"]
    
    res = await execute_query("SELECT COUNT(*) as cnt FROM FIRs WHERE status IN ('Charge Sheeted', 'Closed')")
    cases_solved = res[0]["cnt"]
    
    res = await execute_query("SELECT COUNT(*) as cnt FROM FIRs WHERE status = 'Under Investigation'")
    cases_pending = res[0]["cnt"]
    
    res = await execute_query("SELECT COUNT(*) as cnt FROM Chargesheets")
    chargesheets_filed = res[0]["cnt"]
    
    return OverviewStats(
        total_firs=total_firs,
        total_accused=total_accused,
        total_victims=total_victims,
        cases_solved=cases_solved,
        cases_pending=cases_pending,
        chargesheets_filed=chargesheets_filed
    )

async def get_crime_trends(district: Optional[str] = None, crime_category: Optional[str] = None) -> List[TrendDataPoint]:
    query = """
        SELECT SUBSTR(date_reported, 1, 7) as period, COUNT(*) as count 
        FROM FIRs 
        WHERE 1=1
    """
    params = {}
    if district:
        query += " AND district = :district"
        params["district"] = district
    if crime_category:
        query += " AND crime_major_head = :category"
        params["category"] = crime_category
        
    query += " GROUP BY period ORDER BY period"
    results = await execute_query(query, params)
    return [TrendDataPoint(period=row["period"], count=row["count"]) for row in results if row["period"]]

async def get_district_stats() -> List[DistrictStat]:
    query = """
        SELECT district, COUNT(*) as total,
        SUM(CASE WHEN status IN ('Charge Sheeted', 'Closed') THEN 1 ELSE 0 END) as solved,
        SUM(CASE WHEN status = 'Under Investigation' THEN 1 ELSE 0 END) as pending
        FROM FIRs
        GROUP BY district
        ORDER BY total DESC
    """
    results = await execute_query(query)
    return [DistrictStat(
        district=row["district"],
        total_cases=row["total"],
        solved=row["solved"] or 0,
        pending=row["pending"] or 0
    ) for row in results if row["district"]]

async def get_top_ipc_sections(limit: int = 15) -> List[IPCStat]:
    query = """
        SELECT i.section_number as section, COUNT(*) as count, i.description
        FROM FIR_IPC_Map m
        JOIN IPCSections i ON m.ipc_rowid = i.ROWID
        GROUP BY i.section_number, i.description
        ORDER BY count DESC
        LIMIT :limit
    """
    results = await execute_query(query, {"limit": limit})
    return [IPCStat(
        section=row["section"],
        count=row["count"],
        description=row["description"]
    ) for row in results]

async def get_station_stats(district: Optional[str] = None) -> List[StationStat]:
    query = """
        SELECT police_station as station_name, district, COUNT(*) as total,
        SUM(CASE WHEN status IN ('Charge Sheeted', 'Closed') THEN 1 ELSE 0 END) as solved
        FROM FIRs
        WHERE 1=1
    """
    params = {}
    if district:
        query += " AND district = :district"
        params["district"] = district
        
    query += " GROUP BY police_station, district ORDER BY total DESC"
    results = await execute_query(query, params)
    return [StationStat(
        station_name=row["station_name"],
        district=row["district"],
        total_cases=row["total"],
        solved=row["solved"] or 0
    ) for row in results if row["station_name"]]

async def get_insights() -> List[dict]:
    return [
        {
            "title": "Robbery Cases Active",
            "description": "Robbery has been the most reported crime in Bengaluru Urban this quarter.",
            "metric": "High",
            "type": "warning"
        },
        {
            "title": "Clearance Rate Improving",
            "description": "The overall clearance rate has improved across all districts.",
            "metric": "+5%",
            "type": "success"
        }
    ]
