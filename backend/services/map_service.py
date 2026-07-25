from adapters.database import execute_query
from models.schemas import HeatmapPoint, CrimeCluster
from typing import List, Optional

# Time-of-day buckets filtered on the incident hour
TOD_CLAUSES = {
    "night": "(CAST(strftime('%H', incident_from_date) AS INTEGER) >= 22 "
             "OR CAST(strftime('%H', incident_from_date) AS INTEGER) <= 5)",
    "morning": "CAST(strftime('%H', incident_from_date) AS INTEGER) BETWEEN 6 AND 11",
    "afternoon": "CAST(strftime('%H', incident_from_date) AS INTEGER) BETWEEN 12 AND 17",
    "evening": "CAST(strftime('%H', incident_from_date) AS INTEGER) BETWEEN 18 AND 21",
}


def _tod_filter(query: str, tod: Optional[str]) -> str:
    if tod and tod in TOD_CLAUSES:
        query += f" AND incident_from_date IS NOT NULL AND {TOD_CLAUSES[tod]}"
    return query


async def get_heatmap_data(
    crime_category: Optional[str] = None,
    district: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    tod: Optional[str] = None,
) -> List[HeatmapPoint]:
    query = """
        SELECT latitude, longitude, COUNT(*) as intensity
        FROM FIRs
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    """
    params = {}

    if crime_category:
        query += " AND crime_major_head = :category"
        params["category"] = crime_category

    if district:
        query += " AND district = :district"
        params["district"] = district

    if date_from:
        query += " AND date_reported >= :date_from"
        params["date_from"] = date_from

    if date_to:
        query += " AND date_reported <= :date_to"
        params["date_to"] = date_to

    query = _tod_filter(query, tod)
    query += " GROUP BY latitude, longitude"

    results = await execute_query(query, params)
    return [HeatmapPoint(
        latitude=row["latitude"],
        longitude=row["longitude"],
        intensity=float(row["intensity"])
    ) for row in results]


async def get_crime_clusters(
    district: Optional[str] = None,
    crime_category: Optional[str] = None,
    tod: Optional[str] = None,
) -> List[CrimeCluster]:
    query = """
        SELECT latitude, longitude, COUNT(*) as count,
               crime_major_head as crime_category,
               crime_minor_head as minor_head
        FROM FIRs
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    """
    params = {}
    if district:
        query += " AND district = :district"
        params["district"] = district
    if crime_category:
        query += " AND crime_major_head = :category"
        params["category"] = crime_category

    query = _tod_filter(query, tod)
    query += " GROUP BY latitude, longitude, crime_major_head, crime_minor_head"

    results = await execute_query(query, params)
    return [CrimeCluster(
        latitude=row["latitude"],
        longitude=row["longitude"],
        count=row["count"],
        crime_category=row["crime_category"],
        minor_head=row["minor_head"],
    ) for row in results]


async def get_station_markers() -> List[dict]:
    query = """
        SELECT station_name, district, ROWID as UnitID,
        latitude, longitude,
        (SELECT COUNT(*) FROM FIRs WHERE FIRs.police_station = PoliceStations.station_name) as case_count
        FROM PoliceStations
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    """

    results = await execute_query(query)
    return [dict(row) for row in results]
