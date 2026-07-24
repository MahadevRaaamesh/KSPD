from adapters.database import execute_query
from models.schemas import HeatmapPoint, CrimeCluster
from typing import List, Optional

async def get_heatmap_data(
    crime_category: Optional[str] = None,
    district: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
) -> List[HeatmapPoint]:
    query = """
        SELECT c.latitude, c.longitude, COUNT(*) as intensity
        FROM CaseMaster c
        JOIN Unit u ON c.PoliceStationID = u.UnitID
        JOIN District d ON u.DistrictID = d.DistrictID
        JOIN CrimeHead ch ON c.CrimeMajorHeadID = ch.CrimeHeadID
        WHERE c.latitude IS NOT NULL AND c.longitude IS NOT NULL
    """
    params = {}
    
    if crime_category:
        query += " AND ch.CrimeGroupName = :category"
        params["category"] = crime_category
        
    if district:
        query += " AND d.DistrictName = :district"
        params["district"] = district
        
    if date_from:
        query += " AND c.CrimeRegisteredDate >= :date_from"
        params["date_from"] = date_from
        
    if date_to:
        query += " AND c.CrimeRegisteredDate <= :date_to"
        params["date_to"] = date_to
        
    query += " GROUP BY c.latitude, c.longitude"
    
    results = await execute_query(query, params)
    return [HeatmapPoint(
        latitude=row["latitude"],
        longitude=row["longitude"],
        intensity=float(row["intensity"])
    ) for row in results]

async def get_crime_clusters(district: Optional[str] = None) -> List[CrimeCluster]:
    query = """
        SELECT c.latitude, c.longitude, COUNT(*) as count, ch.CrimeGroupName as crime_category
        FROM CaseMaster c
        JOIN Unit u ON c.PoliceStationID = u.UnitID
        JOIN District d ON u.DistrictID = d.DistrictID
        JOIN CrimeHead ch ON c.CrimeMajorHeadID = ch.CrimeHeadID
        WHERE c.latitude IS NOT NULL AND c.longitude IS NOT NULL
    """
    params = {}
    if district:
        query += " AND d.DistrictName = :district"
        params["district"] = district
        
    query += " GROUP BY c.latitude, c.longitude, ch.CrimeGroupName"
    
    results = await execute_query(query, params)
    return [CrimeCluster(
        latitude=row["latitude"],
        longitude=row["longitude"],
        count=row["count"],
        crime_category=row["crime_category"]
    ) for row in results]

async def get_station_markers() -> List[dict]:
    query = """
        SELECT u.UnitName as station_name, d.DistrictName as district,
        u.UnitID, COUNT(c.CaseMasterID) as case_count
        FROM Unit u
        JOIN District d ON u.DistrictID = d.DistrictID
        LEFT JOIN CaseMaster c ON c.PoliceStationID = u.UnitID
        GROUP BY u.UnitID, u.UnitName, d.DistrictName
    """
    # Note: Our schema doesn't have lat/lng in the Unit table, so we use
    # average lat/lng from cases reported in that station as a proxy.
    
    proxy_query = """
        SELECT u.UnitName as station_name, d.DistrictName as district,
        AVG(c.latitude) as latitude, AVG(c.longitude) as longitude,
        COUNT(c.CaseMasterID) as case_count
        FROM Unit u
        JOIN District d ON u.DistrictID = d.DistrictID
        LEFT JOIN CaseMaster c ON c.PoliceStationID = u.UnitID
        GROUP BY u.UnitID, u.UnitName, d.DistrictName
    """
    
    results = await execute_query(proxy_query)
    # Filter out stations with no valid coordinates
    return [dict(row) for row in results if row.get("latitude")]
