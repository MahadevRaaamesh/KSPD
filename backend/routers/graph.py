from fastapi import APIRouter, Query, Path
from typing import List
from models.schemas import GraphData, AccusedPerson
from services.graph_service import (
    get_case_graph, get_accused_network, get_network_by_name,
    get_co_accused, get_all_accused, get_repeat_offenders,
)

router = APIRouter()

@router.get("/repeat-offenders", response_model=List[dict])
async def repeat_offenders(limit: int = Query(20, ge=1, le=100, description="Max offenders to return")):
    return await get_repeat_offenders(limit)

@router.get("/case/{fir_id}", response_model=GraphData)
async def case_graph(fir_id: int = Path(..., description="The internal CaseMasterID")):
    return await get_case_graph(fir_id)

@router.get("/accused/{accused_id}", response_model=GraphData)
async def accused_graph(accused_id: int = Path(..., description="The internal AccusedMasterID")):
    return await get_accused_network(accused_id)

@router.get("/accused", response_model=List[AccusedPerson])
async def list_accused(limit: int = Query(100, description="Number of accused to return")):
    return await get_all_accused(limit)

@router.get("/network", response_model=GraphData)
async def network_by_name(name: str = Query(..., description="Name of the accused to search")):
    return await get_network_by_name(name)

@router.get("/co-accused/{accused_id}", response_model=List[AccusedPerson])
async def co_accused(accused_id: int = Path(..., description="The internal AccusedMasterID")):
    return await get_co_accused(accused_id)
