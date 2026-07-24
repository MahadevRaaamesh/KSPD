from services.analytics_service import (
    get_crime_trends, get_district_stats, get_station_stats, get_top_ipc_sections
)
from services.graph_service import (
    get_accused_network, get_network_by_name
)
from services.similarity_service import similarity_service
from adapters.database import execute_query

async def sql_query_tool(intent: str, params: dict) -> dict:
    district = params.get("district")
    crime_category = params.get("crime_category")
    
    data = []
    if intent == "crime_trends":
        data = [dp.model_dump() for dp in await get_crime_trends(district, crime_category)]
    elif intent == "district_comparison":
        data = [dp.model_dump() for dp in await get_district_stats()]
    elif intent == "station_analysis":
        data = [dp.model_dump() for dp in await get_station_stats(district)]
    elif intent == "ipc_analysis":
        data = [dp.model_dump() for dp in await get_top_ipc_sections()]
    elif intent == "case_details":
        fir_no = params.get("fir_number")
        if fir_no:
            res = await execute_query("SELECT * FROM CaseMaster WHERE CaseNo LIKE :fir_no OR CrimeNo LIKE :fir_no", {"fir_no": f"%{fir_no}%"})
            data = res
    elif intent == "accused_history":
        name = params.get("person_name")
        if name:
            res = await execute_query("""
                SELECT c.CaseNo, c.CrimeNo, c.CrimeRegisteredDate, s.CaseStatusName
                FROM Accused a
                JOIN CaseMaster c ON a.CaseMasterID = c.CaseMasterID
                LEFT JOIN CaseStatusMaster s ON c.CaseStatusID = s.CaseStatusID
                WHERE a.AccusedName LIKE :name
            """, {"name": f"%{name}%"})
            data = res
            
    return {"data": data, "query_type": intent}

async def graph_query_tool(intent: str, params: dict) -> dict:
    name = params.get("person_name")
    if not name:
        return {"error": "Person name required for graph query."}
        
    if intent == "criminal_network" or intent == "accused_history":
        graph_data = await get_network_by_name(name)
        return {"graph": graph_data.model_dump(), "query_type": intent}
        
    return {"graph": None}

async def vector_search_tool(intent: str, params: dict) -> dict:
    text = params.get("text", "")
    if not text and intent == "similar_cases":
        text = "similar cases" # fallback
        
    res = await similarity_service.search_similar(
        text=text,
        district=params.get("district"),
        crime_category=params.get("crime_category")
    )
    return {"similar_firs": [r.model_dump() for r in res.results], "query_type": intent}
