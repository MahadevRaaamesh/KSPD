from fastapi import APIRouter, Query, Path, HTTPException
from models.schemas import SimilaritySearchResponse, SimilaritySearchRequest, FIR
from services.similarity_service import similarity_service

router = APIRouter()

@router.post("/similar", response_model=SimilaritySearchResponse)
async def search_similar(request: SimilaritySearchRequest):
    return await similarity_service.search_similar(
        text=request.text,
        top_k=request.top_k,
        district=request.district,
        crime_category=request.crime_category
    )

@router.get("/similar/{fir_id}", response_model=SimilaritySearchResponse)
async def search_similar_by_id(
    fir_id: int = Path(...),
    top_k: int = Query(10)
):
    return await similarity_service.search_by_fir_id(fir_id, top_k)

@router.get("/fir/{fir_id}", response_model=FIR)
async def get_fir(fir_id: int = Path(...)):
    fir = await similarity_service.get_fir_by_id(fir_id)
    if not fir:
        raise HTTPException(status_code=404, detail="FIR not found")
    return fir
