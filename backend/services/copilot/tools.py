from services.analytics_service import (
    get_crime_trends, get_district_stats, get_station_stats, get_top_ipc_sections
)
from services.graph_service import get_network_by_name
from services.similarity_service import similarity_service
from adapters.database import execute_query


def _months_from_params(params: dict, default: int = 12) -> int:
    n, unit = params.get("last_n"), params.get("last_unit")
    if not n:
        return default
    if unit == "month":
        return max(1, min(24, int(n)))
    if unit == "week":
        return max(1, min(24, round(int(n) / 4) or 1))
    if unit == "day":
        return max(1, min(24, round(int(n) / 30) or 1))
    return default


async def sql_query_tool(intent: str, params: dict) -> dict:
    district = params.get("district")
    crime_category = params.get("crime_category")
    # trends filter on crime_major_head — only pass minor heads through as-is
    major_filter = crime_category if params.get("category_level") != "minor" else None

    data = []
    if intent == "crime_trends":
        months = _months_from_params(params)
        if params.get("category_level") == "minor":
            # filter directly on the minor head for a sharper answer
            q = """
                SELECT SUBSTR(date_reported, 1, 7) as period, COUNT(*) as count
                FROM FIRs
                WHERE date_reported > date((SELECT MAX(date_reported) FROM FIRs), :window)
                  AND crime_minor_head = :minor
            """
            p = {"window": f"-{months} months", "minor": crime_category}
            if district:
                q += " AND district = :district"
                p["district"] = district
            q += " GROUP BY period ORDER BY period"
            data = await execute_query(q, p)
        else:
            data = [dp.model_dump() for dp in await get_crime_trends(district, major_filter, months)]
    elif intent == "district_comparison":
        data = [dp.model_dump() for dp in await get_district_stats()]
    elif intent == "station_analysis":
        data = [dp.model_dump() for dp in await get_station_stats(district)]
    elif intent == "ipc_analysis":
        data = [dp.model_dump() for dp in await get_top_ipc_sections()]
    elif intent == "case_details":
        fir_no = params.get("fir_number")
        if fir_no:
            data = await execute_query(
                "SELECT ROWID, * FROM FIRs WHERE fir_number LIKE :fir_no",
                {"fir_no": f"%{fir_no}%"})
    elif intent == "accused_history":
        name = params.get("person_name")
        if name:
            data = await execute_query("""
                SELECT c.fir_number, c.date_reported, c.status, c.district,
                       c.crime_major_head, c.crime_minor_head
                FROM Accused a
                JOIN FIRs c ON a.fir_rowid = c.ROWID
                WHERE LOWER(a.name) LIKE LOWER(:name)
                ORDER BY c.date_reported DESC
            """, {"name": f"%{name}%"})

    return {"data": data, "query_type": intent}


async def graph_query_tool(intent: str, params: dict) -> dict:
    name = params.get("person_name")
    if not name:
        return {"error": "Person name required for graph query.", "query_type": intent}

    graph_data = await get_network_by_name(name)

    # Real network summary for the synthesizer
    summary_rows = await execute_query("""
        SELECT c.fir_number, c.district, c.crime_minor_head, c.date_reported
        FROM Accused a
        JOIN FIRs c ON a.fir_rowid = c.ROWID
        WHERE LOWER(a.name) LIKE LOWER(:name)
    """, {"name": f"%{name}%"})
    associates = [n.label for n in graph_data.nodes
                  if n.type == "Accused" and n.label.lower() != name.lower()]
    summary = {
        "person": name,
        "case_count": len({r["fir_number"] for r in summary_rows}),
        "associates": sorted(set(associates)),
        "districts": sorted({r["district"] for r in summary_rows if r["district"]}),
        "categories": sorted({r["crime_minor_head"] for r in summary_rows if r["crime_minor_head"]}),
        "fir_numbers": sorted({r["fir_number"] for r in summary_rows}),
    }
    return {"graph": graph_data.model_dump(), "summary": summary, "query_type": intent}


async def vector_search_tool(intent: str, params: dict) -> dict:
    text = params.get("text", "")
    if not text and intent == "similar_cases":
        text = "similar cases"

    crime_category = params.get("crime_category")
    major_filter = crime_category if params.get("category_level") != "minor" else None
    res = await similarity_service.search_similar(
        text=text,
        district=params.get("district"),
        crime_category=major_filter,
    )
    return {"similar_firs": [r.model_dump() for r in res.results],
            "total_indexed": res.total_firs_indexed,
            "query_type": intent}


async def hotspot_tool(intent: str, params: dict) -> dict:
    """Top crime concentrations (station beats) with dominant category."""
    district = params.get("district")
    crime_category = params.get("crime_category")
    level = params.get("category_level")

    q = """
        SELECT police_station as locality, district, COUNT(*) as count,
               latitude, longitude
        FROM FIRs
        WHERE date_reported > date((SELECT MAX(date_reported) FROM FIRs), '-90 days')
    """
    p = {}
    if district:
        q += " AND district = :district"
        p["district"] = district
    if crime_category:
        col = "crime_minor_head" if level == "minor" else "crime_major_head"
        q += f" AND {col} = :category"
        p["category"] = crime_category
    q += " GROUP BY police_station, district ORDER BY count DESC LIMIT 6"
    rows = await execute_query(q, p)

    hotspots = []
    for r in rows:
        top = await execute_query("""
            SELECT crime_minor_head as cat, COUNT(*) as n FROM FIRs
            WHERE police_station = :ps
              AND date_reported > date((SELECT MAX(date_reported) FROM FIRs), '-90 days')
            GROUP BY crime_minor_head ORDER BY n DESC LIMIT 1
        """, {"ps": r["locality"]})
        hotspots.append({
            "locality": r["locality"].replace(" PS", ""),
            "station": r["locality"],
            "district": r["district"],
            "count": r["count"],
            "top_category": top[0]["cat"] if top else None,
        })
    return {"hotspots": hotspots, "query_type": intent}
