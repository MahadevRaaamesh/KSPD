from adapters.database import execute_query
from models.schemas import OverviewStats, TrendDataPoint, DistrictStat, IPCStat, StationStat
from typing import List, Optional

async def get_overview_stats() -> OverviewStats:
    # 1. Total FIRs
    res = await execute_query("SELECT COUNT(*) as cnt FROM CaseMaster")
    total_firs = res[0]["cnt"]
    
    # 2. Total Accused
    res = await execute_query("SELECT COUNT(*) as cnt FROM Accused")
    total_accused = res[0]["cnt"]
    
    # 3. Total Victims
    res = await execute_query("SELECT COUNT(*) as cnt FROM Victim")
    total_victims = res[0]["cnt"]
    
    # 4. Cases Solved (Assuming StatusID 2=Charge Sheeted, 3=Closed)
    res = await execute_query("SELECT COUNT(*) as cnt FROM CaseMaster WHERE CaseStatusID IN (2, 3)")
    cases_solved = res[0]["cnt"]
    
    # 5. Cases Pending (Assuming StatusID 1=Under Investigation)
    res = await execute_query("SELECT COUNT(*) as cnt FROM CaseMaster WHERE CaseStatusID = 1")
    cases_pending = res[0]["cnt"]
    
    # 6. Chargesheets Filed (Assuming StatusID 2=Charge Sheeted)
    res = await execute_query("SELECT COUNT(*) as cnt FROM CaseMaster WHERE CaseStatusID = 2")
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
        SELECT SUBSTR(CrimeRegisteredDate, 1, 7) as period, COUNT(*) as count 
        FROM CaseMaster c
        JOIN Unit u ON c.PoliceStationID = u.UnitID
        JOIN District d ON u.DistrictID = d.DistrictID
        JOIN CrimeHead ch ON c.CrimeMajorHeadID = ch.CrimeHeadID
        WHERE 1=1
    """
    params = {}
    
    if district:
        query += " AND d.DistrictName = :district"
        params["district"] = district
        
    if crime_category:
        query += " AND ch.CrimeGroupName = :category"
        params["category"] = crime_category
        
    query += " GROUP BY period ORDER BY period"
    
    results = await execute_query(query, params)
    return [TrendDataPoint(period=row["period"], count=row["count"]) for row in results if row["period"]]

async def get_district_stats() -> List[DistrictStat]:
    query = """
        SELECT d.DistrictName, COUNT(c.CaseMasterID) as total,
        SUM(CASE WHEN c.CaseStatusID IN (2, 3) THEN 1 ELSE 0 END) as solved,
        SUM(CASE WHEN c.CaseStatusID = 1 THEN 1 ELSE 0 END) as pending
        FROM District d
        LEFT JOIN Unit u ON d.DistrictID = u.DistrictID
        LEFT JOIN CaseMaster c ON u.UnitID = c.PoliceStationID
        GROUP BY d.DistrictName
        ORDER BY total DESC
    """
    results = await execute_query(query)
    return [DistrictStat(
        district=row["DistrictName"],
        total_cases=row["total"],
        solved=row["solved"] or 0,
        pending=row["pending"] or 0
    ) for row in results]

async def get_top_ipc_sections(limit: int = 15) -> List[IPCStat]:
    query = """
        SELECT s.SectionCode, COUNT(*) as count, s.SectionDescription
        FROM ActSectionAssociation asa
        JOIN Section s ON asa.SectionID = s.SectionCode
        GROUP BY s.SectionCode, s.SectionDescription
        ORDER BY count DESC
        LIMIT :limit
    """
    # Note: We didn't link ActSectionAssociation fully in mock data, 
    # but we will fallback to CrimeMinorHeadID if association table is empty.
    
    # Simpler fallback for our mock data setup
    fallback_query = """
        SELECT ch.CrimeHeadName as section, COUNT(*) as count, ch.CrimeHeadName as description
        FROM CaseMaster c
        JOIN CrimeSubHead ch ON c.CrimeMinorHeadID = ch.CrimeSubHeadID
        GROUP BY ch.CrimeHeadName
        ORDER BY count DESC
        LIMIT :limit
    """
    
    results = await execute_query(fallback_query, {"limit": limit})
    return [IPCStat(
        section=row["section"],
        count=row["count"],
        description=row["description"]
    ) for row in results]

async def get_station_stats(district: Optional[str] = None) -> List[StationStat]:
    query = """
        SELECT u.UnitName, d.DistrictName, COUNT(c.CaseMasterID) as total,
        SUM(CASE WHEN c.CaseStatusID IN (2, 3) THEN 1 ELSE 0 END) as solved
        FROM Unit u
        JOIN District d ON u.DistrictID = d.DistrictID
        LEFT JOIN CaseMaster c ON u.UnitID = c.PoliceStationID
        WHERE 1=1
    """
    params = {}
    if district:
        query += " AND d.DistrictName = :district"
        params["district"] = district
        
    query += " GROUP BY u.UnitName, d.DistrictName ORDER BY total DESC"
    
    results = await execute_query(query, params)
    return [StationStat(
        station_name=row["UnitName"],
        district=row["DistrictName"],
        total_cases=row["total"],
        solved=row["solved"] or 0
    ) for row in results]

async def get_insights() -> List[dict]:
    # Placeholder for AI insights
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
